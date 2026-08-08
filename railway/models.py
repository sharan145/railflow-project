from django.db import models
from django.contrib.auth.models import User

class Station(models.Model):
    code = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=100)
    city = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"{self.name} ({self.code})"

class Train(models.Model):
    train_number = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    source = models.ForeignKey(Station, related_name='departures', on_delete=models.CASCADE)
    destination = models.ForeignKey(Station, related_name='arrivals', on_delete=models.CASCADE)
    departure_time = models.TimeField()
    arrival_time = models.TimeField()
    duration = models.CharField(max_length=50)
    available_seats = models.IntegerField(default=50)
    fare = models.DecimalField(max_digits=8, decimal_places=2)

    def __str__(self):
        return f"{self.train_number} - {self.name}"
    
class Booking(models.Model):
    pnr = models.CharField(max_length=10, unique=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    train = models.ForeignKey(Train, on_delete=models.CASCADE)
    passenger_name = models.CharField(max_length=100)
    travel_date = models.DateField()
    seat_number = models.CharField(max_length=50, default="General")
    seat_class = models.CharField(max_length=20, default="CC")
    booked_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"PNR: {self.pnr} | {self.passenger_name} ({self.seat_number})"