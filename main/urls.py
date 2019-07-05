from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from . import views

app_name = 'main'

urlpatterns = [
    path('', views.index, name='index'),
    path('home/', views.home, name='home'),
    path('home/<str:tieba>', views.rehome, name='rehome'),
    path('crawl/', views.crawl, name='crawl'),
    path('cancel/', views.cancel, name='cancel'),
    path('history/tieba', views.history_tieba, name='history_tieba'),
    path('history/weibo', views.history_weibo, name='history_weibo'),
    path('validate/', views.validate_Isexisted, name='validate'),
    path('downloaded/', views.downloaded, name='downloaded'),
    path('csvdownload/', views.csvdownload, name='csvdownload'),
    path('api/chart/analysis/', views.ChartData.as_view()),
    path('api/chart/keywordsearch/', views.KeywordSearchData.as_view()),
    path('api/history/tieba/', views.TiebaHistoryData.as_view()),
    path('api/history/weibo/', views.WeiboHistoryData.as_view()),
    path('api/table/posts/', views.WeiboTableData.as_view()),
    path('weibo/', views.make_weibo_task, name='weibo'),
    #  path('weibo/history', views.weibo_history, name='weibo_history'),
]
