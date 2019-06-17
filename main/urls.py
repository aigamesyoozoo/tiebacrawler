from django.urls import path

from . import views

app_name = 'main'

urlpatterns = [
    path('', views.index, name='index'),
    path('home/', views.home, name='home'),
    path('home/<str:tieba>', views.rehome, name='rehome'),
    path('crawl/', views.crawl, name='crawl'),
    path('downloading/', views.downloading, name='downloading'),
    path('result/', views.result, name='result')
]