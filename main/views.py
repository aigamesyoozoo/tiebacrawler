from collections import OrderedDict
import sys
from uuid import uuid4
from urllib.parse import urlparse
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
from django.views.decorators.http import require_POST, require_http_methods
from django.shortcuts import render
from django.http import JsonResponse
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.views import APIView
from rest_framework.response import Response

from GTDjango.settings import CHROMEDRIVER_PATH, TIEBACOUNT_PATH, RESULTS_PATH, WEIBO_RESULTS_PATH
from weibocrawler.weibo_crawler import *
import runpy
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from scrapyd_api import ScrapydAPI
import time
import os
import csv
from pathlib import Path
from zipfile import ZipFile
import json
import shutil

import urllib.request
from urllib.parse import quote
import string
from snownlp import SnowNLP
import pandas as pd


scrapyd = ScrapydAPI('http://localhost:6800')


def index(request):

    history = get_history()
    history_tieba = set()
    for folder in history:
        history_tieba.add(get_tiebaname_from_folder(folder))
    history_tieba_sorted = list(history_tieba)
    history_tieba_sorted.sort()
    return render(request, 'main/index.html', context={'history': history, 'history_tieba': history_tieba_sorted})


def get_tiebaname_from_folder(folder):
    parts = folder.split('_')
    if len(parts) is 3:
        return parts[0]
    else:
        return '_'.join(parts[:-2])


def get_tieba_and_daterange_from_folder(folder):
    parts = folder.split('_')
    tieba = parts[0] if len(parts) is 3 else '_'.join(parts[:-2])
    dates = '_'.join(parts[-2:])
    return tieba, dates

def get_weibouser_and_daterange_from_folder(folder):
    parts = folder.split('_')
    weibouser = parts[0] if len(parts) is 3 else '_'.join(parts[:-2])
    dates = '_'.join(parts[-2:])
    return weibouser, dates

def popular_tiebas_among_users_who_posted(tieba_count_path):
    headers = ['tieba', 'count']
    all_forums = read_csv_as_dict_list(tieba_count_path, headers)
    if all_forums:
        all_forums.sort(key=lambda x: int(x['count']), reverse=True)
    for f in all_forums:
        # replace / with a safe character
        f['cleaned_name'] = f['tieba'].replace('/', '^')
    return all_forums


def get_history():
    dir_list = next(os.walk(RESULTS_PATH))[1]
    folders = []
    for folder in dir_list:
        zip_name = folder + '.zip'
        curr_path = (RESULTS_PATH / folder).resolve()
        files = os.listdir(curr_path)
        if files:
            if zip_name not in files:
                create_zip(curr_path, zip_name)
            folders.append(folder)
    return folders

def get_weibo_history():
    '''
    return dict for dropdown
    key: user ,value:[date1,date2]
    '''
    dir_list = next(os.walk(WEIBO_RESULTS_PATH))[1]
    weibo_history_dict = OrderedDict()
    for folder in dir_list:
        weibouser, daterange = get_weibouser_and_daterange_from_folder(folder)
        if weibouser not in weibo_history_dict.keys():
            weibo_history_dict[weibouser] = [daterange]
        else:
            weibo_history_dict[weibouser].append(daterange)
    weibo_history_dict = json.dumps(dict(weibo_history_dict))
        
    return weibo_history_dict

def create_zip(curr_path, zip_name):
    os.chdir(curr_path)
    files = os.listdir(curr_path)
    zipObj = ZipFile(zip_name, 'w')
    for f in files:
        zipObj.write(f)
    zipObj.close()


def history(request):  # contains duplicate code with index()
    history = get_history()
    history_tieba_dict = OrderedDict()
    for folder in history:
        tieba, daterange = get_tieba_and_daterange_from_folder(folder)
        if tieba not in history_tieba_dict.keys():
            history_tieba_dict[tieba] = [daterange]
        else:
            history_tieba_dict[tieba].append(daterange)
    history_tieba_dict = json.dumps(dict(history_tieba_dict))
    return render(request, 'main/history.html', context={'history_tieba_dict': history_tieba_dict})


