from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('dashboard/', views.index, name='dashboard'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('book/<int:train_id>/', views.book_train_view, name='checkout'),
    path('book-ticket/', views.book_ticket, name='book_ticket'),
    path('verify-payment/', views.verify_payment, name='verify_payment'),
    path('my-bookings/', views.my_bookings_view, name='my_bookings'),
    path('radar/', views.live_radar_view, name='radar'),
    path('cancel-ticket/<int:booking_id>/', views.cancel_ticket, name='cancel_ticket'),
    path('food-on-track/', views.food_radar_view, name='food_order'),
    path('admin-analytics/', views.admin_analytics_view, name='admin_analytics'),
    path('trigger-sos/<int:booking_id>/', views.trigger_sos_view, name='trigger_sos'),
    path('crowd-radar/', views.station_crowd_radar_view, name='crowd_radar'),
    path('coach-composition/', views.coach_composition_view, name='coach_composition'),
    path('platform-led/', views.platform_led_view, name='platform_led'),
    path('trains/', views.train_list_view, name='train_list'),
    path('train/<int:train_id>/chart/', views.train_reservation_chart_view, name='train_chart'),
    path('ticket/<str:pnr>/',views.digital_ticket_view,name='digital_ticket'),
    path('trigger-sos/<int:booking_id>/', views.trigger_sos_view, name='trigger_sos'),
]