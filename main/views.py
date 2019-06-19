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


scrapyd = ScrapydAPI('http://localhost:6800')


def index(request):
    return render(request, 'main/index.html')


def downloading(request):
    return render(request, 'main/downloading.html')


def popular_tiebas_among_users_who_posted():
    all_forums = read_csv_as_dict_list(TIEBACOUNT_PATH)
    if all_forums:
        all_forums.sort(key=lambda x: int(x['count']), reverse=True)
    for f in all_forums:
        # replace / with a safe character
        f['cleaned_name'] = f['tieba'].replace('/', '^')
        # count_per_em = int(int(all_forums[0]['count']) / 4)
        # count_per_em = 1 if count_per_em is 0 else count_per_em
    # for f in all_forums:
    #     f['count'] = int(int(f['count']) / count_per_em)
    #     if f['count'] is 0:
    #         f['count'] = 1
    return all_forums


# direct view of results.html for debugging purposes
def result(request):
    all_forums = popular_tiebas_among_users_who_posted()
    context = {
        'forums': all_forums,
        'path': RESULTS_PATH
    }
    return render(request, 'main/result.html', context)


def read_csv_as_dict_list(file_to_read):
    dict_list = []
    with open(file_to_read, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, ['tieba', 'count'])
        for line in reader:
            dict_list.append(line)
    return dict_list


def rehome(request, tieba):
    return render(request, 'main/home.html', {'forums': [tieba.replace('^', '/')]})


def home(request):
    forums = []
    keyword = request.GET.get('kw')
    print('keword is: ', keyword)
    if keyword:
        forums = get_related_forums_by_selenium(keyword)
    context = {'forums': forums}
    return render(request, 'main/home.html', context)


def get_related_forums_by_selenium(keyword):
    options = Options()
    options.headless = True
    browser = webdriver.Chrome(CHROMEDRIVER_PATH, chrome_options=options)
    browser.get('http://c.tieba.baidu.com/')

    search_textbox = browser.find_element_by_id("wd1")
    browser.implicitly_wait(4)  # time intervals given for scrapy to crawl
    search_textbox.send_keys(keyword)
    relevant_forums_webelements = browser.find_elements_by_css_selector(
        ".forum_name , .highlight")
    relevant_forums_title = [forum.text for index, forum in enumerate(
        relevant_forums_webelements) if index % 2 == 0 or index > 7]
    browser.quit()

    return relevant_forums_title


@csrf_exempt
@require_http_methods(['POST', 'GET'])  # only get and post
def crawl(request):
    if request.method == 'POST':
        # remove the 'ba' character as it leads to a different link
        keyword = request.POST.get('keyword', None)[:-1]
        start_date = request.POST.get('start_date', None)
        end_date = request.POST.get('end_date', None)
        if keyword and start_date and end_date:
            task_id, unique_id, status = schedule(
                keyword, start_date, end_date)
            print(task_id, unique_id, status)

        while status is not 'finished':
            time.sleep(10)
            status = get_crawl_status(task_id)
            print('crawl status update loop: ', status)
        all_forums = popular_tiebas_among_users_who_posted()
        context = {
            'keyword': keyword,
            'start_date': start_date,
            'end_date': end_date,
            'status': status,
            'forums': all_forums,
            'path': RESULTS_PATH
        }
        return render(request, 'main/result.html', context)


def schedule(keyword, start_date, end_date):
    unique_id = str(uuid4())  # create a unique ID.
    settings = {
        'unique_id': unique_id,  # unique ID for each record for DB
    }
    task = scrapyd.schedule('default', 'tiebacrawler', settings=settings, keyword=keyword, start_date=start_date,
                            end_date=end_date)
    return task, unique_id, 'started'


def get_crawl_status(task_id):
    return scrapyd.job_status('default', task_id)
