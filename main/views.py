from collections import OrderedDict
from uuid import uuid4
from urllib.parse import urlparse
import urllib.request
from urllib.parse import quote
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
from django.views.decorators.http import require_POST, require_http_methods
from django.shortcuts import render
from django.http import JsonResponse
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.views import APIView
from rest_framework.response import Response

from GTDjango.settings import CHROMEDRIVER_PATH, RESULTS_PATH, PROXIES_PATH
from .models import TiebaTask
from weibocrawler.weibo_crawler import *

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from scrapyd_api import ScrapydAPI

import asyncio
from bs4 import BeautifulSoup
import csv
import glob
import json
import os
import pandas as pd
from pathlib import Path
import shutil
from snownlp import SnowNLP
import sys
import time
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
        keyword = keyword_full[:-1] # remove the 'ba' character as it leads to a different link
        start_date = format_date(request.POST.get(
            'start_date_year', None), request.POST.get('start_date_month', None))
        end_date = format_date(request.POST.get(
            'end_date_year', None), request.POST.get('end_date_month', None))
        status = 'finished'

        if keyword and start_date and end_date:
            folder_name = create_directory(keyword_full, start_date, end_date)
            task_id, unique_id, status = schedule( # shedule tieba crawling task
                keyword, start_date, end_date, folder_name)

            current_task = TiebaTask()
            current_task.set_all_attributes(task_id, keyword, start_date, end_date, status, folder_name)
            current_task.save() # create task log in database
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
            folder_name = create_directory_weibo(uname) # folder_name should be same as uname
            current_task = WeiboCrawlTask(uid, uname)
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
    if task_type == 'tieba':
        task_id = request.GET.get('id', None)
        if task_id:
            scrapyd.cancel('default', task_id)
            current_task = TiebaTask.objects.filter(task_id = task_id).first()
            if current_task:
                delete_folder(RESULTS_PATH, current_task.folder_name)
                current_task.delete()
        
    elif task_type == 'weibo': # weibo
        folder_name = request.GET.get('id', None)
        if folder_name != None:
            WeiboCrawlTask.cancel_weibo_crawl(folder_name)
            delete_folder(WEIBO_RESULTS_PATH, folder_name)

    return render(request, 'main/cancel.html')


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
            is_ongoing_task = True if TiebaTask.objects.filter(folder_name = folder_name) else False
            data = {
                'Is_existed': exists,
                'is_ongoing_task': is_ongoing_task
            }
                
        elif request.POST.get('task_type') == 'weibo':
            info_dict = get_weibo_userid(request.POST.get('keyword', None))
            folder_name = info_dict['uname'] if info_dict else ''    
            is_ongoing_task = True if WeiboCrawlTask.get_task(folder_name) else False
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

    current_task = TiebaTask.objects.filter(task_id=request.POST.get('task_id')).first()
    if current_task:
        while current_task.status != 'finished':
            time.sleep(10)
            current_task.status = get_crawl_status(current_task.task_id)
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

        if folder and search_input and folderExists(folder):
            file_path = (RESULTS_PATH / folder / 'replies.csv').resolve()
            keywords = list(dict.fromkeys(search_input.split())) # remove duplicates
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
        data = { 'users' : get_weibo_history() }
        return Response(data)


# url: /main/api/table/posts/
class WeiboTableData(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, format=None):
        folder_name = request.GET.get('folder', None)
        data = get_weibos_by_user(folder_name)
        return Response(data)


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

def get_weibo_history():
    '''
    return list of users based on foldernames in /weiboresults/ folder
    '''
    dir_list = next(os.walk(WEIBO_RESULTS_PATH))[1]        
    return list(set(dir_list))

