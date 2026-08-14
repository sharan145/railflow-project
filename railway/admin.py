from django.contrib import admin
from .models import (
    Train, 
    Booking, 
    FoodOrder, 
    EmergencyAlert, 
    StationCrowdRadar, 
    CoachLayout, 
    StationPlatform,
    PnrPrediction
)

admin.site.register(Train)
admin.site.register(Booking)
admin.site.register(FoodOrder)
admin.site.register(EmergencyAlert)
admin.site.register(StationCrowdRadar)
admin.site.register(CoachLayout)
admin.site.register(StationPlatform)
admin.site.register(PnrPrediction)