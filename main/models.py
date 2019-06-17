from django.db import models
import json

class Comment(models.Model):
    comment_description = models.CharField(max_length=600)
    comment_user = models.CharField(max_length=100)

    @property
    def to_dict(self):
        data = {
            'comment_description': json.loads(self.comment_description),
            'comment_user': json.loads(self.comment_user)
        }
        return data

    def __str__(self):
        return self.comment_description

class Reply(models.Model):
    reply_description = models.CharField(max_length=600)
    reply_user = models.CharField(max_length=100)

    def __str__(self):
        return self.reply_description