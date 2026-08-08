from django.contrib import admin
from .models import Station, Train, Booking

@admin.register(Station)
class StationAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'city')
    search_fields = ('code', 'name', 'city')

@admin.register(Train)
class TrainAdmin(admin.ModelAdmin):
    list_display = ('train_number', 'name', 'source', 'destination', 'available_seats', 'fare')
    search_fields = ('train_number', 'name')
    list_filter = ('source', 'destination')

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('pnr', 'passenger_name', 'train', 'travel_date', 'seat_class', 'booked_at')
    search_fields = ('pnr', 'passenger_name')
    list_filter = ('travel_date', 'seat_class')