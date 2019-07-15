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

from GTDjango.settings import CHROMEDRIVER_PATH, TIEBACOUNT_PATH, RESULTS_PATH, PROXIES_PATH

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

from snownlp import SnowNLP
import pandas as pd

from weibocrawler.weibo_crawler import *
import asyncio
# from proxybroker import Broker
from bs4 import BeautifulSoup
import urllib.request
from urllib.parse import quote


import zipfile
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

def get_weibo_history():
    '''
    return list of users based on foldernames in /weiboresults/ folder
    '''
    dir_list = next(os.walk(WEIBO_RESULTS_PATH))[1]        
    return list(set(dir_list))

def get_weibo_userid(keyword):
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


def weibo_history(request):
    # get a lsit of dicts with {user:,date:,data:[{contents:,counts:,counts:,counts:}]}

    folder_name = request.GET.get('kw')
    weibos = get_weibos_by_user(folder_name)
    # print(weibos)
    context={
        'weibos':weibos
    }
    return render(request,'main/weibohistory.html',context)

def get_weibos_by_user(folder_name):
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
        if files:
            if zip_name not in files:
                create_zip(curr_path, zip_name)
            folders.append(folder)
    return folders


def create_zip(curr_path, zip_name):
    os.chdir(curr_path)
    files = os.listdir(curr_path)
    zipObj = ZipFile(zip_name, 'w')
    for f in files:
        zipObj.write(f)
    zipObj.close()


def history_tieba(request):
    return render(request, 'main/history_tieba.html')


def history_weibo(request):
    return render(request, 'main/history_weibo.html')


def read_csv_as_dict_list(file_to_read, headers):
    dict_list = []
    with open(file_to_read, 'r', encoding='utf-8') as f:
        reader = [l for l in csv.DictReader(f, headers) if l]
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
    return relevant_forums_title