def get_weibo_userid(keyword):
    '''
        Return username and userid, crawling will rely on the userid.
        Notice:
            if the exact username is not in the suggested list, crawl the first name in suggest list.
    '''
    # url = "https://s.weibo.com/weibo?q=" + keyword +"&Refer=SWeibo_box"
    url = "https://s.weibo.com/user?q=" + keyword # +"&Refer=SUer_box"
    # url = quote(url, safe=string.printable)
    url = quote(url, safe='/:?=')
    html = urllib.request.urlopen(url).read().decode('utf-8')
    time.sleep(1)
    soup = BeautifulSoup(html,features='lxml')
    users = soup.find_all('div',{"class":'info'})
    names = {}
    for user in users:
        if user.select('.name .em') is not None:
            names.update({''.join(user.find('a',{"class":'name'}).text).strip() : user.find('a',{"class":'s-btn-c'})["uid"]})
    if names != {}:
        name_keys = list(names.keys())
        uname = keyword if keyword in names.keys() else name_keys[0] # if the exact username is not in the suggested list, crawl the first name in suggest list
        info_dict = {'uname': uname,'uid':names[uname]}
    else:
        info_dict = None
    print(info_dict)
    return info_dict


def get_weibos_by_user(folder_name):
    '''
        Return list of formatted posts of this user.
    '''
    all_weibos = []
    # all_cards = []
    # dir_list = next(os.walk(WEIBO_RESULTS_PATH))[1]
    if folder_name:
        # folder_name = folder_name + '/pages/'
        curr_path = (WEIBO_RESULTS_PATH / folder_name).resolve() 
        files = os.listdir(curr_path)
        os.chdir(curr_path)
        for jsonfile in files:
            # if zipfile.is_zipfile(jsonfile):
            if jsonfile[-5:] == '.json':
                with open(jsonfile,'r',encoding='utf-8',errors='ignore') as load_f:
                    weibo = json.load(load_f)
                    # all_cards = all_cards + weibos.get('cards')
                    all_weibos.append(weibo)
                    # print(all_cards)
        all_weibos = [{'text' : weibo.get("微博内容精简"),'created_at':weibo.get("发布时间"),'scheme':weibo.get("微博地址"),'reposts_count':weibo.get("转发数"),'comments_count':weibo.get("评论数"),'attitudes_count':weibo.get("点赞数")} for weibo in all_weibos]
    return all_weibos


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
        if files and zip_name in files:
            # if zip_name not in files:
            #     create_zip(curr_path, zip_name)
            folders.append(folder) # folders with zips indicate that the processing of scraped data has completed
    return folders


def create_zip(curr_path, zip_name):
    os.chdir(curr_path)
    files = os.listdir(curr_path)
    zipObj = ZipFile(zip_name, 'w')
    for f in files:
        zipObj.write(f)
    zipObj.close()


def read_csv_as_dict_list(file_to_read, headers):
    dict_list = []
    with open(file_to_read, 'r', encoding='utf-8') as f:
        reader = [l for l in csv.DictReader(f, headers) if l]
        for line in reader:
            dict_list.append(line)
    return dict_list


def get_related_forums_by_selenium(keyword):
    '''
        Return list of relevant forums based on the keyword.
    '''
    options = Options()
    options.headless = True
    browser = webdriver.Chrome(CHROMEDRIVER_PATH, chrome_options=options)
    browser.get('http://c.tieba.baidu.com/')

    keyword_list = keyword.split()
    if keyword not in keyword_list:
        keyword_list.append(keyword)
    relevant_forums_title = []
    # browser.implicitly_wait(1)  # time intervals given for scrapy to crawl
    for kw in keyword_list:
        forums = []
        forums = get_related_forum_one_kw(browser, kw)
        relevant_forums_title = relevant_forums_title + forums
    relevant_forums_title = {}.fromkeys(relevant_forums_title).keys()

    return list(relevant_forums_title)


def get_related_forum_one_kw(browser, keyword):
    try:
        search_textbox = browser.find_element_by_id("wd1")
        search_textbox.clear()
        search_textbox.send_keys(keyword)
        time.sleep(1)  # for fully rendering js
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
    except Exception as e:
        print(e)
        get_related_forum_one_kw(browser, keyword)
    return relevant_forums_title

def format_date(year, month):
    return '-'.join([year, month.zfill(2)])


def process_scraped_content(folder_name):
    folder_full_path = (RESULTS_PATH / folder_name).resolve()
    file_to_process = 'replies.csv'
    file_to_process_full_path = (
        RESULTS_PATH / folder_name / file_to_process).resolve()
    print('before get keyword summary')
    analysis = get_keyword_summary(file_to_process_full_path)
    print('after get keyword summary')
    summary, keywords, sentiments, stats = format_analysis_for_csv(analysis)

    write_to_csv(folder_full_path, 'summary.csv', summary)
    write_to_csv(folder_full_path, 'keywords.csv', keywords)
    write_to_csv(folder_full_path, 'sentiments.csv', sentiments)
    write_to_csv(folder_full_path, 'stats.csv', stats)


