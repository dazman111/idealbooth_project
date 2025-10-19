from django.shortcuts import render, get_object_or_404, redirect
from django.utils.dateparse import parse_date
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Q
from django.core.paginator import Paginator
from django.contrib import messages
from datetime import date
from .models import Favorite

from .models import Photobooth
from .forms import PhotoboothForm
from reservations.models import Reservation
from reservations.forms import AddToCartForm  # ← Assure-toi que ce formulaire existe bien
from datetime import timedelta

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .serializers import PhotoboothSerializer


def photobooth_list(request):
    query = request.GET.get("q", "")
    max_price = request.GET.get("max_price")
    available_only = request.GET.get("available")

    photobooths = Photobooth.objects.all()
    session_stock = request.session.get('session_stock', {})

    # Appliquer les stocks temporaires
    for booth in photobooths:
        booth_id_str = str(booth.id)
        if booth_id_str in session_stock:
            booth.stock = session_stock[booth_id_str]['stock']
            booth.available = session_stock[booth_id_str]['available']

    # Filtres
    if query:
        photobooths = photobooths.filter(Q(name__icontains=query) | Q(description__icontains=query))
    if max_price:
        photobooths = photobooths.filter(price__lte=max_price)
    if available_only:
        photobooths = [b for b in photobooths if b.available > 0]

    paginator = Paginator(photobooths, 6)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "photobooths": page_obj,
        "page_obj": page_obj,
        "is_paginated": page_obj.has_other_pages(),
    }
    return render(request, "photobooths/photobooth_list.html", context)


def photobooth_detail(request, pk):
    photobooth = get_object_or_404(Photobooth, pk=pk)
    form = AddToCartForm()

     # Vérifier si ce photobooth est déjà en favoris
    is_favorite = False
    if request.user.is_authenticated:
        is_favorite = Favorite.objects.filter(user=request.user, photobooth=photobooth).exists()


    reservations = Reservation.objects.filter(photobooth=photobooth)
    disabled_dates = []
    for reservation in reservations:
        current_date = reservation.start_date
        while current_date <= reservation.end_date:
            disabled_dates.append(current_date.strftime('%Y-%m-%d'))
            current_date += timedelta(days=1)

    return render(request, 'photobooths/photobooth_detail.html', {
        'photobooth': photobooth,
        'form': form,
        'disabled_dates': disabled_dates,
        'today': date.today(),  # ← ajoute ça ici
        'is_favorite': is_favorite, 
    })


@login_required
def photobooth_create(request):
    if request.method == 'POST':
        form = PhotoboothForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('photobooth_list')
    else:
        form = PhotoboothForm()
    return render(request, 'photobooths/photobooth_form.html', {'form': form})


@login_required
def photobooth_update(request, pk):
    photobooth = get_object_or_404(Photobooth, pk=pk)
    if request.method == 'POST':
        form = PhotoboothForm(request.POST, request.FILES, instance=photobooth)
        if form.is_valid():
            form.save()
            return redirect('photobooth_list')
    else:
        form = PhotoboothForm(instance=photobooth)
    return render(request, 'photobooths/photobooth_form.html', {'form': form})


@login_required
def photobooth_delete(request, pk):
    photobooth = get_object_or_404(Photobooth, pk=pk)
    if request.method == 'POST':
        photobooth.delete()
        return redirect('photobooth_list')
    return render(request, 'photobooths/photobooth_confirm_delete.html', {'photobooth': photobooth})


@login_required
def dashboard(request):
    query = request.GET.get('q')
    available_only = request.GET.get('available') == '1'

    photobooths = Photobooth.objects.all()

    if query:
        photobooths = photobooths.filter(name__icontains=query)

    if available_only:
        photobooths = photobooths.filter(available=True)

    count = photobooths.count()

    return render(request, 'photobooths/dashboard.html', {
        'photobooths': photobooths,
        'query': query,
        'available_only': available_only,
        'count': count,
    })


def is_admin(user):
    return user.is_staff


