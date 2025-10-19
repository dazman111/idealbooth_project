from rest_framework import viewsets, permissions
from photobooths.models import Photobooth
from .serializers import PhotoboothSerializer

class PhotoboothViewSet(viewsets.ModelViewSet):
    queryset = Photobooth.objects.all()
    serializer_class = PhotoboothSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]  # À ajuster selon besoin
