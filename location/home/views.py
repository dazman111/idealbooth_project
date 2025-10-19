from django.shortcuts import render

def home(request):
    return render(request, 'home.html')

def politique_confidentialite(request):
    return render(request, 'politique_confidentialite.html')

def mentions_legales(request):
    return render(request, 'mentions_legales.html')