@login_required
@user_passes_test(is_admin)
def add_photobooth(request):
    if request.method == 'POST':
        form = PhotoboothForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('photobooth_list')
    else:
        form = PhotoboothForm()
    return render(request, 'photobooths/add_photobooth.html', {'form': form})

def add_to_cart(request, photobooth_id):
    if request.method == 'POST':
        date_str = request.POST.get('date')
        photobooth = get_object_or_404(Photobooth, pk=photobooth_id)

        selected_date = parse_date(date_str)
        if not selected_date:
            messages.error(request, "Date invalide.")
            return redirect('photobooth_list')

        cart = request.session.get('cart', [])

        # Optionnel : vérifier si cet item existe déjà
        for item in cart:
            if item['photobooth_id'] == photobooth.id and item['date'] == date_str:
                messages.warning(request, "Ce photobooth est déjà dans votre panier pour cette date.")
                return redirect('photobooth_list')

        cart.append({
            "photobooth_id": photobooth.id,
            "name": photobooth.name,
            "price": float(photobooth.price),
            "date": date_str,
            "image_url": photobooth.image.url if photobooth.image else '/static/img/default.jpg'
        })
        request.session['cart'] = cart
        messages.success(request, f"{photobooth.name} ajouté au panier pour le {date_str}.")
        return redirect('photobooth_list')
    
class PhotoboothViewSet(viewsets.ModelViewSet):
    queryset = Photobooth.objects.all()
    serializer_class = PhotoboothSerializer
    permission_classes = [IsAuthenticated]

@login_required
def notify_me(request, photobooth_id):
    photobooth = get_object_or_404(Photobooth, id=photobooth_id)
    # Ici tu peux ajouter l'utilisateur à une liste d'attente ou envoyer un email
    messages.success(request, "Vous serez notifié lorsque le photobooth sera disponible.")
    return redirect('photobooth_list')

@staff_member_required
def restock_photobooth(request, booth_id):
    session_stock = request.session.get('session_stock', {})
    booth = get_object_or_404(Photobooth, id=booth_id)
    booth_id_str = str(booth.id)

    if booth_id_str in session_stock:
        session_stock[booth_id_str]['stock'] += 1
        session_stock[booth_id_str]['available'] += 1
    else:
        session_stock[booth_id_str] = {
            'stock': booth.stock + 1,
            'available': booth.available + 1
        }

    request.session['session_stock'] = session_stock
    messages.success(request, f"Le stock du photobooth '{booth.name}' a été modifié (temporairement).")
    return redirect('manage_photobooths')  # ou photobooth_list selon ton routing

@staff_member_required
def reset_stock_session(request):
    if 'session_stock' in request.session:
        del request.session['session_stock']
        messages.success(request, "Le stock temporaire a été réinitialisé.")
    return redirect('photobooth_list')

@staff_member_required
def reduce_stock_photobooth(request, booth_id):
    booth = get_object_or_404(Photobooth, id=booth_id)

    # Gestion du stock via session
    session_stock = request.session.get('session_stock', {})

    booth_key = str(booth.id)
    current_stock = session_stock.get(booth_key, booth.available)

    if current_stock > 0:
        session_stock[booth_key] = current_stock - 1
        messages.success(request, f"Stock de '{booth.name}' réduit à {session_stock[booth_key]}.")
    else:
        messages.warning(request, f"Stock de '{booth.name}' déjà à 0.")

    request.session['session_stock'] = session_stock

    return redirect('manage_photobooths')  # ou 'photobooth_list' selon ta vue

@login_required
def add_favorite(request, pk):
    photobooth = get_object_or_404(Photobooth, pk=pk)
    Favorite.objects.get_or_create(user=request.user, photobooth=photobooth)
    return redirect(request.META.get('HTTP_REFERER', 'photobooth_list'))

@login_required
def remove_favorite(request, pk):
    photobooth = get_object_or_404(Photobooth, pk=pk)
    Favorite.objects.filter(user=request.user, photobooth=photobooth).delete()
    return redirect(request.META.get('HTTP_REFERER', 'photobooth_list'))



