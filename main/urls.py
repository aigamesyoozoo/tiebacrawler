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
    path('downloading/', views.downloading, name='downloading'),
    path('result/', views.result, name='result'),
    path('history/', views.history, name='history'),
    path('cancel/', views.cancel, name='cancel'),
    path('backup/', views.backup, name='backup'),
    path('api/chart/analysis', views.ChartData.as_view()),
    path('validate/', views.validate_Isexisted, name='validate'),
    path('downloaded/', views.downloaded, name='downloaded'),
    # path('weibo/', views.weibo, name='weibo')
]
