from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
from django.views.decorators.http import require_POST, require_http_methods
from django.shortcuts import render
from django.http import JsonResponse
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.views import APIView
from rest_framework.response import Response

from .models import TiebaTask
from GTDjango.settings import CHROMEDRIVER_PATH, RESULTS_PATH, WEIBO_RESULTS_PATH, PROXIES_PATH
from main.general_processing.general_processing import *
from main.tieba_processing.tieba_processing import *
from main.weibo_processing.weibo_processing import *
from weibocrawler.weibo_crawler import *

from scrapyd_api import ScrapydAPI

import asyncio
from bs4 import BeautifulSoup
from collections import OrderedDict
import csv
import datetime
import glob
import json
import os
from pathlib import Path
import shutil
import sys
import time
from uuid import uuid4
from urllib.parse import urlparse
import urllib.request
from urllib.parse import quote
import zipfile
from zipfile import ZipFile


scrapyd = ScrapydAPI('http://localhost:6800')


# url: /main
def index(request):
    ''' Landing Page allowing for search of Tieba or Weibo '''
    history = get_history()
    history_tieba = set()
    for folder in history:
        history_tieba.add(get_tiebaname_from_folder(folder))
    history_tieba_sorted = list(history_tieba)
    history_tieba_sorted.sort()
    return render(request, 'main/index.html', context={'history_tieba': history_tieba_sorted})


# url: /main/home/
def home(request):
    ''' Tieba and Date Selection page. '''
    keyword = request.GET.get('kw')
    tieba = request.GET.get('tieba')
    forums = []
    if keyword:
        print('Keyword >>', keyword)
        forums = get_related_forums_by_selenium(keyword)
    elif tieba:
        print('Tieba >>', tieba)
        forums = [tieba.replace('^', '/')]
    return render(request, 'main/home.html', context={'forums': forums})


# url: /main/crawl/tieba/
@csrf_exempt
@require_http_methods(['POST', 'GET'])  # only get and post
def make_tieba_task(request):
    '''
    Called by AJAX on home.html.
    (1) Schedules scrapy task, (2) Create tieba crawl task log in database that manages ongoing crawl tasks
    Able to crawl multiple tieba concurrently. 
    This will only handle making task, 'main/result/tieba/' will wait for the result.
    '''
    if request.method == 'POST':
        print('welcome to tieba task:')
        keyword_full = request.POST.get('keyword', None)
        # remove the 'ba' character as it leads to a different link
        keyword = keyword_full[:-1]
        start_date = format_date(request.POST.get(
            'start_date_year', None), request.POST.get('start_date_month', None))
        end_date = format_date(request.POST.get(
            'end_date_year', None), request.POST.get('end_date_month', None))
        status = 'finished'

        if keyword and start_date and end_date:
            folder_name = create_directory(keyword_full, start_date, end_date)
            task_id, unique_id, status = schedule(  # shedule tieba crawling task
                scrapyd, keyword, start_date, end_date, folder_name)

            current_task = TiebaTask()
            current_task.set_all_attributes(
                task_id, keyword, start_date, end_date, status, folder_name)
            current_task.save()  # create task log in database
            print('Tieba Task >>>', folder_name, task_id, unique_id, status)
            data = {
                "Is_submitted": True,
                "task_id": task_id
            }
        else:
            data = {
                "Is_submitted": False
            }
        return JsonResponse(data)


# url: /main/crawl/weibo
@csrf_exempt
def make_weibo_task(request):
    '''
    Makes Weibo Task
    '''
    if request.method == "POST":
        uid = request.POST.get('uid')
        kw = uname = request.POST.get('uname', None)
        download_folder = None

        if uid and uname:
            # folder_name should be same as uname
            folder_name = create_directory_weibo(uname)
            current_task = WeiboCrawlTask(uid, uname) # begins crawling process
            if current_task.status == 'finished':
                download_folder = process_download_folder_weibo(folder_name)

        context = {
            'keyword':  kw,
            'folder': download_folder  # not empty only if there are downloads
        }
        resultTemplate = 'main/weiboresult.html'

    return render(request, resultTemplate, context)


# url: /main/cancel/
def cancel(request):
    '''
    Cancels the Tieba/Weibo task.
    For Tieba: cancel scrapy task, remove task from database log, and delete folder
    For Weibo: stop crawling in associated WeiboCrawlTask object and using class method to cancel it
    '''
    task_type = request.GET.get('task_type')
    cancelled = False

    if task_type == 'tieba':
        task_id = request.GET.get('id', None)
        if task_id:
            scrapyd.cancel('default', task_id)
            current_task = TiebaTask.objects.filter(task_id=task_id).first()
            if current_task:
                delete_folder(RESULTS_PATH, current_task.folder_name)
                current_task.delete()
                cancelled = True

    elif task_type == 'weibo':  # weibo
        folder_name = request.GET.get('id', None)
        if folder_name:
            success = WeiboCrawlTask.cancel_weibo_crawl(folder_name)
            if success:
                try:
                    delete_folder(WEIBO_RESULTS_PATH, folder_name)
                except FileNotFoundError as e:
                    print(e)
                    print('Unable to delete folder "', folder_name, '" as file or folder cannot be found.')
                cancelled = True

    return render(request, 'main/cancel.html', context = { 'cancelled': cancelled })


