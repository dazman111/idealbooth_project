from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .forms import ArticleForm, ArticleImageFormSet
from .models import Article, Comment
from .forms import CommentForm
from .forms import ArticleForm, ImageForm
from django.contrib.auth.decorators import user_passes_test
from django.contrib import messages
from .models import ArticleImage


def blog_home(request):
    articles = Article.objects.all()
    return render(request, 'blog/blog_home.html', {'articles': articles})

def article_detail(request, article_id):
    article = get_object_or_404(Article, id=article_id)
    comments = article.comments.all()
    
    if request.method == 'POST' and request.user.is_authenticated:
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.article = article
            comment.user = request.user
            comment.save()
            messages.success(request, "Votre commentaire a été ajouté avec succès.")
            return redirect('article_detail', article_id=article.id)
    else:
        form = CommentForm()

    return render(request, 'blog/article_detail.html', {'article': article, 'comments': comments, 'form': form})

@login_required
def edit_comment(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)

    if request.user != comment.user:
        return redirect('article_detail', article_id=comment.article.id)

    if request.method == 'POST':
        form = CommentForm(request.POST, instance=comment)
        if form.is_valid():
            form.save()
            return redirect('article_detail', article_id=comment.article.id)
    else:
        form = CommentForm(instance=comment)

    return render(request, 'blog/edit_comment.html', {'form': form})

def is_admin(user):
    return user.is_superuser

@user_passes_test(is_admin)
def manage_blog(request):
    articles = Article.objects.all()
    return render(request, 'blog/manage_blog.html', {'articles': articles})

@user_passes_test(is_admin)
def add_article(request):
    if request.method == 'POST':
        form = ArticleForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('manage_blog')
    else:
        form = ArticleForm()
    return render(request, 'blog/add_article.html', {'form': form})

@user_passes_test(is_admin)
def edit_article(request, article_id):
    article = get_object_or_404(Article, id=article_id)
    if request.method == 'POST':
        form = ArticleForm(request.POST, request.FILES, instance=article)
        formset = ArticleImageFormSet(request.POST, request.FILES, instance=article)
        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            return redirect('manage_blog')
    else:
        form = ArticleForm(instance=article)
        formset = ArticleImageFormSet(instance=article)
    return render(request, 'blog/edit_article.html', {'form': form, 'formset': formset,'article': article})

@user_passes_test(is_admin)
def delete_article(request, article_id):
    article = get_object_or_404(Article, id=article_id)
    article.delete()
    return redirect('manage_blog')

@csrf_exempt
@login_required
def ajax_post_comment(request):
    if request.method == 'POST':
        article_id = request.POST.get('article_id')
        text = request.POST.get('text')
        article = Article.objects.get(id=article_id)

        comment = Comment.objects.create(
            user=request.user,
            article=article,
            text=text
        )
        return JsonResponse({'status': 'success', 'message': 'Commentaire ajouté avec succès !'})
    return JsonResponse({'status': 'error', 'message': 'Méthode invalide.'})

@login_required
def like_article(request):
    if request.method == 'POST':
        article_id = request.POST.get('article_id')
        article = get_object_or_404(Article, id=article_id)
        liked = False

        if request.user in article.likes.all():
            article.likes.remove(request.user)
        else:
            article.likes.add(request.user)
            liked = True

        return JsonResponse({
            'liked': liked,
            'total_likes': article.likes.count()
        })
    
@login_required
def delete_comment(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id, user=request.user)
    comment.delete()
    return redirect('article_detail', pk=comment.article.pk)

def create_article(request):
    if request.method == 'POST':
        form = ArticleForm(request.POST)
        image_form = ImageForm(request.POST, request.FILES)
        files = request.FILES.getlist('image')

        if form.is_valid():
            article = form.save()
            for f in files:
                ArticleImage.objects.create(article=article, image=f)
            return redirect('article_detail', pk=article.pk)
    else:
        form = ArticleForm()
        image_form = ImageForm()

    return render(request, 'blog/create_article.html', {
        'form': form,
        'image_form': image_form
    })

def update_article(request, pk):
    article = get_object_or_404(Article, pk=pk)

    form = ArticleForm(request.POST or None, request.FILES or None, instance=article)
    formset = ArticleImageFormSet(request.POST or None, request.FILES or None, instance=article)

    if request.method == 'POST':
        if form.is_valid() and formset.is_valid():
            print("Image reçue :", request.FILES.get('image'))  # Debug si besoin
            form.save()
            formset.save()
            return redirect('manage_blog')  # ou autre redirection
        else:
            print("Formulaire non valide")
            print(form.errors)
            print(formset.errors)

    return render(request, 'blog/update_article.html', {
        'form': form,
        'formset': formset,
        'article': article
    })