def process_download_folder(folder_name):
    '''
    Checks if there are files in the folder.
    If there are files, (1) create zip + return download path to the zip,
    (2) process scraped content
    Else if there are no files at all, return None
    '''
    download_folder = ''
    download_path_obj = (RESULTS_PATH / folder_name)
    download_path_full = download_path_obj.resolve()

    try:
        files = os.listdir(download_path_full)

        if 'replies.csv' in files:
            print('before process_scraped_content')
            process_scraped_content(folder_name)
            print('after process_scraped_content')

        if files:
            create_zip(download_path_full, folder_name + '.zip')
            download_folder = folder_name

        else:
            os.rmdir(download_path_full)
    except:
        print('Unable to continue processing downloading folder ',
              folder_name, ' as the folder has been deleted.')

    return download_folder


def process_download_folder_weibo(folder_name):
    # check if there are downloads
    download_path_obj = (WEIBO_RESULTS_PATH / folder_name)
    download_path_full = download_path_obj.resolve()
    files = os.listdir(download_path_full)
    download_folder = ''

    if files:
        # create_zip(download_path_full, folder_name + '.zip')
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


def create_directory_weibo(keyword):
    name = keyword
    os.chdir(WEIBO_RESULTS_PATH)
    if name in os.listdir(WEIBO_RESULTS_PATH):
        path = str((WEIBO_RESULTS_PATH/name).resolve()) +"/*"
        files = glob.glob(path)
        # files = glob.glob('/YOUR/PATH/*')
        for f in files:
            os.remove(f)
    else:    
        os.chdir(WEIBO_RESULTS_PATH)
        os.makedirs(name)
    return name   


def schedule(keyword, start_date, end_date, folder_name):
    '''
        Schedule scrapy task for tieba.
    '''
    unique_id = str(uuid4())  # create a unique ID.
    settings = {
        'unique_id': unique_id,  # unique ID for each record for DB
    }
    task = scrapyd.schedule('default', 'tiebacrawler', settings=settings, keyword=keyword, start_date=start_date,
                            end_date=end_date, folder_name=folder_name)
    return task, unique_id, 'started'


def get_crawl_status(task_id):
    '''
        Get task status for tieba.
    '''
    return scrapyd.job_status('default', task_id)


def delete_folder(path,name):
    os.chdir(path)
    shutil.rmtree(name)