def read_csv_as_dict_list(file_to_read, headers):
    dict_list = []
    with open(file_to_read, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, headers)
        for line in reader:
            dict_list.append(line)
    return dict_list


def rehome(request, tieba):
    if request.method == 'GET':
        return render(request, 'main/home.html', {'forums': [tieba.replace('^', '/')]})


def home(request):
    keyword = request.GET.get('kw')
    tieba = request.GET.get('tieba')
    forums = []  # cater for else condition
    if keyword:
        print('keyword', keyword)
        forums = get_related_forums_by_selenium(keyword)
        # forums = ['a', 'b', 'c', 'd']
    elif tieba:
        print('tieba', tieba)
        forums = [tieba.replace('^', '/')]
    return render(request, 'main/home.html', context={'forums': forums})

# WEIBO Process Part
def make_weibo_task(request):

    if request.method == "GET":
        keyword = request.GET.get('kw')
        if keyword:
            print('keyword',keyword)
            info_dict = get_weibo_userid(keyword)
            uid = info_dict['uid']
            uname = info_dict['uname']
            start_date='2019-06'
            end_date='2019-07'
            folder_name = create_directory_weibo(uname,start_date,end_date)
            
        crawl_weibo(uid,folder_name)        
      
    download_folder = process_download_folder_weibo(uname)

    context = {
        'keyword':  keyword,
        'folder': download_folder  # not empty only if there are downloads
    }
        # import subprocess

        # subprocess.run(['python', r'./weibocrawler/weibo_crawler.py', uid],stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        # runpy.run_path(r'./weibocrawler/weibo_crawler.py', run_name='__main__')

    return render(request, 'main/weiboresult.html',context)


def get_weibo_userid(keyword):
    # url = "https://s.weibo.com/weibo?q=" + keyword +"&Refer=SWeibo_box"
    url = "https://s.weibo.com/user?q=" + keyword # +"&Refer=SUer_box"
    # url = quote(url, safe=string.printable)
    url = quote(url, safe='/:?=')
    html = urllib.request.urlopen(url).read().decode('utf-8')
    time.sleep(0.1)
    soup = BeautifulSoup(html,features='lxml')
    name_elem = soup.find('a',{"class":'name'})
    id_elem = soup.find('a',{"class":'s-btn-c'})
    
    info_dict = {'uname': ''.join(name_elem.em.text).strip(),'uid':str(id_elem["uid"])} #.encode('gbk')
    print(info_dict)
    return info_dict

# TODO
def weibo_history(request):
    # get a lsit of dicts with {user:,date:,data:[{contents:,counts:,counts:,counts:}]}

    folder_name = request.GET.get('kw')
    weibos = get_weibos_by_user_range(folder_name)
    # print(weibos)
    context={
        'weibos':weibos
    }
    return render(request,'main/weibohistory.html',context)

def get_weibos_by_user_range(folder_name = ''):
    all_weibos = []
    all_cards = []
    # dir_list = next(os.walk(WEIBO_RESULTS_PATH))[1]
    if folder_name != '':
        folder_name = folder_name + '/pages/'
        curr_path = (WEIBO_RESULTS_PATH / folder_name).resolve() 
        files = os.listdir(curr_path)
        os.chdir(curr_path)
        for jsonfile in files:
            with open(jsonfile,'r', encoding='utf-8') as load_f:
                weibos = json.load(load_f)
                all_cards = all_cards + weibos.get('cards')
                # print(all_cards)
        all_weibos = [{'text' : card.get('mblog').get('text'),'reposts_count':card.get('mblog').get('reposts_count'),'comments_count':card.get('mblog').get('comments_count'),'attitudes_count':card.get('mblog').get('attitudes_count')} for card in all_cards]
    return all_weibos


