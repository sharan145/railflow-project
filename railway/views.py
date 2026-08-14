from datetime import datetime, date, timedelta
import random
import string
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.http import JsonResponse
from django.conf import settings
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from django.shortcuts import get_object_or_404, redirect, render
from .models import (
    Booking,
    CoachLayout,
    EmergencyAlert,
    FoodOrder,
    PnrPrediction,
    StationCrowdRadar,
    StationPlatform,
    Train,
    TrainSeat,
)
import base64
from io import BytesIO
import qrcode
from django.views.decorators.http import require_POST

# --- Notification Utility Helper ---
def send_booking_confirmation_notification(user_email, user_phone, booking):
    """
    Sends an automated email & SMS when a ticket is successfully booked or PNR is generated.
    """
    # 1. Send Email via SendGrid
    try:
        message = Mail(
            from_email='no-reply@railflow.com',
            to_emails=user_email,
            subject=f'Booking Confirmed! PNR: {booking.pnr}',
            html_content=f"""
                <div style="font-family: Arial, sans-serif; padding: 20px; border: 1px solid #ddd;">
                    <h2 style="color: #2b6cb0;">RailFlow Ticket Confirmation</h2>
                    <p>Dear <b>{booking.passenger_name}</b>,</p>
                    <p>Your ticket has been successfully booked!</p>
                    <hr>
                    <p><b>Train:</b> {booking.train.train_number} - {booking.train.name}</p>
                    <p><b>PNR Number:</b> {booking.pnr}</p>
                    <p><b>Date of Travel:</b> {booking.travel_date}</p>
                    <p><b>Seat:</b> {booking.seat_class} - {booking.seat_number}</p>
                    <hr>
                    <p>Thank you for traveling with us!</p>
                </div>
            """
        )
        if hasattr(settings, 'SENDGRID_API_KEY') and settings.SENDGRID_API_KEY:
            sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
            sg.send(message)
    except Exception as e:
        print(f"Email notification error: {e}")

    # 2. Send SMS via Twilio (Optional placeholder)
    try:
        pass
    except Exception as e:
        print(f"SMS notification error: {e}")


def digital_ticket_view(request, pnr):
    booking = get_object_or_404(Booking, pnr=pnr)

    qr_data = f"PNR: {booking.pnr} | Train: {booking.train.train_number} - {booking.train.name} | Passenger: {booking.passenger_name} | Seat: {booking.seat_number} | Date: {booking.travel_date}"

    qr = qrcode.QRCode(box_size=10, border=2)
    qr.add_data(qr_data)
    qr.make(fit=True)
    img = qr.make_image(fill_color='black', back_color='white')

    buffer = BytesIO()
    img.save(buffer, format='PNG')
    qr_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

    context = {
        'booking': booking,
        'qr_code': qr_base64,
    }
    return render(request, 'railway/digital_ticket.html', context)

def index(request):
    source = request.GET.get('source', '').strip()
    destination = request.GET.get('destination', '').strip()

    trains = Train.objects.all()

    if source:
        trains = trains.filter(
            Q(source__code__icontains=source)
            | Q(source__name__icontains=source)
            | Q(name__icontains=source)
        )

    if destination:
        trains = trains.filter(
            Q(destination__code__icontains=destination)
            | Q(destination__name__icontains=destination)
            | Q(name__icontains=destination)
        )

    context = {
        'trains': trains,
    }
    return render(request, 'railway/index.html', context)


def dashboard_view(request):
    return render(request, 'railway/index.html')


def platform_led_view(request):
    query = request.GET.get('train_no', '').strip()
    platform_data = None

    if query:
        platform_data = StationPlatform.objects.filter(
            train__train_number__icontains=query
        ).first()

    context = {'platform_data': platform_data, 'query': query}
    return render(request, 'railway/platform_led.html', context)


def register_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')

        if username and password:
            if not User.objects.filter(username=username).exists():
                user = User.objects.create_user(
                    username=username, email=email, password=password
                )
                login(request, user)
                return redirect('index')

    return render(request, 'railway/register.html')


def live_radar_view(request):
    query = request.GET.get('train_number', '').strip()
    train = None
    if query:
        train = Train.objects.filter(train_number__icontains=query).first()

    context = {'train': train, 'query': query}
    return render(request, 'railway/radar.html', context)


