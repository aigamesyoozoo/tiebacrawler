from django.db import models


class TiebaTask(models.Model):
    task_id = models.CharField(max_length=100)
    keyword = models.CharField(max_length=200)
    start_date = models.CharField(max_length=50)
    end_date = models.CharField(max_length=50)
    status = models.CharField(max_length=20)
    folder_name = models.CharField(max_length=300)

    def set_all_attributes(self, task_id, keyword, start_date, end_date, status, folder_name):
        self.task_id = task_id
        self.keyword = keyword
        self.start_date = start_date
        self.end_date = end_date
        self.status = status
        self.folder_name = folder_name

    def __str__(self):
        return 'TiebaTask(task_id='+self.task_id+', keyword='+self.keyword+', start_date='+self.start_date+', end_date='+self.end_date+', status='+self.status+', folder_name='+self.folder_name+')'
