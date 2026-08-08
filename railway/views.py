from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from .models import Train, Booking
import random, string

# 1. Main Dashboard (Protected: Requires user to be logged in)
@login_required(login_url='login')
def index(request):
    source = request.GET.get('source', '').strip().upper()
    destination = request.GET.get('destination', '').strip().upper()
    
    # Start by getting all trains from the database so they are visible by default
    trains = Train.objects.all()
    
    # If the user searched for a specific source and destination, filter them
    if source and destination:
        trains = trains.filter(
            source__code__icontains=source, 
            destination__code__icontains=destination
        )
        
    context = {
        'trains': trains,
    }
    return render(request, 'railway/index.html', context)

def dashboard_view(request):
    return render(request, 'railway/index.html')

# 2. Login & Registration Views
def register_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')

        if username and password:
            if not User.objects.filter(username=username).exists():
                user = User.objects.create_user(username=username, email=email, password=password)
                login(request, user)
                return redirect('index')

    return render(request, 'railway/register.html')

def live_radar_view(request):
    query = request.GET.get('train_number', '').strip()
    train = None
    if query:
        train = Train.objects.filter(train_number__icontains=query).first()
    
    context = {
        'train': train,
        'query': query
    }
    return render(request, 'railway/radar.html', context)    

def login_view(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        username = request.POST.get('username')
        password = request.POST.get('password')

        if action == 'register':
            if username and password:
                if not User.objects.filter(username=username).exists():
                    user = User.objects.create_user(username=username, password=password)
                    login(request, user)
                    return redirect('index')
        else:
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('index')
                
    return render(request, 'railway/login.html')

# 3. Checkout Page for a Selected Train
@login_required(login_url='login')
def checkout_view(request, train_id):
    train = get_object_or_404(Train, id=train_id)
    context = {
        'train': train,
        # Razorpay Test Key (Replace with your own test key if desired)
        'razorpay_key_id': 'rzp_test_TLCbEdab9fHvzS' 
    }
    return render(request, 'railway/book_train.html', context)

# 4. Verify Payment and Save Ticket to Database
@login_required(login_url='login')
def verify_payment(request):
    if request.method == 'POST':
        train_id = request.POST.get('train_id')
        passenger_name = request.POST.get('passenger_name')
        travel_date = request.POST.get('travel_date')
        seat_number = request.POST.get('seat_number')  # Captures e.g., "2A - RAC 1"
        
        train = get_object_or_404(Train, id=train_id)
        
        if train.available_seats > 0:
            # Decrement available seats
            train.available_seats -= 1
            train.save()
            
            # Generate Unique PNR
            pnr_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            
            # Extract seat class if included (e.g. "2A" from "2A - RAC 1")
            extracted_class = "CC"
            if seat_number and " - " in seat_number:
                extracted_class = seat_number.split(" - ")[0]
            
            # Save booking to database with user mapping and seat details
            Booking.objects.create(
                pnr=pnr_code,
                user=request.user,
                train=train,
                passenger_name=passenger_name,
                travel_date=travel_date,
                seat_number=seat_number if seat_number else "General",
                seat_class=extracted_class
            )
            return JsonResponse({'status': 'success', 'pnr': pnr_code})
        else:
            return JsonResponse({'status': 'error', 'message': 'Sold out! No seats remaining.'}, status=400)
            
    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)

# 5. Ticket Booking Endpoint (Maps to name='book_ticket')
@login_required(login_url='login')
def book_ticket(request):
    if request.method == 'POST':
        train_id = request.POST.get('train_id')
        passenger_name = request.POST.get('passenger_name')
        travel_date = request.POST.get('travel_date')
        seat_number = request.POST.get('seat_number')
        
        try:
            train = Train.objects.get(id=train_id)
            
            if train.available_seats > 0:
                train.available_seats -= 1
                train.save()
            
            pnr_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            
            extracted_class = "CC"
            if seat_number and " - " in seat_number:
                extracted_class = seat_number.split(" - ")[0]
            
            Booking.objects.create(
                pnr=pnr_code,
                user=request.user,
                train=train,
                passenger_name=passenger_name,
                travel_date=travel_date,
                seat_number=seat_number if seat_number else "General",
                seat_class=extracted_class
            )
            return JsonResponse({'status': 'success', 'pnr': pnr_code})
        except Train.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Train not found'}, status=404)
            
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=400)

# 6. My Bookings Page (Filtered to show only logged-in user's bookings)
@login_required(login_url='login')
def my_bookings_view(request):
    bookings = Booking.objects.filter(user=request.user).order_by('-booked_at')
    return render(request, 'railway/bookings.html', {'bookings': bookings})