from GTDjango.settings import CHROMEDRIVER_PATH, RESULTS_PATH
from main.general_processing.general_processing import *

import json
import os
import pandas as pd
from scrapyd_api import ScrapydAPI
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from snownlp import SnowNLP
import sys
import time
from uuid import uuid4


def create_directory(keyword, start_date, end_date):
    name = '_'.join([keyword, start_date, end_date])
    os.chdir(RESULTS_PATH)
    if name in os.listdir(RESULTS_PATH):
        shutil.rmtree(name)

    os.chdir(RESULTS_PATH)
    os.makedirs(name)
    return name


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


def folder_exists(folder):
    history = get_history()
    return history and folder in history


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
            # folders with zips indicate that the processing of scraped data has completed
            folders.append(folder)
    return folders


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
        MAX = 20  # Too many irrelevant tiebas, take top hits will do
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


def schedule(scrapyd, keyword, start_date, end_date, folder_name):
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


def get_crawl_status(scrapyd, task_id):
    ''' Get task status for tieba '''
    return scrapyd.job_status('default', task_id)


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

    # variables for summary processing
    finalized_summary = []
    replies_id = []
    post_id = []

    # summary processing for whole tieba
    s = SnowNLP(big_text)

    # limit the number of summary based on replies count (1 summary every 5 replies up to a maximum of 5 summaries)
    # add 1 to compensate for rounding down
    calc_total_summary = int(df_nonull.shape[0] / 5) + 1
    if calc_total_summary < 5:
        summary = s.summary(calc_total_summary)
    else:
        # get top 5 summary (reply), truncation might happen in the summary
        summary = s.summary(5)

    # locating post and replies id
    # remove duplicates from summary (happens on certain dataset)
    no_dup_summary = list(set(summary))
    for summ in no_dup_summary:

        # search dataframe for data containing the summary, substring of the actual list
        sum_df = df_nonull[df_nonull[2].str.contains(summ, na=False)]

        # loop through each of the dataframe, if the substring is short, might increase the number of summary found by a lot
        for i in range(sum_df.shape[0]):
            post_id.append(sum_df.iloc[i][0])  # post id
            replies_id.append(sum_df.iloc[i][1])  # replies id
            # summary, obtain it again since we have removed duplicates
            finalized_summary.append(sum_df.iloc[i][2])

    # return a dictionary, json.dumps if needed
    return {'post_id': post_id, 'replies_id': replies_id, 'replies_count': df_nonull.shape[0], 'summary': finalized_summary, 'keyword': dict(result), 'positive': positive, 'negative': negative, 'neutral': neutral}
