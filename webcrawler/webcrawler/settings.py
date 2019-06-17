# -*- coding: utf-8 -*-

import os
import sys
import datetime
import django

# DJANGO INTEGRATION

sys.path.append(os.path.dirname(os.path.abspath('.')))
os.environ['DJANGO_SETTINGS_MODULE'] = 'GTDjango.settings'

# This is required only if Django Version > 1.8
django.setup()

# DJANGO INTEGRATION

# Scrapy settings for webcrawler project
#
# For simplicity, this file contains only settings considered important or
# commonly used. You can find more settings consulting the documentation:
#
#     https://doc.scrapy.org/en/latest/topics/settings.html
#     https://doc.scrapy.org/en/latest/topics/downloader-middleware.html
#     https://doc.scrapy.org/en/latest/topics/spider-middleware.html

BOT_NAME = 'webcrawler'

SPIDER_MODULES = ['webcrawler.spiders']
NEWSPIDER_MODULE = 'webcrawler.spiders'


# Crawl responsibly by identifying yourself (and your website) on the user-agent
#USER_AGENT = 'webcrawler (+http://www.yourdomain.com)'
USER_AGENT = 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)'

# DOWNLOADER_MIDDLEWARES = {
#     # rotate user agent
#     'scrapy.downloadermiddlewares.useragent.UserAgentMiddleware': None,
#     'scrapy_user_agents.middlewares.RandomUserAgentMiddleware': 400,
#     #rotate ip
#     'scrapy_proxy_pool.middlewares.ProxyPoolMiddleware': 610,
#     'scrapy_proxy_pool.middlewares.BanDetectionMiddleware': 620
# }

# Obey robots.txt rules
ROBOTSTXT_OBEY = False

# PROXY_POOL_ENABLED = True

# Configure maximum concurrent requests performed by Scrapy (default: 16)
#CONCURRENT_REQUESTS = 32

# Configure a delay for requests for the same website (default: 0)
# See https://doc.scrapy.org/en/latest/topics/settings.html#download-delay
# See also autothrottle settings and docs
# DOWNLOAD_DELAY = 3
# The download delay setting will honor only one of:
#CONCURRENT_REQUESTS_PER_DOMAIN = 16
#CONCURRENT_REQUESTS_PER_IP = 16

# Disable cookies (enabled by default)
COOKIES_ENABLED = False
COOKIES_DEBUG = True

# Disable Telnet Console (enabled by default)
#TELNETCONSOLE_ENABLED = False

# Override the default request headers:
# DEFAULT_REQUEST_HEADERS = {
#   'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
#   'Accept-Language': 'en',
# }

# Enable or disable spider middlewares
# See https://doc.scrapy.org/en/latest/topics/spider-middleware.html
# SPIDER_MIDDLEWARES = {
#    'webcrawler.middlewares.WebcrawlerSpiderMiddleware': 543,
# }

# Enable or disable downloader middlewares
# See https://doc.scrapy.org/en/latest/topics/downloader-middleware.html
# DOWNLOADER_MIDDLEWARES = {
#    'webcrawler.middlewares.WebcrawlerDownloaderMiddleware': 543,
# }

# Enable or disable extensions
# See https://doc.scrapy.org/en/latest/topics/extensions.html
# EXTENSIONS = {
#    'scrapy.extensions.telnet.TelnetConsole': None,
# }

# Configure item pipelines
# See https://doc.scrapy.org/en/latest/topics/item-pipeline.html
ITEM_PIPELINES = {
    'webcrawler.pipelines.WebcrawlerPipeline': 300,
}

# Enable and configure the AutoThrottle extension (disabled by default)
# See https://doc.scrapy.org/en/latest/topics/autothrottle.html
# AUTOTHROTTLE_ENABLED = True
# The initial download delay
# AUTOTHROTTLE_START_DELAY = 3
# The maximum download delay to be set in case of high latencies
# AUTOTHROTTLE_MAX_DELAY = 5
# The average number of requests Scrapy should be sending in parallel to
# each remote server
# AUTOTHROTTLE_TARGET_CONCURRENCY = 0.5
# Enable showing throttling stats for every response received:
# AUTOTHROTTLE_DEBUG = True

# Enable and configure HTTP caching (disabled by default)
# See https://doc.scrapy.org/en/latest/topics/downloader-middleware.html#httpcache-middleware-settings
# HTTPCACHE_ENABLED = True
# HTTPCACHE_EXPIRATION_SECS = 0
# HTTPCACHE_DIR = 'httpcache'
# HTTPCACHE_IGNORE_HTTP_CODES = []
# HTTPCACHE_STORAGE = 'scrapy.extensions.httpcache.FilesystemCacheStorage'


FEED_EXPORT_ENCODING = 'utf-8'

START_DATE = datetime.datetime.strptime("2019-06", '%Y-%m').date()
END_DATE = datetime.datetime.strptime("2019-07", '%Y-%m').date()
NUM_TIEZI = 50
script_dir = os.path.dirname(__file__)  # <-- absolute dir the script is in
rel_path = '../../results'
FILE_PATH = os.path.join(script_dir, rel_path)


# BAIDUID=794E986AA686897D83A246CFDC7EDDCB:FG=1;
# pgv_pvi=5716038656;
# BIDUPSID=794E986AA686897D83A246CFDC7EDDCB;
# PSTM=1552895031;
# TIEBA_USERTYPE=e56b4cc7fde5cc70f1eb2833;
# bdshare_firstime=1555395819541;
# BAIDU_WISE_UID=wapp_1556764853453_759;
# ZD_ENTRY=google;
# cflag=13%3A3;
# pgv_si=s2056644608;
# TIEBAUID=902f5df64a57aa5f243f420e;
# wise_device=0;
# 1380099753_FRSVideoUploadTip=1;
# BDUSS=EFFb25hcEE4ZmNqc1B-WEx2bUZBYm9Zek9lVlEyUXVRQVVHV2JPUHF1fmVGQnhkSVFBQUFBJCQAAAAAAAAAAAEAAACppkJS9-m5xQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAN6H9Fzeh~RcU;
# STOKEN=b195c50cd9315ed43fe1d69308e267e7aa14bae5640a019dc9af241cf8126349;
# Hm_lvt_98b9d8c2fd6608d564bf2ac2ae642948=1559199658,1559202172,1559294726,1559529573;
# Hm_lpvt_98b9d8c2fd6608d564bf2ac2ae642948=1559530718
