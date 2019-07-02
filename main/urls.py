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
    path('history/', views.history, name='history'),
    path('validate/', views.validate_Isexisted, name='validate'),
    path('downloaded/', views.downloaded, name='downloaded'),
    path('csvdownload/', views.csvdownload, name='csvdownload'),
    path('api/chart/analysis/', views.ChartData.as_view(), name='chart'),
    path('api/chart/keywordsearch/', views.KeywordSearchData.as_view(), name='keywordsearch'),
    path('api/history/tieba/', views.HistoryData.as_view(), name='historytieba'),
    # path('weibo/', views.weibo, name='weibo')
]
