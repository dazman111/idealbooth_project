import django_filters
from .models import Reservation

class ReservationFilter(django_filters.FilterSet):
    start_date = django_filters.DateFilter(field_name="start_date", lookup_expr='gte')
    end_date = django_filters.DateFilter(field_name="end_date", lookup_expr='lte')
    status = django_filters.CharFilter(field_name="status", lookup_expr='iexact')
    photobooth = django_filters.NumberFilter(field_name="photobooth__id")

    class Meta:
        model = Reservation
        fields = ['start_date', 'end_date', 'status', 'photobooth']
