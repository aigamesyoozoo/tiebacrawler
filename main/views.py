from uuid import uuid4
from urllib.parse import urlparse
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
from django.views.decorators.http import require_POST, require_http_methods
from django.shortcuts import render
from django.http import JsonResponse
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

from GTDjango.settings import CHROMEDRIVER_PATH, TIEBACOUNT_PATH, RESULTS_PATH

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


scrapyd = ScrapydAPI('http://localhost:6800')

def index(request):
    
    history = get_history()
    history_tieba = set()
    for folder in history:
        history_tieba.add(get_tiebaname_from_folder(folder))
    history_tieba_sorted = list(history_tieba)
    history_tieba_sorted.sort()
    time.sleep(15)
    return render(request, 'main/index.html', context={'history': history, 'history_tieba': history_tieba_sorted})


def get_tiebaname_from_folder(folder):
    parts = folder.split('_')
    if len(parts) is 3:
        return parts[0]
    else:
        return '_'.join(parts[:-2])


def downloading(request):
    return render(request, 'main/downloading.html')


def popular_tiebas_among_users_who_posted(tieba_count_path):
    all_forums = read_csv_as_dict_list(tieba_count_path)
    if all_forums:
        all_forums.sort(key=lambda x: int(x['count']), reverse=True)
    for f in all_forums:
        # replace / with a safe character
        f['cleaned_name'] = f['tieba'].replace('/', '^')
    return all_forums


# DEBUGGING ONLY
# direct view of results.html for debugging purposes
def result(request):
    test_tieba_count_path = (
        RESULTS_PATH / 'c吧_2019-06_2019-06' / 'tieba_count.csv').resolve()
    all_forums = popular_tiebas_among_users_who_posted(test_tieba_count_path)
    print(all_forums)
    context = {
        'folder': 'blah blah',
        'forums': all_forums
    }
    return render(request, 'main/result.html', context)


def get_history():
    dir_list = next(os.walk(RESULTS_PATH))[1]
    folders = []
    for folder in dir_list:
        zip_name = folder + '.zip'
        curr_path = (RESULTS_PATH / folder).resolve()
        files = os.listdir(curr_path)
        if files:
            if zip_name not in files:
                create_zip(curr_path, zip_name, files)
            folders.append(folder)
    return folders


def create_zip(curr_path, zip_name, files):
    os.chdir(curr_path)
    zipObj = ZipFile(zip_name, 'w')
    for f in files:
        zipObj.write(f)
    zipObj.close()


def history(request):
    dir_list = next(os.walk(RESULTS_PATH))[1]
    folders = []
    for folder in dir_list:
        curr_path = (RESULTS_PATH / folder).resolve()
        os.chdir(curr_path)  # only can read files (.csv) in working directory
        files = os.listdir(curr_path)
        if files:
            zipObj = ZipFile(folder + '.zip', 'w')
            for f in files:
                zipObj.write(f)
            zipObj.close()
            folders.append(folder)
    folders.sort()
    context = {
        'folders': folders
    }
    return render(request, 'main/history.html', context)


def read_csv_as_dict_list(file_to_read):
    dict_list = []
    with open(file_to_read, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, ['tieba', 'count'])
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


def get_related_forums_by_selenium(keyword):
    options = Options()
    options.headless = True
    browser = webdriver.Chrome(CHROMEDRIVER_PATH, chrome_options=options)
    # browser = webdriver.Chrome(CHROMEDRIVER_PATH)
    browser.get('http://c.tieba.baidu.com/')

    keyword_list = keyword.split()  # filter(None,str.split(" "))
    keyword_list.append(keyword)
    relevant_forums_title = []
    # browser.implicitly_wait(1)  # time intervals given for scrapy to crawl
    # search_textbox = browser.find_element_by_id("wd1")
    for kw in keyword_list:
        forums = []
        forums = get_related_forum_one_kw(browser, kw)
        relevant_forums_title = relevant_forums_title + forums
    # browser.quit()

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
    # relevant_forums_webelements = browser.find_elements_by_css_selector(
    #     ".forum_name , .highlight")
    # relevant_forums_title = [forum.text for index, forum in enumerate(

    #     relevant_forums_webelements) if index % 2 == 0 or index > 7]
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
        start_date = format_date(request.POST.get('start_date_year', None), request.POST.get('start_date_month', None))
        end_date = format_date(request.POST.get('end_date_year', None), request.POST.get('end_date_month', None))
        folder_name = '_'.join([keyword, start_date, end_date])

        if folder_name not in dir_list:
            data={
                'Is_existed' : False
            }
        else :
            data={
                'Is_existed' : True
            }
        return JsonResponse(data)