# url: /main/history/tieba/
def history_tieba(request):
    ''' Renders history page of Tieba. Content is render by AJAX calls on FE. '''
    return render(request, 'main/history_tieba.html')


# url: /main/history/weibo/
def history_weibo(request):
    ''' Renders history page of Weibo. Content is render by AJAX calls on FE. '''
    return render(request, 'main/history_weibo.html')


# url:/main/validate/
@csrf_exempt
def validate_isexisted(request):
    '''
    Tieba and Weibo: To check if selection has already been scraped before.
    For Weibo, there is an additional key, "info-dict" containing uid and uname, if it exists.
    '''
    data = {}
    if request.method == 'POST':
        if request.POST.get('task_type') == 'tieba':
            keyword = request.POST.get('keyword', None)
            start_date = format_date(request.POST.get(
                'start_date_year', None), request.POST.get('start_date_month', None))
            end_date = format_date(request.POST.get(
                'end_date_year', None), request.POST.get('end_date_month', None))
            folder_name = '_'.join([keyword, start_date, end_date])
            exists = folder_name in next(os.walk(RESULTS_PATH))[1]
            is_ongoing_task = True if TiebaTask.objects.filter(
                folder_name=folder_name) else False
            data = {
                'Is_existed': exists,
                'is_ongoing_task': is_ongoing_task
            }

        elif request.POST.get('task_type') == 'weibo':
            info_dict = get_weibo_userid(request.POST.get('keyword', None))
            folder_name = info_dict['uname'] if info_dict else ''
            is_ongoing_task = True if WeiboCrawlTask.get_task(
                folder_name) else False
            dir_list = next(os.walk(WEIBO_RESULTS_PATH))[1]
            exists = folder_name in dir_list
            data = {
                'Is_existed': exists,
                'ongoing_task': is_ongoing_task,
                'info_dict': info_dict
            }
    return JsonResponse(data)


# url: /main/result/tieba/
@csrf_exempt
def result_tieba(request):
    '''
    Check for scrapy crawl status every 10 seconds. 
    Once the task finishes, process the downloads, and render the result page.
    '''
    download_folder = ''
    resultTemplate = 'main/result.html'

    current_task = TiebaTask.objects.filter(
        task_id=request.POST.get('task_id')).first()
    if current_task:
        while current_task.status != 'finished':
            time.sleep(10)
            current_task.status = get_crawl_status(
                scrapyd, current_task.task_id)
            if not current_task.status:
                current_task.status = 'finished'
            current_task.save()
            print('crawl status update loop: ', current_task.status)

        download_folder = process_download_folder(current_task.folder_name)

        context = {
            'keyword':  current_task.keyword,
            'start_date': current_task.start_date,
            'end_date': current_task.end_date,
            'folder': download_folder  # not empty only if there are downloads
        }
        current_task.delete()

    return render(request, resultTemplate, context)


# url: /main/csvdownload/
def csvdownload(request):
    ''' Display Tieba zip files available for downloading '''
    history = get_history()
    return render(request, 'main/csvdownload.html', context={'history': history})

# url: /main/pending/
def pending(request):
    ''' Display pending tieba and weibo tasks '''
    tieba_list = TiebaTask.objects.all()
    weibo_list = WeiboCrawlTask.ALL_WEIBO_TASKS
    date = datetime.datetime.now().strftime("%d %b %Y %H:%M:%S")
    
    context = {
        'date': date,
        'tieba_list': tieba_list,
        'weibo_list': weibo_list
    }
    return render(request, 'main/pending.html', context)


# url: /main/api/chart/analysis/
class ChartData(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, format=None):
        folder = request.GET.get('folder', None)
        summary, keywords, sentiments, stats, forums = read_analysis_from_csv(
            folder)

        data = {
            'summary': summary,
            'keywords': keywords,
            'sentiments': sentiments,
            'stats': stats,
            'forums': forums,
        }
        return Response(data)


# url: /main/api/chart/keywordsearch/
class KeywordSearchData(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, format=None):
        folder = request.GET.get('folder', None)
        search_input = request.GET.get('search_input', None).strip()
        keywords_with_frequency = None
        MAX = 10

        if folder and search_input and folder_exists(folder):
            file_path = (RESULTS_PATH / folder / 'replies.csv').resolve()
            # remove duplicates
            keywords = list(dict.fromkeys(search_input.split()))
            keywords = keywords[:min(MAX, len(keywords))]
            keywords_with_frequency = get_frequency_from_string_input(
                file_path, keywords)

        return Response(keywords_with_frequency)


# url: /main/api/history/tieba/
class TiebaHistoryData(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, format=None):

        history = get_history()
        history_tieba_dict = OrderedDict()
        for folder in history:
            tieba, daterange = get_tieba_and_daterange_from_folder(folder)
            if tieba not in history_tieba_dict.keys():
                history_tieba_dict[tieba] = [daterange]
            else:
                history_tieba_dict[tieba].append(daterange)
        data = dict(history_tieba_dict)

        return Response(data)


# url: /main/api/history/weibo/
class WeiboHistoryData(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, format=None):
        data = {'users': get_weibo_history()}
        return Response(data)


# url: /main/api/table/posts/
class WeiboTableData(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, format=None):
        folder_name = request.GET.get('folder', None)
        data = get_weibos_by_user(folder_name)
        return Response(data)