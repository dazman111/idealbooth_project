from django import forms
from .models import Comment
from .models import Article, ArticleImage
from django.forms.models import inlineformset_factory

class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['content','rating']
        widgets = {
            'rating': forms.NumberInput(attrs={'min': 1, 'max': 5, 'class': 'form-control'}),
            'content': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
        }

class ArticleForm(forms.ModelForm):
    class Meta:
        model = Article
        fields = ['title', 'content', 'author', 'image']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 5, 'class': 'form-control'}),
        }

class ImageForm(forms.ModelForm):
    class Meta:
        model = ArticleImage
        fields = ['image']
        widgets = {
            'image': forms.ClearableFileInput,
        }

class ArticleImageForm(forms.ModelForm):
    class Meta:
        model = ArticleImage
        fields = ['image']

ArticleImageFormSet = inlineformset_factory(
    Article, ArticleImage, form=ArticleImageForm,
    extra=3, can_delete=True
)
