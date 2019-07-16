from django.db import models

class WeiboTask(models.Model):
    uid = models.CharField(max_length=100)
    uname = models.CharField(max_length=200)
    status = models.CharField(max_length=20)
    folder_name = models.CharField(max_length=200)