def get_keyword_summary(file_path):

    #variables for sentiment analysis
    positive = 0
    negative = 0
    neutral = 0
	
    #read content
    #df = pd.read_csv(file_path, encoding='utf-8', header=None) #issue with unicode character in filepath
    with open(file_path, 'r', encoding='utf-8') as f:
        df = pd.read_csv(f, encoding='utf-8', header=None)
    print('replies.csv opened')

    #remove replies with null value
    df_nonull = df[pd.notnull(df[2])]
	
    keywords = []
    big_text = ""
	
    #loop through each row for keyword processing for single reply
    for text in df_nonull[2]:

        big_text += text + "。" #append text for summary processing later on
        s = SnowNLP(text) #initialize text as SnowNLP object
		
        #sentiment analysis
        sentiment = s.sentiments #value for sentiments, range from 0 to 1
        if sentiment > 0.7:
            positive += 1
        elif sentiment < 0.3:
            negative += 1
        else:
            neutral += 1
		
        #keyword extraction
        key = s.keywords(5) #get top 5 keywords of each reply
        #loop through each keyword
        for x in key:
            if len(x) > 1: #make sure keyword length is more than one, to prevent meaningless keyword
                keywords.append(x) #append to list

    print('end BIG FOR LOOP')

    #keyword processing for whole tieba
    dictionary = {'keyword': keywords} #convert to dictionary for creating dataframe
    keyword_df = pd.DataFrame(dictionary) #create dataframe
    result = keyword_df.keyword.value_counts().nlargest(10, keep='first') #get the top 10 keywords of the whole tieba based on count
	
    #variables for summary processing
    finalized_summary = []
    replies_id = []
    post_id = []
	
    #summary processing for whole tieba
    print('before SNOWNLP')
    s = SnowNLP(big_text)
    print('after SNOWNLP')
    
    #limit the number of summary based on replies count (1 summary every 5 replies up to a maximum of 5 summaries)
    calc_total_summary = int(df_nonull.shape[0] / 5) + 1 #add 1 to compensate for rounding down
    print('after calc_total_summary',calc_total_summary)
    if calc_total_summary < 5:
        summary = s.summary(calc_total_summary)
    else:
        summary = s.summary(5) #get top 5 summary (reply), truncation might happen in the summary
    print('SUMMARY')
    print(summary)

    #locating post and replies id
    no_dup_summary = list(set(summary)) #remove duplicates from summary (happens on certain dataset)
    print('before 2ND for loop for duplicate summary')
    for summ in no_dup_summary:

        sum_df = df_nonull[df_nonull[2].str.contains(summ, na=False)] #search dataframe for data containing the summary, substring of the actual list
        
        #loop through each of the dataframe, if the substring is short, might increase the number of summary found by a lot
        for i in range(sum_df.shape[0]):
            post_id.append(sum_df.iloc[i][0])            #post id
            replies_id.append(sum_df.iloc[i][1])         #replies id
            finalized_summary.append(sum_df.iloc[i][2])  #summary, obtain it again since we have removed duplicates

    return {'post_id': post_id, 'replies_id': replies_id, 'replies_count': df_nonull.shape[0], 'summary': finalized_summary, 'keyword': dict(result), 'positive': positive, 'negative': negative, 'neutral': neutral} #return a dictionary, json.dumps if needed
	

def format_analysis_for_csv(analysis):
    summary = [(item, analysis['post_id'][index], analysis['replies_id'][index])
               for index, item in enumerate(analysis['summary'])]
    keywords = [
        keyword_and_count for keyword_and_count in analysis['keyword'].items()]  # list of dict
    sentiments = [
        ('positive', analysis['positive']),
        ('negative', analysis['negative']),
        ('neutral', analysis['neutral'])
    ]
    stats = [('replies_count', analysis['replies_count'])]

    return summary, keywords, sentiments, stats


def write_to_csv(folder_full_path, filename, data):
    os.chdir(folder_full_path)
    with open(filename, 'w', encoding='utf-8', newline='') as f:
        csv.writer(f, dialect="excel").writerows(data)


def folderExists(folder):
    history = get_history()
    return history and folder in history


def read_analysis_from_csv(folder):
    download_path_obj = (RESULTS_PATH / folder)
    os.chdir(download_path_obj.resolve())
    files = os.listdir(download_path_obj)
    summary = sentiments = keywords = top_forums = stats = None
    url_template = 'https://tieba.baidu.com/p/%s#post_content_%s'

    if 'summary.csv' in files:
        with open('summary.csv', newline='', encoding='utf-8') as f:
            summary = list(csv.reader(f, delimiter=',',
                                      quotechar='|', dialect="excel"))
            summary = [(s[0], url_template % (s[1], s[2])) for s in summary]

        with open('stats.csv', 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            stats = {rows[0]: rows[1] for rows in reader}

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

        total = len(forums)
        MAX = 20 # Too many irrelevant tiebas, take top hits will do
        top = MAX if total > MAX else total
        forums = sorted(forums, key=lambda x: int(
            x['count']), reverse=True)[:top]

        # convert to simple dict for easy ref by front-end
        top_forums = {pair['tieba']: pair['count'] for pair in forums}

    return summary, keywords, sentiments, stats, top_forums


def get_frequency_from_string_input(file_path, input_list):
    counter = {}
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            df = pd.read_csv(f, encoding='utf-8', header=None)

        df_nonull = df[pd.notnull(df[2])]
        df_nonull.head()
        counter = {}
        for i in input_list:
            count_df = df_nonull[df_nonull[2].str.contains(i, na=False)]
            counter.update({i: len(count_df)})
    except:
        print(sys.exc_info()[0])
    return counter