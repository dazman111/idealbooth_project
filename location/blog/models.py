from django.db import models
from django.conf import settings
from django_ckeditor_5.fields import CKEditor5Field


class Article(models.Model):
    title = models.CharField(max_length=255)
    content = CKEditor5Field('Contenu', config_name='default')
    author = models.CharField(max_length=100, blank=True, null=True)
    image = models.ImageField(upload_to='blog_images/', blank=True, null=True)
    published_date = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    likes = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='liked_articles', blank=True)

    def __str__(self):
        return self.title
    
    def total_likes(self):
        return self.likes.count()
    

class Comment(models.Model):
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name="comments")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    rating = models.PositiveIntegerField(default=5)

    def __str__(self):
        return f"Comment by {self.user.username} on {self.article.title}"
    

class ArticleLikes(models.Model):
    article = models.ForeignKey(Article, on_delete=models.CASCADE)
    customuser = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    
class ArticleImage(models.Model):
    article = models.ForeignKey(Article, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='articles/multiple/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