def get_related_forums_by_selenium(keyword):
    options = Options()
    options.headless = True
    browser = webdriver.Chrome(CHROMEDRIVER_PATH, chrome_options=options)
    browser.get('http://c.tieba.baidu.com/')

    keyword_list = keyword.split()
    keyword_list.append(keyword)
    relevant_forums_title = []
    # browser.implicitly_wait(1)  # time intervals given for scrapy to crawl
    for kw in keyword_list:
        forums = []
        forums = get_related_forum_one_kw(browser, kw)
        relevant_forums_title = relevant_forums_title + forums

    return set(relevant_forums_title)


def get_related_forum_one_kw(browser, keyword):
    search_textbox = browser.find_element_by_id("wd1")
    search_textbox.clear()
    search_textbox.send_keys(keyword)
    time.sleep(1)  # for fully rendering js
    # relevant_forums_title = []
    # relevant_forums_webelements = []
    # relevant_forums_data = []
    webelements_json = []
    relevant_forums_webelements = browser.find_elements_by_css_selector(
        ".suggestion_list > li")
    relevant_forums_data = [webelement.get_attribute(
        "data-field") for webelement in relevant_forums_webelements]
    if relevant_forums_data is not []:
        for webelement_json in relevant_forums_data:
            temp = json.loads(str(webelement_json))
            webelements_json.append(temp)
        relevant_forums_title = [webelement_json['sugValue'] +
                                 '吧' for webelement_json in webelements_json if str(webelement_json['sugType']) in ["forum_item"]]
    return relevant_forums_title


@csrf_exempt
def validate_Isexisted(request):
    if request.method == 'POST':
        dir_list = next(os.walk(RESULTS_PATH))[1]

        keyword = request.POST.get('keyword', None)
        start_date = format_date(request.POST.get(
            'start_date_year', None), request.POST.get('start_date_month', None))
        end_date = format_date(request.POST.get(
            'end_date_year', None), request.POST.get('end_date_month', None))
        folder_name = '_'.join([keyword, start_date, end_date])

        if folder_name not in dir_list:
            data = {
                'Is_existed': False
            }
        else:
            data = {
                'Is_existed': True
            }
        return JsonResponse(data)


@csrf_exempt
@require_http_methods(['POST', 'GET'])  # only get and post
def crawl(request):
    if request.method == 'POST':

        keyword_full = request.POST.get('keyword', None)
        # remove the 'ba' character as it leads to a different link
        keyword = keyword_full[:-1]
        start_date = format_date(request.POST.get(
            'start_date_year', None), request.POST.get('start_date_month', None))
        end_date = format_date(request.POST.get(
            'end_date_year', None), request.POST.get('end_date_month', None))
        print('NEW>>>', start_date, end_date)

        status = 'finished'
        if keyword and start_date and end_date:
            folder_name = create_directory(keyword_full, start_date, end_date)
            task_id, unique_id, status = schedule(
                keyword, start_date, end_date, folder_name)

            print(task_id, unique_id, status)

            request.session['task_id'] = task_id
            request.session['status'] = status
            request.session['folder_name'] = folder_name
            request.session['keyword'] = keyword
            request.session['start_date'] = start_date
            request.session['end_date'] = end_date

            data = {
                "Is_submitted": True,
                "task_id": task_id
            }
        else:
            data = {
                "Is_submitted": False
            }
        return JsonResponse(data)


@csrf_exempt
def downloaded(request):
    print(request.session.items())
    while request.session['status'] is not 'finished':
        time.sleep(10)
        request.session['status'] = get_crawl_status(
            request, request.session['task_id'])
        print('crawl status update loop: ', request.session['status'])

    all_forums, download_folder = process_download_folder(
        request.session['folder_name'])

    context = {
        'keyword':  request.session['keyword'],
        'start_date': request.session['start_date'],
        'end_date': request.session['end_date'],
        'success': request.session['status'],
        'forums': all_forums,  # can be empty if no forums found
        'folder': download_folder  # not empty only if there are downloads
    }

    request.session['keyword'] = request.session['start_date'] = request.session['end_date'] = request.session['folder_name'] = ''

    return render(request, 'main/result.html', context)