def login_view(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        username = request.POST.get('username')
        password = request.POST.get('password')

        if action == 'register':
            if username and password:
                if not User.objects.filter(username=username).exists():
                    user = User.objects.create_user(
                        username=username, password=password
                    )
                    login(request, user)
                    return redirect('index')
        else:
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('index')

    return render(request, 'railway/login.html')


@transaction.atomic
def book_train_view(request, train_id):
    train = get_object_or_404(Train, id=train_id)

    selected_date_str = request.GET.get(
        'date', datetime.today().strftime('%Y-%m-%d')
    )
    selected_class = request.GET.get('class', '3A')
    seat_preference = request.GET.get('pref', request.GET.get('seat_preference', 'WINDOW')).upper()

    try:
        travel_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date()
    except ValueError:
        travel_date = datetime.today().date()

    available_classes = ['1A', '2A', '3A', 'SL', 'CC', 'EC']

    if selected_class not in available_classes:
        selected_class = '3A'

    seats = TrainSeat.objects.filter(
        train=train, travel_date=travel_date, coach_class=selected_class
    )

    if not seats.exists():
        seat_count = 36 if selected_class in ['1A', '2A', 'EC'] else 48
        for i in range(1, seat_count + 1):
            st_type = 'LOWER' if (i % 8 in [1, 4]) else ('WINDOW' if (i % 8 in [3, 6]) else 'AISLE')
            TrainSeat.objects.create(
                train=train,
                travel_date=travel_date,
                coach_class=selected_class,
                seat_number=str(i),
                seat_type=st_type,
                is_booked=False
            )
        seats = TrainSeat.objects.filter(
            train=train, travel_date=travel_date, coach_class=selected_class
        )

    # Smart Recommendation Logic: Fetch the first available seat matching the preference
    recommended_seat = seats.filter(is_booked=False, seat_type__iexact=seat_preference).first()
    if not recommended_seat:
        recommended_seat = seats.filter(is_booked=False).first()

    context = {
        'train': train,
        'seats': seats,
        'recommended_seat': recommended_seat,
        'selected_date': str(travel_date),
        'travel_date': str(travel_date),
        'selected_class': selected_class,
        'coach_class': selected_class,
        'available_classes': available_classes,
        'seat_preference': seat_preference,
        'razorpay_key_id': 'rzp_test_TLCbEdab9fHvzS'
    }
    return render(request, 'railway/book_train.html', context)


def train_list_view(request):
    trains = Train.main.all() if hasattr(Train, 'main') else Train.objects.all()
    
    source_query = request.GET.get('source', '').strip()
    dest_query = request.GET.get('destination', '').strip()
    
    if source_query:
        trains = trains.filter(
            Q(source__code__icontains=source_query) | Q(source__name__icontains=source_query)
        )
    if dest_query:
        trains = trains.filter(
            Q(destination__code__icontains=dest_query) | Q(destination__name__icontains=dest_query)
        )
        
    context = {
        'trains': trains,
        'source_query': source_query,
        'dest_query': dest_query,
    }
    return render(request, 'railway/train_list.html', context)


def train_reservation_chart_view(request, train_id):
    train = get_object_or_404(Train, id=train_id)
    
    selected_date = request.GET.get('date', datetime.today().strftime('%Y-%m-%d'))
    selected_class = request.GET.get('class', '3A')
    
    booked_seats = TrainSeat.objects.filter(
        train=train,
        travel_date=selected_date,
        coach_class=selected_class,
        is_booked=True
    )
    
    available_classes = ['1A', '2A', '3A', 'SL', 'CC', 'EC']
    
    context = {
        'train': train,
        'selected_date': selected_date,
        'selected_class': selected_class,
        'available_classes': available_classes,
        'booked_seats': booked_seats,
    }
    return render(request, 'railway/train_chart.html', context)


@transaction.atomic
def verify_payment(request):
    if request.method == 'POST':
        train_id = request.POST.get('train_id')
        passenger_name = request.POST.get('passenger_name')
        travel_date = request.POST.get('travel_date')
        seat_number = request.POST.get('seat_number')

        train = get_object_or_404(Train, id=train_id)

        extracted_class = 'CC'
        seat_num_val = seat_number if seat_number else 'General'
        if seat_number and ' - ' in seat_number:
            extracted_class, seat_num_val = seat_number.split(' - ', 1)
        elif seat_number and '-' in seat_number:
            extracted_class, seat_num_val = seat_number.split('-', 1)

        if seat_number:
            seat_obj, created = TrainSeat.objects.select_for_update().get_or_create(
                train=train,
                coach_class=extracted_class,
                seat_number=seat_num_val,
                travel_date=travel_date,
                defaults={'is_booked': False},
            )

            if seat_obj.is_booked:
                return JsonResponse(
                    {
                        'status': 'error',
                        'message': 'Oops! This seat was just booked by another passenger. Please choose a different seat.',
                    },
                    status=400,
                )

            seat_obj.is_booked = True
            seat_obj.save()

        if train.available_seats > 0:
            train.available_seats -= 1
            train.save()
        else:
            return JsonResponse(
                {
                    'status': 'error',
                    'message': 'Sold out! No seats remaining.',
                },
                status=400,
            )

        pnr_code = ''.join(
            random.choices(string.ascii_uppercase + string.digits, k=6)
        )

        # Zero-friction support: Assign user if authenticated, else None for guest
        current_user = request.user if request.user.is_authenticated else None

        new_booking = Booking.objects.create(
            pnr=pnr_code,
            user=current_user,
            train=train,
            passenger_name=passenger_name,
            travel_date=travel_date,
            seat_number=seat_number if seat_number else 'General',
            seat_class=extracted_class,
        )

        user_email = current_user.email if current_user and current_user.email else 'passenger@example.com'
        send_booking_confirmation_notification(user_email, '+919876543210', new_booking)

        return JsonResponse({'status': 'success', 'pnr': pnr_code})

    return JsonResponse(
        {'status': 'error', 'message': 'Invalid request'}, status=400
    )


@transaction.atomic
def book_ticket(request):
    if request.method == 'POST':
        train_id = request.POST.get('train_id')
        passenger_name = request.POST.get('passenger_name')
        travel_date = request.POST.get('travel_date')
        seat_number = request.POST.get('seat_number')

        try:
            train = Train.objects.get(id=train_id)

            extracted_class = 'CC'
            seat_num_val = seat_number if seat_number else 'General'
            if seat_number and ' - ' in seat_number:
                extracted_class, seat_num_val = seat_number.split(' - ', 1)
            elif seat_number and '-' in seat_number:
                extracted_class, seat_num_val = seat_number.split('-', 1)

            if seat_number:
                seat_obj, created = TrainSeat.objects.select_for_update().get_or_create(
                    train=train,
                    coach_class=extracted_class,
                    seat_number=seat_num_val,
                    travel_date=travel_date,
                    defaults={'is_booked': False},
                )

                if seat_obj.is_booked:
                    return JsonResponse(
                        {
                            'status': 'error',
                            'message': 'Seat already taken by someone else.',
                        },
                        status=400,
                    )

                seat_obj.is_booked = True
                seat_obj.save()

            if train.available_seats > 0:
                train.available_seats -= 1
                train.save()
            else:
                return JsonResponse(
                    {
                        'status': 'error',
                        'message': 'Train is fully booked.',
                    },
                    status=400,
                )

            pnr_code = ''.join(
                random.choices(string.ascii_uppercase + string.digits, k=6)
            )
            
            # Zero-friction support: Assign user if authenticated, else None for guest
            current_user = request.user if request.user.is_authenticated else None

            new_booking = Booking.objects.create(
                pnr=pnr_code,
                user=current_user,
                train=train,
                passenger_name=passenger_name,
                travel_date=travel_date,
                seat_number=seat_number if seat_number else 'General',
                seat_class=extracted_class,
            )

            user_email = current_user.email if current_user and current_user.email else 'passenger@example.com'
            send_booking_confirmation_notification(user_email, '+919876543210', new_booking)

            return JsonResponse({'status': 'success', 'pnr': pnr_code})
        except Train.DoesNotExist:
            return JsonResponse(
                {'status': 'error', 'message': 'Train not found'}, status=404
            )

    return JsonResponse(
        {'status': 'error', 'message': 'Invalid request method'}, status=400
    )


@transaction.atomic
def cancel_ticket(request, booking_id):
    if request.method == 'POST':
        booking = get_object_or_404(Booking, id=booking_id)

        if not booking.is_cancelled:
            booking.is_cancelled = True
            booking.save()

            train = booking.train
            train.available_seats += 1
            train.save()

            if booking.seat_number:
                coach_class = booking.seat_class
                seat_num = booking.seat_number
                if ' - ' in booking.seat_number:
                    coach_class, seat_num = booking.seat_number.split(
                        ' - ', 1
                    )
                elif '-' in booking.seat_number:
                    coach_class, seat_num = booking.seat_number.split('-', 1)

                TrainSeat.objects.filter(
                    train=train,
                    coach_class=coach_class,
                    seat_number=seat_num,
                    travel_date=booking.travel_date,
                ).update(is_booked=False)

            return JsonResponse(
                {
                    'status': 'success',
                    'message': 'Ticket cancelled successfully. Refund initiated.',
                }
            )
        else:
            return JsonResponse(
                {
                    'status': 'error',
                    'message': 'Ticket is already cancelled.',
                },
                status=400,
            )

    return JsonResponse(
        {'status': 'error', 'message': 'Invalid request method'}, status=400
    )


def station_crowd_radar_view(request):
    train_query = request.GET.get('train_number', '').strip()
    crowd_reports = None
    train = None

    if train_query:
        train = Train.objects.filter(
            train_number__icontains=train_query
        ).first()
        if train:
            crowd_reports = StationCrowdRadar.objects.filter(train=train)

    context = {
        'train': train,
        'train_query': train_query,
        'crowd_reports': crowd_reports,
    }
    return render(request, 'railway/crowd_radar.html', context)


def food_radar_view(request):
    pnr_query = request.GET.get('pnr', '').strip()
    booking = None

    menu_items = [
        {
            'id': 1,
            'name': 'South Indian Veg Thali',
            'price': 360,
            'station': 'Mysuru Junction',
        },
        {'id': 2, 'name': 'Chicken Biryani Deluxe', 'price': 480, 'station': 'Mandya'},
        {
            'id': 3,
            'name': 'Masala Dosa & Filter Coffee',
            'price': 240,
            'station': 'Kengeri',
        },
        {
            'id': 4,
            'name': 'North Indian Paneer Meal',
            'price': 400,
            'station': 'Ramanagaram',
        },
    ]

    if pnr_query:
        booking = Booking.objects.filter(
            pnr=pnr_query, is_cancelled=False
        ).first()

    if request.method == 'POST' and booking:
        item_name = request.POST.get('item_name')
        price = float(request.POST.get('price'))
        station = request.POST.get('station')
        quantity = int(request.POST.get('quantity', 1))
        payment_mode = request.POST.get('payment_mode', 'Online')

        total_amount = price * quantity
        is_paid = True if payment_mode == 'Online' else False

        FoodOrder.objects.create(
            booking=booking,
            item_name=item_name,
            price=price,
            quantity=quantity,
            total_amount=total_amount,
            station_stop=station,
            payment_mode=payment_mode,
            is_paid=is_paid,
        )
        return redirect('my_bookings')

    context = {
        'booking': booking,
        'pnr_query': pnr_query,
        'menu_items': menu_items,
    }
    return render(request, 'railway/food_order.html', context)


def my_bookings_view(request):
    if request.user.is_authenticated:
        # This will show active tickets, and hide them the moment is_cancelled becomes True
        bookings = Booking.objects.filter(user=request.user, is_cancelled=False).order_by(
            '-booked_at'
        )
    else:
        bookings = Booking.objects.filter(is_cancelled=False).order_by('-booked_at')
        
    return render(request, 'railway/bookings.html', {'bookings': bookings})

def food_radar_view(request):
    pnr_query = request.GET.get('pnr', '').strip()
    booking = None

    menu_items = [
        {
            'id': 1,
            'name': 'South Indian Veg Thali',
            'price': 360,
            'station': 'Mysuru Junction',
        },
        {'id': 2, 'name': 'Chicken Biryani Deluxe', 'price': 480, 'station': 'Mandya'},
        {
            'id': 3,
            'name': 'Masala Dosa & Filter Coffee',
            'price': 240,
            'station': 'Kengeri',
        },
        {
            'id': 4,
            'name': 'North Indian Paneer Meal',
            'price': 400,
            'station': 'Ramanagaram',
        },
    ]

    if pnr_query:
        # Removed the strict is_cancelled=False check here so valid PNRs can still order food,
        # but we ensure it's not cancelled via an if check below if needed
        booking = Booking.objects.filter(pnr=pnr_query).first()
        if booking and booking.is_cancelled:
            booking = None # Don't allow food ordering for cancelled tickets

    if request.method == 'POST' and booking:
        item_name = request.POST.get('item_name')
        price = float(request.POST.get('price'))
        station = request.POST.get('station')
        quantity = int(request.POST.get('quantity', 1))
        payment_mode = request.POST.get('payment_mode', 'Online')

        total_amount = price * quantity
        is_paid = True if payment_mode == 'Online' else False

        FoodOrder.objects.create(
            booking=booking,
            item_name=item_name,
            price=price,
            quantity=quantity,
            total_amount=total_amount,
            station_stop=station,
            payment_mode=payment_mode,
            is_paid=is_paid,
        )
        return redirect('my_bookings')

    context = {
        'booking': booking,
        'pnr_query': pnr_query,
        'menu_items': menu_items,
    }
    return render(request, 'railway/food_order.html', context)


@transaction.atomic
def trigger_sos_view(request, booking_id):
    if request.method == 'POST':
        booking = get_object_or_404(Booking, id=booking_id)

        if booking.is_cancelled:
            return JsonResponse({
                'status': 'error',
                'message': 'This booking is already cancelled or refunded.',
            }, status=400)

        refund_amount = float(booking.train.fare) / 2.0

        booking.is_cancelled = True
        booking.save()

        train = booking.train
        train.available_seats += 1
        train.save()

        if booking.seat_number:
            coach_class = booking.seat_class
            seat_num = booking.seat_number
            if ' - ' in booking.seat_number:
                coach_class, seat_num = booking.seat_number.split(' - ', 1)
            elif '-' in booking.seat_number:
                coach_class, seat_num = booking.seat_number.split('-', 1)

            TrainSeat.objects.filter(
                train=train,
                coach_class=coach_class,
                seat_number=seat_num,
                travel_date=booking.travel_date,
            ).update(is_booked=False)

        # Zero-friction support: Assign user if authenticated, else None for guest
        current_user = request.user if request.user.is_authenticated else None

        EmergencyAlert.objects.create(
            booking=booking,
            user=current_user,
            alert_type=request.POST.get(
                'alert_type', 'Medical / Security Emergency'
            ),
            status='Active - RPF Dispatched & 50% Refund Processed',
        )

        return JsonResponse(
            {
                'status': 'success',
                'message': f'🚨 Emergency RPF & Conductor dispatched! Your ticket has been cancelled and a 50% refund of ₹{refund_amount:.2f} has been processed to your online payment method.',
                'refund_amount': refund_amount,
            }
        )

    return JsonResponse(
        {'status': 'error', 'message': 'Invalid request'}, status=400
    )


def coach_composition_view(request):
    pnr_query = request.GET.get('pnr', '').strip()
    booking = None
    coaches = []

    if pnr_query:
        booking = Booking.objects.filter(
            pnr=pnr_query, is_cancelled=False
        ).first()
        if booking:
            coaches = CoachLayout.objects.filter(
                train=booking.train
            ).order_by('position_index')

    context = {
        'booking': booking,
        'pnr_query': pnr_query,
        'coaches': coaches,
    }
    return render(request, 'railway/coach_composition.html', context)


def admin_analytics_view(request):
    active_bookings = Booking.objects.filter(is_cancelled=False)
    total_train_revenue = (
        active_bookings.aggregate(total=Sum('train__fare'))['total'] or 0
    )
    total_tickets_sold = active_bookings.count()
    cancelled_tickets_count = Booking.objects.filter(
        is_cancelled=True
    ).count()

    all_food_orders = FoodOrder.objects.all()
    total_food_revenue = (
        all_food_orders.aggregate(total=Sum('total_amount'))['total'] or 0
    )
    total_food_orders_count = all_food_orders.count()

    online_food_revenue = (
        all_food_orders.filter(payment_mode='Online', is_paid=True).aggregate(
            total=Sum('total_amount')
        )['total']
        or 0
    )
    ontrain_paid_revenue = (
        all_food_orders.filter(payment_mode='OnTrain', is_paid=True).aggregate(
            total=Sum('total_amount')
        )['total']
        or 0
    )
    ontrain_pending_revenue = (
        all_food_orders.filter(payment_mode='OnTrain', is_paid=False).aggregate(
            total=Sum('total_amount')
        )['total']
        or 0
    )

    popular_items = (
        all_food_orders.values('item_name')
        .annotate(order_count=Count('id'), revenue=Sum('total_amount'))
        .order_by('-order_count')
    )

    context = {
        'total_train_revenue': total_train_revenue,
        'total_tickets_sold': total_tickets_sold,
        'cancelled_tickets_count': cancelled_tickets_count,
        'total_food_revenue': total_food_revenue,
        'total_food_orders_count': total_food_orders_count,
        'online_food_revenue': online_food_revenue,
        'ontrain_paid_revenue': ontrain_paid_revenue,
        'ontrain_pending_revenue': ontrain_pending_revenue,
        'popular_items': popular_items,
        'recent_food_orders': all_food_orders.order_by('-ordered_at')[:10],
    }
    return render(request, 'railway/admin_analytics.html', context)