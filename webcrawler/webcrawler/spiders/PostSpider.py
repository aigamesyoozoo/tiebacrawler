import scrapy
from scrapy.http import Request
from scrapy import Request, Selector
from webcrawler.items import TiebaItem, PostItem, ReplyItem, CommentItem
import datetime
from dateutil.relativedelta import *
import time
from webcrawler.settings import START_DATE, END_DATE, NUM_TIEZI
import json
import logging


class PostSpider(scrapy.Spider):
    name = 'tiebacrawler'
    request_baidu_domain = 'http://tieba.baidu.com'
    # tid will be post_id,pid will be reply_id
    request_comment_url_base = 'http://tieba.baidu.com/p/comment?tid=%s&pid=%s&pn=%s'
    request_post_url_base = 'http://tieba.baidu.com/p/%s'
    request_tieba_url_base = 'http://tieba.baidu.com/f?kw=%s&ie=utf-8'
    # request_tieba_url = request_tieba_url_base % ('%E5%8F%8B%E8%B0%8A%E5%B7%B2%E8%B5%B0%E5%88%B0%E5%B0%BD%E5%A4%B4')
    tiezi_count = 0
    folder_name =''

    def __init__(self, *args, **kwargs):
        # We are going to pass these args from our django view.
        # To make everything dynamic, we need to override them inside __init__ method

        # singular - from argument
        self.keyword = kwargs.get('keyword')
        self.start_date = datetime.datetime.strptime(
            kwargs.get('start_date'), '%Y-%m').date()
        self.end_date = datetime.datetime.strptime(
            kwargs.get('end_date'), '%Y-%m').date()
        self.folder_name = kwargs.get('folder_name')
        
        # self.folder_name = 'xba_2019-02_2019-03'
        print('--------------------------------------------------------------')
        print('INIT VALUES>> self.startdate',
              self.start_date, 'self.enddate', self.end_date)
        print('INIT TYPE>> self.startdate type:', type(self.start_date), 'self.enddate type:',
              type(self.end_date))

        # self.keyword = '%E4%BA%8C%E6%AC%A1%E5%85%83'#二次元
        # self.start_date = START_DATE
        # self.end_date = END_DATE

        # self.domain = kwargs.get('domain')
        # in list form
        self.start_urls = [self.request_tieba_url_base % (self.keyword)]
        # self.allowed_domains = [self.domain]

        # CommentSpider.rules = [
        #     scrapy.spiders.Rule(LinkExtractor(unique=True), callback='parse_item'),
        # ]
        super(PostSpider, self).__init__(*args, **kwargs)

    def parse(self, response):
        posts_sel = Selector(response).css('.j_thread_list')
        for sel in posts_sel:
            create_time = sel.css(
                '.threadlist_author span.is_show_create_time::text').extract_first()
            last_reply_time = sel.css(
                '.threadlist_author span.threadlist_reply_date::text').extract_first()
            create_time = str(create_time).strip()
            last_reply_time = str(last_reply_time).strip()

            # print(
            #     '-----------------------post-date&&last-reply-date-----------------------------')
            # print(create_time)
            # print(last_reply_time)

            if self.compare_post_date(create_time) or self.compare_post_date(last_reply_time):
                # 直接取百度的id <a href="/p/6144256076?pid=125817093956&amp;see_lz=1#125817093956"></a>
                post_id = sel.css('::attr(data-tid)').extract_first()
                #posturl = "http://tieba.baidu.com/p/" + sel.css('.j_th_tit a::attr(href)').extract_first()
                #posturl = 'http://tieba.baidu.com/p/%s' % (post_id)
                author_home_url = self.request_baidu_domain + \
                    str(sel.css('.tb_icon_author a::attr(href)').extract_first())
                item = PostItem()
                item['title'] = str(
                    sel.css('.j_th_tit a::text').extract_first()).strip()
                item['post_id'] = post_id
                item['reply_num'] = str(
                    sel.css('.threadlist_rep_num::text').extract_first()).strip()
                yield item
                yield Request(self.request_post_url_base % (post_id), callback=self.parse_reply, meta={'post_id': post_id})
                yield Request(author_home_url, callback=self.parse_user_related_tieba)

        if self.tiezi_count < NUM_TIEZI/50:
            print('------------------tiezicount-----------------------')
            self.tiezi_count += 1
            print(self.tiezi_count)
            yield Request(self.start_urls[0] + '&pn=' + str(self.tiezi_count*50), callback=self.parse)

    def parse_reply(self, response):
        replies_sel = Selector(response).css('.j_l_post')
        for sel in replies_sel:
            # print('------------------.tail-info::text-----post_date----------------------------')
            # print(sel.css('.tail-info::text').extract())
            # print('------------------.p_tail::text-----post_date----------------------------')
            # print(sel.css('.p_tail::text').extract())

            # <span class="j_jb_ele"><a class="tail-info" data-checkun="un"><img class="icon-jubao" src=></a></span><span class="tail-info">2楼</span><span class="tail-info">2019-05-18 18:14</span>
            if len(sel.css('.tail-info::text').extract()) > 0:
                post_date = str(
                    sel.css('.tail-info::text').extract()[-1]).strip()
                # print('------------------.tail-info::text----------------------------')
                # print(post_date)
            # <ul class="p_tail"><li><span>9楼</span></li><li><span>2018-01-13 22:41</span></li></ul>
            elif len(sel.css('.p_tail::text').extract()) > 0:
                post_date = str(sel.css('.p_tail::text').extract()[-1]).strip()
                # print('-----------------.p_tail::text----------------------------')
                # print(post_date)
            else:
                # print('-----------------.none----------------------------')
                post_date = ''
                # print(post_date)

            if self.compare_post_date(post_date[:7]):
                #comment_json_str = sel.css('.j_lzl_r::attr(data-field)').extract_first()
                comment_json_str = sel.css(
                    '::attr(data-field)').extract_first()
                comment_json = json.loads(str(comment_json_str))
                comment = comment_json['content']
                reply_id = comment['post_id']

                item = ReplyItem()
                meta = response.meta
                item['post_id'] = meta['post_id']
                item['reply_id'] = reply_id
                item['comment_num'] = comment['comment_num']
                # if sel.css('.j_d_post_content::text').extract_first().strip() != '':
                # if is '',then leave it as ''
                item['content'] = str(
                    sel.css('.j_d_post_content::text').extract_first()).strip()
                if ''.join(sel.css('.post_bubble_middle_inner::text').extract()) != '':  # 有样式框的文本
                    item['content'] = ''.join(
                        sel.css('.post_bubble_middle_inner::text').extract())

                author_home_url = self.request_baidu_domain + \
                    str(sel.css('.p_author_name::attr(href)').extract_first())
                yield item
                yield Request(self.request_comment_url_base % (meta['post_id'], reply_id, 1),
                              callback=self.parse_comment, meta={'post_id': meta['post_id'], 'reply_id': reply_id, 'cur_page': 1})
                yield Request(author_home_url, callback=self.parse_user_related_tieba)
        if Selector(response).css('.pb_list_pager a::text').extract_first() == '下一页':
            yield Request(self.request_baidu_domain + Selector(response).css('.pb_list_pager a::herf'), callback=self.parse_reply)

    def parse_comment(self, response):
        comments_sel = Selector(response).css('.lzl_single_post')
        # print('-------------------comments_sel------------------------')
        # print(comments_sel)
        for sel in comments_sel:
            item = CommentItem()
            meta = response.meta
            author_home_url = self.request_baidu_domain + \
                str(sel.css('.lzl_p_p::attr(href)').extract_first()).strip()

            item['post_id'] = response.meta['post_id']
            item['reply_id'] = response.meta['reply_id']
            item['content'] = ''.join(
                sel.css('.lzl_content_main::text').extract()).strip()
            yield item
            yield Request(author_home_url, callback=self.parse_user_related_tieba)

        logging.debug('before parsing next page if existed..')
        next_page = self.get_next_page(response)

        # meta.reply_id meta.post_id
        if int(next_page) > int(response.meta['cur_page']):
            yield Request(self.request_comment_url_base % (response.meta['post_id'], response.meta['reply_id'], next_page),
                          callback=self.parse_comment, meta={'post_id': response.meta['post_id'], 'reply_id': response.meta['reply_id'], 'cur_page': next_page})  # tid is 主贴的id, pid是回复的id

    def parse_user_related_tieba(self, response):
        following_tieba_sel = Selector(response).css(
            '.u-f-item::text').extract()
        posting_tieba_sel = Selector(response).css('.n_name::attr(title)').extract()
        posting_tieba_sel = [sel +'吧' for sel in posting_tieba_sel]
        tiebas = following_tieba_sel + posting_tieba_sel

        # print('-----------------------Spider-tieba-------------------------------')
        # print(tiebas)
        item = TiebaItem()
        item['tieba_name'] = set(tiebas)
        return item



    def compare_post_date(self, post_date):
        if post_date in ['None', None, '', []]:
            return False

        #postdate = str(post_date)
        postdate = post_date
        splitdate = postdate.split('-')
        if len(splitdate) < 2:
            # print('today')
            date = time.strftime("%Y-%m", time.localtime())
            date = datetime.datetime.strptime(date, '%Y-%m').date()

        elif int(splitdate[0].strip()) > 12:
            #print('with year')
            date = datetime.datetime.strptime(postdate, '%Y-%m').date()

        elif int(splitdate[0].strip()) <= 12:
            #print('without year')
            postdate = '2019' + '-' + splitdate[0].strip()
            date = datetime.datetime.strptime(postdate, '%Y-%m').date()
        # print(date)
        d1 = datetime.datetime.strptime(self.start_date, '%Y-%m').date()
        d2 = datetime.datetime.strptime(
            self.end_date, '%Y-%m').date()+relativedelta(months=+1)
        # if date >= self.start_date and date <= self.end_date:
        if d1 <= date < d2:
            return True
        else:
            return False

    def get_next_page(self, response):
        anchor_sels = Selector(response).css('.j_pager a')
        #anchor_sels = Selector(response).css('.lzl_li_pager p a')
        # print('--------------------------anchor_sels---------------------------------')
        # print(len(anchor_sels))
        next_page = 1
        for sel in anchor_sels:
            #logging.debug('pager anchor text: ' % (sel.css('::text').extract_first()))
            if sel.css('::text').extract_first() == '下一页':
                next_page = sel.css('::attr(href)').extract_first()[1:]
                #next_page = sel.css('::attr(index)').extract_first()
                logging.debug('next page num: %s' % (next_page))
        return int(next_page)