def format_date(year, month):
    return '-'.join([year, month.zfill(2)])


def process_scraped_content(folder_name):
    folder_full_path = (RESULTS_PATH / folder_name).resolve()
    file_to_process = 'replies.csv'
    file_to_process_full_path = (
        RESULTS_PATH / folder_name / file_to_process).resolve()

    analysis = get_keyword_summary(file_to_process_full_path)
    summary, keywords, sentiments = format_analysis_for_csv(analysis)

    write_to_csv(folder_full_path, 'summary.csv', summary)
    write_to_csv(folder_full_path, 'keywords.csv', keywords)
    write_to_csv(folder_full_path, 'sentiments.csv', sentiments)


def process_download_folder(folder_name):
    '''
    Checks if there are files in the folder.
    If there are files, (1) create zip + return download path to the zip,
    (2) process scraped content, and 
    (3) return list of popular tiebas.
    Else if there are no files at all, return None
    '''
    download_path_obj = (RESULTS_PATH / folder_name)
    download_path_full = download_path_obj.resolve()
    files = os.listdir(download_path_full)
    download_folder = ''
    all_forums = []

    if 'replies.csv' in files:
        process_scraped_content(folder_name)

    if files:
        create_zip(download_path_full, folder_name + '.zip')
        download_folder = folder_name
        if 'tieba_count.csv' in files:
            tieba_count_path = (download_path_obj /
                                'tieba_count.csv').resolve()
            all_forums = popular_tiebas_among_users_who_posted(
                tieba_count_path)
    else:
        os.rmdir(download_path_full)

    return all_forums, download_folder

def process_download_folder_weibo(folder_name):
    # check if there are downloads
    download_path_obj = (WEIBO_RESULTS_PATH / folder_name)
    download_path_full = download_path_obj.resolve()
    files = os.listdir(download_path_full)
    download_folder = ''

    if files:
        create_zip(download_path_full, folder_name + '.zip')
        download_folder = folder_name

    return download_folder

def create_directory(keyword, start_date, end_date):
    name = '_'.join([keyword, start_date, end_date])
    os.chdir(RESULTS_PATH)
    if name in os.listdir(RESULTS_PATH):
        shutil.rmtree(name)

    os.chdir(RESULTS_PATH)
    os.makedirs(name)
    return name

def create_directory_weibo(keyword, start_date, end_date):
    name = '_'.join([keyword, start_date, end_date])
    os.chdir(WEIBO_RESULTS_PATH)
    if name in os.listdir(WEIBO_RESULTS_PATH):
        shutil.rmtree(name)
    os.chdir(WEIBO_RESULTS_PATH)
    os.makedirs(name)  
    return name    

def schedule(keyword, start_date, end_date, folder_name):
    # global task
    unique_id = str(uuid4())  # create a unique ID.
    settings = {
        'unique_id': unique_id,  # unique ID for each record for DB
    }
    task = scrapyd.schedule('default', 'tiebacrawler', settings=settings, keyword=keyword, start_date=start_date,
                            end_date=end_date, folder_name=folder_name)
    return task, unique_id, 'started'


def get_crawl_status(request, task_id):
    return scrapyd.job_status('default', request.session['task_id'])


def delete_folder(name):
    os.chdir(RESULTS_PATH)
    shutil.rmtree(name)


def cancel(request):
    scrapyd.cancel('default', request.session['task_id'])
    delete_folder(request.session['folder_name'])

    request.session['keyword'] = request.session['start_date'] = request.session[
        'end_date'] = request.session['folder_name'] = request.session['task_id'] = ''

    return render(request, 'main/cancel.html')


