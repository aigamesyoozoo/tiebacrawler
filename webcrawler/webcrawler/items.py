# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# https://doc.scrapy.org/en/latest/topics/items.html

from scrapy.item import Item, Field



class TiebaItem(Item):
    # define the fields for your item here like:
    # name = scrapy.Field()
    
    # name of tieba
    tieba_name = Field()
    # list of posts url in this tieba
    Url = Field()
    # 
    num_following_user = Field()

class PostItem(Item):
    # user who post 
    author_home_url = Field()
    # title of post
    title = Field()
    # 
    post_id = Field()
    reply_num = Field()

class ReplyItem(Item):
    post_id = Field()
    reply_id = Field()
    author_home_url = Field()
    content = Field()
    comment_num = Field()

class CommentItem(Item):
    post_id = Field()
    reply_id = Field()
    author_home_url = Field()
    comment_id = Field()
    content = Field()


