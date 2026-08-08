from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('dashboard/', views.index, name='dashboard'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('book/<int:train_id>/', views.checkout_view, name='checkout'),
    path('book-ticket/', views.book_ticket, name='book_ticket'),
    path('verify-payment/', views.verify_payment, name='verify_payment'),
    path('my-bookings/', views.my_bookings_view, name='my_bookings'),
    path('radar/', views.live_radar_view, name='radar'),
]