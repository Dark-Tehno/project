from django.db import models


class Tags(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name


class DarkNews(models.Model):
    title = models.CharField(max_length=255)
    content = models.TextField(verbose_name="Контент(формат MD)")
    created_at = models.DateTimeField(auto_now_add=True)
    likes = models.IntegerField(default=0)
    dislikes = models.IntegerField(default=0)
    tags = models.ManyToManyField(Tags, related_name='news')

    def __str__(self):
        return self.title

