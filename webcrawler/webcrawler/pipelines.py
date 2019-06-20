# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://doc.scrapy.org/en/latest/topics/item-pipeline.html
from webcrawler.items import TiebaItem,PostItem,ReplyItem,CommentItem
# from webcrawler.settings import FILE_PATH
from webcrawler.spiders import PostSpider
import csv
import os

class WebcrawlerPipeline(object):
    
    ####################need to be pushed###################
    script_dir = os.path.dirname(__file__)  # <-- absolute dir the script is in
    FOLDER_NAME = os.path.join(script_dir, '../../results/')

    def open_spider(self,spider): 
        self.FOLDER_NAME = self.FOLDER_NAME + str(spider.folder_name)
    ####################need to be pushed###################

    def process_item(self, item, spider):
        if isinstance(item, PostItem):
            with open(self.FOLDER_NAME+'/posts.csv', 'a+', encoding='utf-8', newline='') as f:
                csv.writer(f, dialect="excel").writerow((item['post_id'],item['title'],item['reply_num']))

        elif isinstance(item, ReplyItem):         
            with open(self.FOLDER_NAME+'/replies.csv', 'a+', encoding='utf-8', newline='') as f:
                csv.writer(f, dialect="excel").writerow((item['post_id'],item['reply_id'],item['content'],item['comment_num']))

        elif isinstance(item, CommentItem):
            with open(self.FOLDER_NAME+'/comments.csv', 'a+', encoding='utf-8', newline='') as f:
                csv.writer(f, dialect="excel").writerow((item['post_id'],item['reply_id'],item['content']))

        elif isinstance(item, TiebaItem):
            with open(self.FOLDER_NAME + '/tieba_count.csv', 'a+', encoding='utf-8', newline='') as f:
                f.seek(0)
                reader = csv.reader(f)
                tiebas = dict(row[:2] for row in list(reader))

                tiebas_name = item['tieba_name']
                # print('------------------------tieba-tobe-added-------------------------------')
                # print(tiebas_name)
                for tieba_name in tiebas_name:
                    # print('-----------------------Pipeline-tieba-------------------------------')                   
                    tieba = str(tieba_name).strip()
                    # print('-----------------------before-dict-tieba-------------------------------')
                    # print(tiebas)
                    # print(tieba)
                    if tieba is '':
                        continue

                    if tieba not in list(tiebas.keys()):
                        # print('does not exist')
                        tiebas.update({tieba : 1 })
                    else:
                        tiebas[tieba] = int(tiebas[tieba_name]) + 1
                        # print('already exists!')
                        
                    # print('-----------------------after-dict-tieba-------------------------------')
                    # print(tiebas)

            with open(self.FOLDER_NAME + '/tieba_count.csv', 'w+', encoding='utf-8', newline='') as f:   
                f.seek(0)
                writer = csv.writer(f)
                writer.writerows(tiebas.items())
            
        return item