@csrf_exempt
@require_http_methods(['POST', 'GET'])  # only get and post
def crawl(request):
    if request.method == 'POST':

        # global keyword, start_date, end_date, folder_name

        keyword_full = request.POST.get('keyword', None)
        # remove the 'ba' character as it leads to a different link
        keyword = keyword_full[:-1]
        start_date = format_date(request.POST.get('start_date_year', None), request.POST.get('start_date_month', None))
        end_date = format_date(request.POST.get('end_date_year', None), request.POST.get('end_date_month', None))
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
                "Is_submitted" : True,
                "task_id" : task_id
            }
        else:
            data = {
                "Is_submitted" : False
            }
        return JsonResponse(data)

@csrf_exempt
def downloaded(request):
    while request.session['status'] is not 'finished':
        time.sleep(10)
        request.session['status'] = get_crawl_status(request, request.session['task_id'])
        print('crawl status update loop: ', request.session['status'])

    all_forums, download_folder = process_download_folder(request.session['folder_name'])

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


# @csrf_exempt
# @require_http_methods(['POST', 'GET'])  # only get and post
# def crawl(request):
#     if request.method == 'POST':

#         global keyword, start_date, end_date, folder_name

#         keyword_full = request.POST.get('keyword', None)
#         # remove the 'ba' character as it leads to a different link
#         keyword = keyword_full[:-1]
#         start_date = format_date(request.POST.get('start_date_year', None), request.POST.get('start_date_month', None))
#         end_date = format_date(request.POST.get('end_date_year', None), request.POST.get('end_date_month', None))

#         # start_date_year = request.POST.get('start_date_year', None)
#         # start_date_month = request.POST.get('start_date_month', None)
#         # if len(start_date_month) is 1:
#         #     start_date_month = "0" + start_date_month
#         # start_date = '-'.join([start_date_year, start_date_month])

#         # end_date_year = request.POST.get('end_date_year', None)
#         # end_date_month = request.POST.get('end_date_month', None)
#         # if len(end_date_month) is 1:
#         #     end_date_month = "0" + end_date_month
#         # end_date = '-'.join([end_date_year, end_date_month])
#         print('NEW>>>', start_date, end_date)

#         status = 'finished'
#         if keyword and start_date and end_date:
#             folder_name = create_directory(keyword_full, start_date, end_date)
#             task_id, unique_id, status = schedule(
#                 keyword, start_date, end_date, folder_name)

#             print(task_id, unique_id, status)

#         while status is not 'finished':
#             time.sleep(10)
#             status = get_crawl_status(task_id)
#             print('crawl status update loop: ', status)

#         all_forums, download_folder = process_download_folder(folder_name)

#         context = {
#             'keyword': keyword,
#             'start_date': start_date,
#             'end_date': end_date,
#             'success': status,
#             'forums': all_forums,  # can be empty if no forums found
#             'folder': download_folder  # not empty only if there are downloads
#         }

#         keyword = start_date = end_date = folder_name = ''

#         return render(request, 'main/result.html', context)

def format_date(year, month):
    return '-'.join([year, month.zfill(2)])


def process_download_folder(folder_name):
    # check if there are downloads
    download_path_obj = (RESULTS_PATH / folder_name)
    download_path_full = download_path_obj.resolve()
    files = os.listdir(download_path_full)
    download_folder = ''
    all_forums = []
    if files:
        create_zip(download_path_full, folder_name + '.zip', files)
        download_folder = folder_name
        if 'tieba_count.csv' in files:
            tieba_count_path = (download_path_obj /
                                'tieba_count.csv').resolve()
            all_forums = popular_tiebas_among_users_who_posted(
                tieba_count_path)

    return all_forums, download_folder


# def create_directory(keyword, start_date, end_date):
#     name = '_'.join([keyword, start_date, end_date])
#     if name not in os.listdir(RESULTS_PATH):
#         os.chdir(RESULTS_PATH)
#         os.makedirs(name)        
#     return name

def create_directory(keyword, start_date, end_date):
    name = '_'.join([keyword, start_date, end_date])
    os.chdir(RESULTS_PATH)
    if name in os.listdir(RESULTS_PATH):
        shutil.rmtree(name)

    os.chdir(RESULTS_PATH)
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
    # print('------------------------------')
    # print(task)
    # global task, keyword, start_date, end_date, folder_name

    scrapyd.cancel('default', request.session['task_id'])
    delete_folder(request.session['folder_name'])

    # all_forums, download_folder = process_download_folder(
    #     request.session['folder_name'])

    context = {
    #     'keyword':  request.session['keyword'],
    #     'start_date': request.session['start_date'],
    #     'end_date': request.session['end_date'],
    #     'success': '',  # empty indicates that success message will not be printed
    #     'forums': all_forums,
    #     'folder': download_folder  # not empty only if there are downloads       
    }

    # keyword = start_date = end_date = folder_name = ''
    request.session['keyword'] = request.session['start_date'] = request.session['end_date'] = request.session['folder_name'] =  request.session['task_id']=''

    return render(request, 'main/cancel.html', context)
