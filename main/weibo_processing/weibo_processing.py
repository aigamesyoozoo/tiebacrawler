from bs4 import BeautifulSoup
import glob
import json
import os
from GTDjango.settings import WEIBO_RESULTS_PATH, PROXIES_PATH
from urllib.parse import quote
import urllib.request
import time


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
    url = "https://s.weibo.com/user?q=" + keyword  # +"&Refer=SUer_box"
    url = quote(url, safe='/:?=')
    html = urllib.request.urlopen(url).read().decode('utf-8')
    time.sleep(1)
    soup = BeautifulSoup(html, features='lxml')
    users = soup.find_all('div', {"class": 'info'})
    names = {}
    for user in users:
        if user.select('.name .em') is not None:
            names.update({''.join(user.find('a', {"class": 'name'}).text).strip(
            ): user.find('a', {"class": 's-btn-c'})["uid"]})
    if names != {}:
        name_keys = list(names.keys())
        # if the exact username is not in the suggested list, crawl the first name in suggest list
        uname = keyword if keyword in names.keys() else name_keys[0]
        info_dict = {'uname': uname, 'uid': names[uname]}
    else:
        info_dict = None
    print(info_dict)
    return info_dict


def get_weibos_by_user(folder_name):
    '''
        Return list of formatted posts of this user.
    '''
    all_weibos = []

    if folder_name:
        curr_path = (WEIBO_RESULTS_PATH / folder_name).resolve()
        files = os.listdir(curr_path)
        os.chdir(curr_path)
        for jsonfile in files:
            if jsonfile[-5:] == '.json':
                with open(jsonfile, 'r', encoding='utf-8', errors='ignore') as load_f:
                    weibo = json.load(load_f)
                    all_weibos.append(weibo)
        all_weibos = [{'text': weibo.get("微博内容精简"), 'created_at': weibo.get("发布时间"), 'scheme': weibo.get("微博地址"), 'reposts_count': weibo.get(
            "转发数"), 'comments_count': weibo.get("评论数"), 'attitudes_count': weibo.get("点赞数")} for weibo in all_weibos]
    return all_weibos


def process_download_folder_weibo(folder_name):
    # check if there are downloads
    download_path_obj = (WEIBO_RESULTS_PATH / folder_name)
    download_path_full = download_path_obj.resolve()
    files = os.listdir(download_path_full)
    download_folder = ''

    if files:
        download_folder = folder_name
    else:
        os.rmdir(download_path_full)

    return download_folder


def create_directory_weibo(keyword):
    name = keyword
    os.chdir(WEIBO_RESULTS_PATH)
    if name in os.listdir(WEIBO_RESULTS_PATH):
        path = str((WEIBO_RESULTS_PATH/name).resolve()) + "/*"
        files = glob.glob(path)
        for f in files:
            os.remove(f)
    else:
        os.chdir(WEIBO_RESULTS_PATH)
        os.makedirs(name)
    return name