@csrf_exempt
def validate_Isexisted(request):
    if request.method == 'POST':
        print('keyword',request.POST.get('keyword'))
        print('validate',request.POST.get('task_type'))
        if request.POST.get('task_type') == 'tieba':
            dir_list = next(os.walk(RESULTS_PATH))[1]
            keyword = request.POST.get('keyword', None)
            start_date = format_date(request.POST.get(
                'start_date_year', None), request.POST.get('start_date_month', None))
            end_date = format_date(request.POST.get(
                'end_date_year', None), request.POST.get('end_date_month', None))
            keyword = request.POST.get('keyword', None)
            folder_name = '_'.join([keyword, start_date, end_date])
                
        elif request.POST.get('task_type') == 'weibo':
            request.session['status'] = 'not finished'
            dir_list = next(os.walk(WEIBO_RESULTS_PATH))[1]
            # start_date = '2019-06'
            # end_date = '2019-07'
            info_dict = get_weibo_userid(request.POST.get('keyword', None))
            keyword = info_dict['uname'] if info_dict is not None else ''
        
            folder_name = keyword

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
def make_tieba_task(request):
    '''
    Able to crawl multiple tieba concurrently by browser.
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
        print('NEW>>>', start_date, end_date)

        status = 'finished'
        if keyword and start_date and end_date:
            folder_name = create_directory(keyword_full, start_date, end_date)
            task_id, unique_id, status = schedule(
                keyword, start_date, end_date, folder_name)

            print(task_id, unique_id, status)
            request.session['task_type'] = 'tieba'
            request.session['task_id'] = task_id
            request.session['status'] = status
            request.session['folder_name'] = folder_name
            request.session['keyword'] = keyword
            request.session['start_date'] = start_date
            request.session['end_date'] = end_date
            request.session.modified = True
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
def make_weibo_task(request):
    '''
    Currently can only crawl one weibo task at a time.
    '''
    if request.method == "POST":
        print('welcome to weibo task:')
        request.session['weibo_keyword'] = request.POST.get('keyword')
        if request.session['weibo_keyword']:
            request.session['task_type'] = 'weibo'
            print('weibo_keyword',request.session['weibo_keyword'])
            print('task_type:',request.session['task_type'] )
            info_dict = get_weibo_userid(request.session['weibo_keyword'])
            if info_dict is not None:
                request.session['uid'] = info_dict['uid']
                request.session['uname'] = info_dict['uname']
                request.session['weibo_folder_name'] = create_directory_weibo(request.session['uname'])             
                request.session['weibo_status'] = 'not finished'
                # print('before sumission :',request.session.items())
                request.session.modified = True
                                
                crawl_weibo(request.session['uid'],request.session['weibo_folder_name'])
                # print('after sumission :',request.session.items())  
    
                download_folder = process_download_folder_weibo(request.session['weibo_folder_name'])
                # print('download_folder：',download_folder )
                
                context = {
                    'keyword':  request.session['uname'], #request.session['keyword'],
                    'folder': download_folder  # not empty only if there are downloads
                }
            else:
                context = {
                    'keyword':  request.session['weibo_keyword'],
                }

    
        request.session['weibo_status'] = request.session['weibo_keyword'] =  request.session['weibo_folder_name'] = request.session['task_type']=''
        request.session.modified = True
        resultTemplate = 'main/weiboresult.html'
    return render(request, resultTemplate, context)


@csrf_exempt
def downloaded(request):
    # Currently this only handle tieba task, weibo task will be handled by make_weibo_task itself
    download_folder = ''
    print('downloaded:',request.session.items())
    
    # if request.session['task_type'] == 'tieba':
    while request.session['status'] is not 'finished':
        # print('this is a tieba task')
        time.sleep(10)
        request.session['status'] = get_crawl_status(
                request)
        request.session.modified = True
        print('crawl status update loop: ', request.session['status'])

    all_forums, download_folder = process_download_folder(
            request.session['folder_name'])  # no longer using all_forums, as data is obtained by ajax instead
    resultTemplate = 'main/result.html'
        
    context = {
        'keyword':  request.session['keyword'],
        'start_date': request.session['start_date'],
        'end_date': request.session['end_date'],
        'folder': download_folder  # not empty only if there are downloads
    }


    # elif request.session['task_type'] == 'weibo': 
    #     resultTemplate = 'main/weiboresult.html'
    #     while request.session['status'] is not 'finished':
    #         print('this is a weibo task')
    #         time.sleep(5)
    #         request.session['status'] = get_weibo_status()
    #         request.session.modified = True
    #         print('crawl status update loop: ', request.session['status'])
    #     download_folder = process_download_folder_weibo(request.session['folder_name'])
    #     print('download_folder',download_folder )
        
    #     context = {
    #         'keyword':  request.session['keyword'],
    #         'folder': download_folder  # not empty only if there are downloads
    #     }
    
    request.session['keyword'] = request.session['start_date'] = request.session['end_date'] = request.session['folder_name'] = request.session['task_type']=''
    request.session.modified = True
    return render(request, resultTemplate, context)

def format_date(year, month):
    return '-'.join([year, month.zfill(2)])


def process_scraped_content(folder_name):
    folder_full_path = (RESULTS_PATH / folder_name).resolve()
    file_to_process = 'replies.csv'
    file_to_process_full_path = (
        RESULTS_PATH / folder_name / file_to_process).resolve()

    analysis = get_keyword_summary(file_to_process_full_path)
    summary, keywords, sentiments, stats = format_analysis_for_csv(analysis)

    write_to_csv(folder_full_path, 'summary.csv', summary)
    write_to_csv(folder_full_path, 'keywords.csv', keywords)
    write_to_csv(folder_full_path, 'sentiments.csv', sentiments)
    write_to_csv(folder_full_path, 'stats.csv', stats)


def process_download_folder(folder_name):
    '''
    Checks if there are files in the folder.
    If there are files, (1) create zip + return download path to the zip,
    (2) process scraped content, and 
    (3) return list of popular tiebas.
    Else if there are no files at all, return None
    '''
    download_folder = ''
    all_forums = []
    download_path_obj = (RESULTS_PATH / folder_name)
    download_path_full = download_path_obj.resolve()

    try:
        files = os.listdir(download_path_full)

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
    except:
        print('Unable to continue processing downloading folder ',
              folder_name, ' as the folder has been deleted.')

    return all_forums, download_folder


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


def get_crawl_status(request):
    return scrapyd.job_status('default', request.session['task_id'])


def delete_folder(path,name):
    os.chdir(path)
    shutil.rmtree(name)


def cancel(request):
    print('cancel module:',request.session['task_type'] )
    if request.session['task_type'] == 'tieba':
        scrapyd.cancel('default', request.session['task_id'])
        delete_folder(RESULTS_PATH,request.session['folder_name'])

    # elif request.session['task_type'] == 'weibo':
    else: # weibo     
        cancel_weibo_crawl()
        # delete_folder(WEIBO_RESULTS_PATH,request.session['folder_name'])
        print('weibo task cancel')
    request.session['keyword'] = request.session['start_date'] = request.session[
        'end_date'] = request.session['folder_name'] = request.session['task_id'] = request.session['task_type'] = ''
    request.session.modified = True
    return render(request, 'main/cancel.html')


def get_keyword_summary(file_path):

    #variables for sentiment analysis
    positive = 0
    negative = 0
    neutral = 0
	
    #read content
    #df = pd.read_csv(file_path, encoding='utf-8', header=None) #issue with unicode character in filepath
    with open(file_path, 'r', encoding='utf-8') as f:
        df = pd.read_csv(f, encoding='utf-8', header=None)
	
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

    #keyword processing for whole tieba
    dictionary = {'keyword': keywords} #convert to dictionary for creating dataframe
    keyword_df = pd.DataFrame(dictionary) #create dataframe
    result = keyword_df.keyword.value_counts().nlargest(10, keep='first') #get the top 10 keywords of the whole tieba based on count
	
    #variables for summary processing
    finalized_summary = []
    replies_id = []
    post_id = []
	
    #summary processing for whole tieba
    s = SnowNLP(big_text)
    
    #limit the number of summary based on replies count (1 summary every 5 replies up to a maximum of 5 summaries)
    calc_total_summary = int(df_nonull.shape[0] / 5) + 1 #add 1 to compensate for rounding down
    if(calc_total_summary < 5):
        summary = s.summary(calc_total_summary)
    else:
        summary = s.summary(5) #get top 5 summary (reply), truncation might happen in the summary
		
    #locating post and replies id
    no_dup_summary = list(set(summary)) #remove duplicates from summary (happens on certain dataset)
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

# To be added weibo 9
class WeiboHistoryData(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, format=None):
        data = { 'users' : get_weibo_history() }
        return Response(data)

# To be added weibo 10
class WeiboTableData(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, format=None):
        folder_name = request.GET.get('folder', None)
        data = get_weibos_by_user(folder_name)
        return Response(data)

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
            # keywords = search_input.split()
            # remove duplicates
            keywords = list(dict.fromkeys(search_input.split()))
            keywords = keywords[:min(MAX, len(keywords))]
            keywords_with_frequency = get_frequency_from_string_input(
                file_path, keywords)

        return Response(keywords_with_frequency)


def folderExists(folder):
    history = get_history()
    if not history or folder not in history:
        return False
    return True


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

        # # Too many irrelevant tiebas, take top hits will do
        total = len(forums)
        max = 20
        top = max if total > max else total
        forums = sorted(forums, key=lambda x: int(
            x['count']), reverse=True)[:top]

        # convert to simple dict for easy ref by front-end
        top_forums = {pair['tieba']: pair['count'] for pair in forums}

    return summary, keywords, sentiments, stats, top_forums


def csvdownload(request):
    history = get_history()
    return render(request, 'main/csvdownload.html', context={'history': history})


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


class Jsontest(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, format=None):

        data = [
            {
                'name': 'hi',
                'id': 1,
                'blah': 'hohoho'
            },
            {
                'name': 'hello',
                'id': 2,
                'blah': 'hehehe'
            },
            {
                'name': 'yoohoo',
                'id': 3,
                'blah': 'kekeke'
            },
        ]

        return Response(data)