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
    # Allow user to be blank/null for guest bookings
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    train = models.ForeignKey(Train, on_delete=models.CASCADE)
    pnr = models.CharField(max_length=10, unique=True)
    passenger_name = models.CharField(max_length=100)
    travel_date = models.DateField()
    seat_number = models.CharField(max_length=20)
    seat_class = models.CharField(max_length=10)
    is_cancelled = models.BooleanField(default=False)
    booked_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"PNR: {self.pnr} | {self.passenger_name} ({self.seat_number})"

class FoodOrder(models.Model):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='food_orders')
    item_name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=6, decimal_places=2, default=0.00)
    quantity = models.PositiveIntegerField(default=1)
    total_amount = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    station_stop = models.CharField(max_length=100, default="Station")
    
    PAYMENT_CHOICES = [
        ('Online', 'Paid While Booking (Online)'),
        ('OnTrain', 'Pay on Train (Cash/UPI)'),
    ]
    payment_mode = models.CharField(max_length=20, choices=PAYMENT_CHOICES, default='Online')
    is_paid = models.BooleanField(default=False)
    
    status = models.CharField(max_length=50, default="Preparing")
    ordered_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.quantity}x {self.item_name} - PNR: {self.booking.pnr} ({self.payment_mode})"
    
class CoachLayout(models.Model):
    train = models.ForeignKey(Train, on_delete=models.CASCADE, related_name='coaches')
    coach_identifier = models.CharField(max_length=10) # e.g., "B1", "A2", "S3", "GEN"
    coach_type = models.CharField(max_length=50)        # e.g., "AC 3-Tier", "Sleeper", "General"
    position_index = models.IntegerField(default=1)     # Distance from engine (1 = right behind engine)
    is_pantry = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.train.train_number} - Coach {self.coach_identifier} ({self.coach_type})" 
    
class PnrPrediction(models.Model):
    pnr_number = models.CharField(max_length=10, unique=True)
    train = models.ForeignKey(Train, on_delete=models.CASCADE)
    passenger_name = models.CharField(max_length=100)
    current_status = models.CharField(max_length=50) # e.g., "WL 12", "RAC 3"
    confirmation_probability = models.IntegerField() # e.g., 85 (for 85%)
    prediction_trend = models.CharField(max_length=100) # e.g., "High Chance of Confirmation"
    chart_status = models.CharField(max_length=50, default="CHART NOT PREPARED")

    def __str__(self):
        return f"PNR: {self.pnr_number} - {self.current_status}"    
    
class StationPlatform(models.Model):
    train = models.OneToOneField(Train, on_delete=models.CASCADE, related_name='platform_info')
    platform_number = models.CharField(max_length=10) # e.g., "Platform 3"
    scheduled_time = models.TimeField()
    expected_arrival = models.TimeField()
    status_message = models.CharField(max_length=100, default="ON TIME") # e.g., "ON TIME", "DELAYED 15 MINS"
    announcement_notice = models.CharField(max_length=200, blank=True, null=True) # e.g., "Train arriving shortly"

    def __str__(self):
        return f"{self.train.train_number} - {self.platform_number}"      
    
class EmergencyAlert(models.Model):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='emergencies')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    alert_type = models.CharField(max_length=50, default="Medical & Security SOS")
    status = models.CharField(max_length=50, default="Active / Dispatched")
    triggered_at = models.DateTimeField(auto_now_add=True)
    resolved = models.BooleanField(default=False)

    def __str__(self):
        return f"SOS - PNR: {self.booking.pnr} ({self.status})"
    
class TrainSeat(models.Model):
    train = models.ForeignKey('Train', on_delete=models.CASCADE)
    coach_class = models.CharField(max_length=10) # e.g., '2A', '3A', 'SL'
    seat_number = models.CharField(max_length=20) # e.g., 'AVL-0110', 'RAC 1'
    travel_date = models.DateField()
    is_booked = models.BooleanField(default=False) # Tracks if it's taken

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)    
        
class TrainSeat(models.Model):
    SEAT_TYPE_CHOICES = [
        ('WINDOW', 'Window Seat'),
        ('AISLE', 'Aisle Seat'),
        ('MIDDLE', 'Middle / General'),
        ('LOWER', 'Lower Berth (Senior/Pref)'),
    ]

    train = models.ForeignKey(Train, on_delete=models.CASCADE)
    travel_date = models.DateField()
    coach_class = models.CharField(max_length=10) # e.g., '3A', 'SL', 'CC'
    seat_number = models.CharField(max_length=10)
    seat_type = models.CharField(max_length=20, choices=SEAT_TYPE_CHOICES, default='WINDOW')
    is_booked = models.BooleanField(default=False)

def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Automatically assign a seat type based on seat number if not set
        if not self.seat_type and self.seat_number.isdigit():
            num = int(self.seat_number)
            if num % 8 == 1 or num % 8 == 4: # Standard Indian Railway layout logic
                self.seat_type = 'LOWER'
            elif num % 8 == 3 or num % 8 == 6:
                self.seat_type = 'WINDOW'
            else:
                self.seat_type = 'AISLE'        
    
class StationCrowdRadar(models.Model):
    train = models.ForeignKey(Train, on_delete=models.CASCADE, related_name='crowd_stats')
    station_name = models.CharField(max_length=100)
    platform_number = models.CharField(max_length=10, default="1")
    congestion_level = models.CharField(max_length=50, default="Moderate") # Low, Moderate, High Congestion
    estimated_arrival = models.CharField(max_length=50, default="On Time")
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.train.train_number} @ {self.station_name} - {self.congestion_level}"