def get_keyword_summary(file_path):
    # variables for sentiment analysis
    positive = 0
    negative = 0
    neutral = 0

    # read content
    # df = pd.read_csv(file_path, encoding='utf-8', header=None) #issue with unicode character in filepath
    with open(file_path, 'r', encoding='utf-8') as f:
        df = pd.read_csv(f, encoding='utf-8', header=None)

    # remove replies with null value
    df_nonull = df[pd.notnull(df[2])]

    keywords = []
    big_text = ""

    # loop through each row for keyword processing for single reply
    for text in df_nonull[2]:
        big_text += text + "。"  # append text for summary processing later on
        s = SnowNLP(text)  # initialize text as SnowNLP object

        # sentiment analysis
        sentiment = s.sentiments  # value for sentiments, range from 0 to 1
        if sentiment > 0.7:
            positive += 1
        elif sentiment < 0.3:
            negative += 1
        else:
            neutral += 1

        # keyword extraction
        key = s.keywords(5)  # get top 5 keywords of each reply
        # loop through each keyword
        for x in key:
            if len(x) > 1:  # make sure keyword length is more than one, to prevent meaningless keyword
                keywords.append(x)  # append to list

    # keyword processing for whole tieba
    # convert to dictionary for creating dataframe
    dictionary = {'keyword': keywords}
    keyword_df = pd.DataFrame(dictionary)  # create dataframe
    # get the top 10 keywords of the whole tieba based on count
    result = keyword_df.keyword.value_counts().nlargest(10, keep='first')

    # summary processing for whole tieba
    s = SnowNLP(big_text)
    summary = s.summary(5)  # get top 5 summary (reply)

    print(summary)
    print(dict(result))
    print(positive)
    print(negative)
    print(neutral)

    # return a dictionary, json.dumps if needed
    return {'summary': summary, 'keyword': dict(result), 'positive': positive, 'negative': negative, 'neutral': neutral}


def format_analysis_for_csv(analysis):
    summary = [[item] for item in analysis['summary']]  # list
    keywords = [
        keyword_and_count for keyword_and_count in analysis['keyword'].items()]
    sentiments = [
        ('positive', analysis['positive']),
        ('negative', analysis['negative']),
        ('neutral', analysis['neutral'])
    ]
    return summary, keywords, sentiments


def write_to_csv(folder_full_path, filename, data):
    os.chdir(folder_full_path)
    with open(filename, 'w', encoding='utf-8', newline='') as f:
        csv.writer(f, dialect="excel").writerows(data)


class ChartData(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, format=None):
        folder = request.GET.get('folder', None)

        summary, keywords, sentiments, forums = read_analysis_from_csv(
            folder)

        data = {
            'summary': summary,
            'keywords': keywords,
            'sentiments': sentiments,
            'forums': forums,
        }
        return Response(data)


def read_analysis_from_csv(folder):
    download_path_obj = (RESULTS_PATH / folder)
    os.chdir(download_path_obj.resolve())
    files = os.listdir(download_path_obj)
    summary = sentiments = keywords = forums = None

    if 'summary.csv' in files:
        with open('summary.csv', newline='', encoding='utf-8') as f:
            summary = list(csv.reader(f, delimiter=',',
                                      quotechar='|', dialect="excel"))
            summary = [s[0] for s in summary]

        with open('sentiments.csv', 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            sentiments = {rows[0]: rows[1] for rows in reader}

        with open('keywords.csv', 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            keywords = {rows[0]: rows[1] for rows in reader}

    tieba_count_filename = 'tieba_count.csv'
    if tieba_count_filename in files:
        with open(tieba_count_filename, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            forums = [{'tieba': rows[0], 'count':rows[1]} for rows in reader]

        # # Too many irrelevant tiebas, take top hits will do
        total = len(forums)
        max = 20
        top = max if total > max else total
        forums = sorted(forums, key=lambda x: int(
            x['count']), reverse=True)[:top]

        # convert to simple dict for easy ref by front-end
        top_forums = {pair['tieba']: pair['count'] for pair in forums}

    return summary, keywords, sentiments, top_forums
