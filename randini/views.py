import json
import logging
import requests
from decimal import Decimal
from datetime import datetime, timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from django.db.models import Q, Sum, F, Count
from django.conf import settings
from django.utils import timezone

from .models import Customer, SparePart, Booking, Order, OrderItem, ContactMessage
from .forms import SparePartForm, BookingForm

# Ensure these exist in your utils.py
try:
    from .utils import get_access_token, generate_password, generate_access_token
except ImportError:
    # Fallback placeholders if utils are not ready
    def generate_access_token(): return "token"
    def generate_password(t): return "pass"

logger = logging.getLogger(__name__)

# ============================================================
# 1. PUBLIC & CUSTOMER VIEWS
# ============================================================

def home(request):
    return render(request, "home.html")

def about(request):
    return render(request, 'about.html')

def services(request):
    return render(request, "services.html")

@login_required
def contact(request):
    if request.method == "POST":
        ContactMessage.objects.create(
            name=request.POST.get('name'),
            email=request.POST.get('email'),
            phone=request.POST.get('phone'),
            subject=request.POST.get('subject'),
            message=request.POST.get('message')
        )
        messages.success(request, "Message sent successfully!")
        return redirect('contact') 
    return render(request, 'contact.html')

@login_required
def booking_view(request):
    if request.method == 'POST':
        form = BookingForm(request.POST, request.FILES)
        if form.is_valid():
            booking = form.save(commit=False)
            booking.user = request.user
            booking.save()
            messages.success(request, "Booking submitted successfully!")
            return redirect('user_profile')
    else:
        form = BookingForm()
    return render(request, 'booking.html', {'form': form})

@login_required
def spareparts(request):
    parts = SparePart.objects.all().order_by("-id")
    return render(request, "spareparts.html", {"parts": parts})

@login_required
def user_profile(request):
    context = {
        'bookings': Booking.objects.filter(user=request.user).order_by('-id'),
        'orders': Order.objects.filter(user=request.user).order_by('-created_at'),
    }
    return render(request, 'profile.html', context)

# ============================================================
# 2. CART & SHOPPING SYSTEM
# ============================================================

@login_required
def cart(request):
    cart_session = request.session.get("cart", {})
    cart_items = []
    subtotal = Decimal("0.00")

    for part_id, item_data in cart_session.items():
        try:
            part = SparePart.objects.get(id=part_id)
            quantity = item_data.get("quantity", 0)
            item_total = part.price * quantity
            subtotal += item_total
            cart_items.append({"part": part, "quantity": quantity, "total": item_total})
        except SparePart.DoesNotExist:
            continue

    return render(request, "cart.html", {"cart_items": cart_items, "subtotal": subtotal, "total": subtotal})

@login_required
def add_to_cart(request, part_id):
    part = get_object_or_404(SparePart, id=part_id)
    cart = request.session.get("cart", {})
    part_id_str = str(part_id)
    
    if part_id_str in cart:
        cart[part_id_str]["quantity"] += 1
    else:
        cart[part_id_str] = {"quantity": 1, "price": str(part.price)}

    request.session["cart"] = cart
    messages.success(request, f"{part.name} added to cart!")
    return redirect("cart")

@login_required
def increase_cart(request, part_id):
    cart = request.session.get("cart", {})
    part_id_str = str(part_id)
    if part_id_str in cart:
        cart[part_id_str]["quantity"] += 1
        request.session.modified = True
    return redirect("cart")

@login_required
def decrease_cart(request, part_id):
    cart = request.session.get("cart", {})
    part_id_str = str(part_id)
    if part_id_str in cart:
        cart[part_id_str]["quantity"] -= 1
        if cart[part_id_str]["quantity"] <= 0:
            del cart[part_id_str]
        request.session.modified = True
    return redirect("cart")

@login_required
def remove_from_cart(request, part_id):
    cart = request.session.get("cart", {})
    part_id_str = str(part_id)
    if part_id_str in cart:
        del cart[part_id_str]
        request.session.modified = True
    return redirect("cart")

# ============================================================
# 3. M-PESA & CHECKOUT LOGIC
# ============================================================

@login_required
def checkout(request):
    cart = request.session.get('cart', {})
    if not cart:
        messages.error(request, "Your cart is empty!")
        return redirect('spareparts')

    # Calculate totals
    subtotal = sum(Decimal(item['price']) * item['quantity'] for item in cart.values())
    total_amount = subtotal # Add shipping logic here if needed

    if request.method == 'POST':
        phone = request.POST.get('phone')
        full_name = request.POST.get('full_name')
        email = request.POST.get('email')
        address = request.POST.get('address')
        city = request.POST.get('city')
        payment_method = request.POST.get('payment_method')

        # 1. Clean Phone Number (Must be 2547XXXXXXXX)
        # This takes the last 9 digits and adds 254
        clean_phone = phone.replace(" ", "").replace("+", "")
        formatted_phone = "254" + clean_phone[-9:]

        try:
            with transaction.atomic():
                # 2. Create the Order
                order = Order.objects.create(
                    user=request.user,
                    full_name=full_name,
                    email=email,
                    phone_number=formatted_phone,
                    address=address,
                    city=city,
                    total_amount=total_amount,
                    payment_method=payment_method,
                    status='Pending'
                )

                # 3. Create Order Items
                for item_id, item_data in cart.items():
                    part = SparePart.objects.get(id=item_id)
                    OrderItem.objects.create(
                        order=order,
                        product=part, # Match your model field name (product)
                        price=Decimal(item_data['price']),
                        quantity=item_data['quantity']
                    )

                # 4. Handle M-Pesa Payment
                if payment_method == 'mpesa':
                    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
                    # Use your existing helper functions
                    password = generate_password(timestamp)
                    access_token = generate_access_token()

                    payload = {
                        "BusinessShortCode": "174379",
                        "Password": password,
                        "Timestamp": timestamp,
                        "TransactionType": "CustomerPayBillOnline",
                        "Amount": 1, # Use 1 for testing, or int(total_amount) for production
                        "PartyA": formatted_phone,
                        "PartyB": "174379",
                        "PhoneNumber": formatted_phone,
                        "CallBackURL": "https://your-ngrok-url.ngrok-free.app/mpesa-callback/", 
                        "AccountReference": f"Order{order.id}",
                        "TransactionDesc": f"Payment for Order {order.id}"
                    }

                    response = requests.post(
                        "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest",
                        json=payload, 
                        headers={"Authorization": f"Bearer {access_token}"}
                    )
                    res_data = response.json()

                    if res_data.get('ResponseCode') == '0':
                        order.mpesa_checkout_id = res_data.get('CheckoutRequestID')
                        order.save()
                        
                        # Clear session cart
                        request.session['cart'] = {}
                        messages.success(request, "STK Push sent! Please enter your PIN on your phone.")
                        return redirect('order_success', order_id=order.id)
                    else:
                        # Log Safaricom's specific error message
                        error_msg = res_data.get('CustomerMessage', 'STK Push failed')
                        raise Exception(error_msg)
                
                # 5. Handle Cash on Delivery
                elif payment_method == 'cash':
                    request.session['cart'] = {}
                    messages.success(request, "Order placed successfully! We will contact you for delivery.")
                    return redirect('order_success', order_id=order.id)

        except Exception as e:
            messages.error(request, f"Checkout failed: {str(e)}")
            return redirect('checkout')

    # Pass everything the template needs
    context = {
        'cart_items': cart.values(),
        'subtotal': subtotal,
        'total': total_amount,
    }
    return render(request, 'checkout.html', context)
@csrf_exempt
def mpesa_callback(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            stk_callback = data['Body']['stkCallback']
            result_code = stk_callback['ResultCode']
            checkout_id = stk_callback['CheckoutRequestID']
            
            order = Order.objects.filter(mpesa_checkout_id=checkout_id).first()
            
            if order:
                if result_code == 0:
                    # Payment Successful
                    items = stk_callback['CallbackMetadata']['Item']
                    receipt = next(item['Value'] for item in items if item['Name'] == 'MpesaReceiptNumber')
                    
                    order.status = 'Completed'
                    order.payment_status = 'Paid'
                    order.transaction_id = receipt
                else:
                    # Payment Failed or Cancelled by User
                    order.status = 'Failed'
                    order.payment_status = 'Unpaid'
                
                order.save()
                
        except Exception as e:
            print(f"Callback Error: {e}") # Log this to your terminal
            
        return JsonResponse({"ResultCode": 0, "ResultDesc": "Accepted"})


# ============================================================
# 4. AUTHENTICATION (USER & STAFF)
# ============================================================

# ============================================================
# AUTHENTICATION (USER & STAFF SEPARATION)
# ============================================================

def register_view(request):
    if request.method == "POST":
        p1 = request.POST.get("password1")
        if p1 != request.POST.get("password2"):
            messages.error(request, "Passwords do not match")
            return redirect("register")
        
        username = request.POST.get("username")
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already taken")
            return redirect("register")

        # Create User and the linked Customer profile from your models.py
        user = User.objects.create_user(
            username=username,
            email=request.POST.get("email"),
            password=p1,
            first_name=request.POST.get("name")
        )
        # Link to your Customer model
        Customer.objects.create(user=user, phone=request.POST.get("phone"))
        
        messages.success(request, "Account created! Please log in.")
        return redirect("login")
    return render(request, 'register.html')

def login_view(request):
    """Handles regular customer login"""
    if request.method == "POST":
        user = authenticate(request, username=request.POST.get("username"), password=request.POST.get("password"))
        if user is not None:
            if not user.is_staff:
                login(request, user)
                return redirect("home")
            else:
                # If a staff member tries to use the user login, redirect them
                messages.info(request, "Staff account detected. Please use the Staff Portal.")
                return redirect("staff_login")
        messages.error(request, "Invalid username or password")
    return render(request, "login.html")
@login_required
def order_success(request, order_id):
    # Fetch the order, ensuring it belongs to the logged-in user for security
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    # We fetch the items linked to this order to show a summary
    order_items = OrderItem.objects.filter(order=order)

    context = {
        'order': order,
        'order_items': order_items,
    }
    return render(request, 'order_success.html', context)
def staff_login(request):
    """Handles garage management login"""
    if request.method == "POST":
        user = authenticate(request, username=request.POST.get("username"), password=request.POST.get("password"))
        if user is not None and user.is_staff:
            login(request, user)
            return redirect("staff_dashboard")
        else:
            messages.error(request, "Access Denied: Staff credentials required.")
    return render(request, "staff/login.html")

def logout_view(request):
    logout(request)
    return redirect("login")

# ============================================================
# 5. STAFF ADMINISTRATION DASHBOARD
# ============================================================

# ============================================================
# FIXED: Updated to match your models.py (stock instead of stock_quantity)
# ============================================================

@staff_member_required
def complete_order(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    if request.method == "POST":
        try:
            with transaction.atomic():
                for item in order.items.all():
                    # Your model uses 'product', not 'part'
                    spare_part = item.product 
                    if spare_part.stock >= item.quantity:
                        spare_part.stock -= item.quantity
                        spare_part.save()
                    else:
                        messages.error(request, f"Insufficient stock for {spare_part.name}.")
                        return redirect('staff_orders')

                order.status = 'Completed'
                order.save()
                messages.success(request, f"Order #{order.id} completed!")
        except Exception as e:
            messages.error(request, f"Error: {e}")
    return redirect('staff_orders')

@staff_member_required
def stock_report(request):
    # Your model uses 'stock', not 'stock_quantity'
    low_stock_parts = SparePart.objects.filter(stock__lte=5).order_by('stock')
    all_parts = SparePart.objects.all()
    total_inventory_value = all_parts.aggregate(total=Sum(F('price') * F('stock')))['total'] or 0
    return render(request, 'staff/stock_report.html', {
        'low_stock_parts': low_stock_parts,
        'total_inventory_value': total_inventory_value,
        'all_parts_count': all_parts.count(),
        'low_stock_count': low_stock_parts.count(),
    })

from django.db.models.functions import TruncDay
from django.utils import timezone
from datetime import timedelta

@staff_member_required(login_url="/staff/login/")
def staff_dashboard(request):
    # 1. Basic Stats
    orders = Order.objects.all()
    today = timezone.now()
    seven_days_ago = today - timedelta(days=7)

    # 2. Revenue Trend Data (Line Chart)
    # Groups completed orders by day for the last 7 days
    daily_revenue = (
        Order.objects.filter(status='Completed', created_at__gte=seven_days_ago)
        .annotate(day=TruncDay('created_at'))
        .values('day')
        .annotate(total=Sum('total_amount'))
        .order_by('day')
    )
    
    chart_labels = [entry['day'].strftime('%a') for entry in daily_revenue]
    chart_data = [float(entry['total']) for entry in daily_revenue]

    # 3. Service Mix Data (Doughnut Chart)
    # Counts how many of each service type exists in Bookings
    service_counts = (
        Booking.objects.values('service_type')
        .annotate(count=Count('id'))
    )
    
    service_labels = [s['service_type'].title() for s in service_counts]
    service_data = [s['count'] for s in service_counts]

    context = {
        'total_sales': orders.filter(status='Completed').aggregate(Sum('total_amount'))['total_amount__sum'] or 0,
        'orders_count': orders.count(),
        'pending_count': orders.filter(status='Pending').count(),
        'bookings_count': Booking.objects.count(),
        'inquiries_count': ContactMessage.objects.count(),
        'customers_count': User.objects.filter(is_staff=False).count(),
        'recent_orders': orders.order_by('-created_at')[:5],
        'today': today,
        
        # Chart Data
        'chart_labels': chart_labels,
        'chart_data': chart_data,
        'service_labels': service_labels,
        'service_data': service_data,
    }
    return render(request, 'staff/dashboard.html', context)

@staff_member_required
def staff_orders(request):
    orders = Order.objects.all().order_by('-created_at')
    return render(request, 'staff/orders.html', {'orders': orders})





@staff_member_required
def staff_bookings(request):
    if request.method == "POST":
        booking = get_object_or_404(Booking, id=request.POST.get('booking_id'))
        if request.POST.get('price'): booking.price = Decimal(request.POST.get('price'))
        
        if 'set_pending' in request.POST: booking.status = 'Pending'
        elif 'set_inprogress' in request.POST: booking.status = 'In Progress'
        elif 'set_completed' in request.POST: booking.status = 'Completed'
        elif 'delete_booking' in request.POST: 
            booking.delete()
            return redirect('staff_bookings')
        booking.save()
        return redirect('staff_bookings')

    return render(request, 'staff/bookings.html', {
        'bookings': Booking.objects.all().order_by('-id'),
        'total_revenue': Booking.objects.filter(status='Completed').aggregate(Sum('price'))['price__sum'] or 0
    })

@staff_member_required
def print_receipt(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)
    return render(request, 'staff/receipt_print.html', {'booking': booking, 'today': timezone.now()})

@staff_member_required
def staff_inquiries(request):
    inquiries = ContactMessage.objects.all().order_by('-created_at')
    if request.method == "POST":
        msg_id = request.POST.get('msg_id')
        if 'mark_all_read' in request.POST:
            ContactMessage.objects.filter(is_read=False).update(is_read=True)
        elif msg_id:
            msg = get_object_or_404(ContactMessage, id=msg_id)
            if 'mark_read' in request.POST: msg.is_read = True; msg.save()
            elif 'delete' in request.POST: msg.delete()
        return redirect('staff_inquiries')
    return render(request, 'staff/inquiries.html', {'inquiries': inquiries, 'unread_count': inquiries.filter(is_read=False).count()})
def staff_inventory(request):
    """
    View to display, search, and monitor garage stock levels.
    """
    query = request.GET.get('q', '')
    
    # Base Queryset
    parts = SparePart.objects.all()

    # Apply Search Filter
    if query:
        parts = parts.filter(
            Q(name__icontains=query) | 
            Q(description__icontains=query)
        )

    # Statistics for the Dashboard Cards
    total_items = SparePart.objects.count()
    # Corrected field name: 'stock' instead of 'stock_quantity'
    low_stock_count = SparePart.objects.filter(stock__lt=5).count()

    context = {
        'parts': parts.order_by('name'),
        'query': query,
        'total_items': total_items,
        'low_stock_count': low_stock_count,
    }
    return render(request, 'staff/inventory.html', context)
@staff_member_required
def add_sparepart(request):
    form = SparePartForm(request.POST or None, request.FILES or None)
    if form.is_valid(): form.save(); return redirect("staff_inventory")
    return render(request, "staff/add_sparepart.html", {"form": form})

@staff_member_required
def edit_sparepart(request, pk):
    part = get_object_or_404(SparePart, pk=pk)
    form = SparePartForm(request.POST or None, request.FILES or None, instance=part)
    if form.is_valid(): form.save(); return redirect("staff_inventory")
    return render(request, "staff/edit_sparepart.html", {"form": form, "part": part})

@staff_member_required
def delete_sparepart(request, part_id):
    if request.method == "POST":
        get_object_or_404(SparePart, id=part_id).delete()
    return redirect('staff_inventory')



@staff_member_required
def staff_analytics(request):
    last_30_days = timezone.now() - timedelta(days=30)
    sales_data = Order.objects.filter(created_at__gte=last_30_days, status='Completed')\
        .values('created_at__date').annotate(total=Sum('total_amount')).order_by('created_at__date')

    top_parts = OrderItem.objects.values('product__name')\
        .annotate(total_qty=Sum('quantity')).order_by('-total_qty')[:5]

    context = {
        'sales_labels': [s['created_at__date'].strftime('%d %b') for s in sales_data],
        'sales_values': [float(s['total']) for s in sales_data],
        'part_labels': [p['part__name'] for p in top_parts],
        'part_values': [p['total_qty'] for p in top_parts],
        'total_revenue': Order.objects.filter(status='Completed').aggregate(Sum('total_amount'))['total_amount__sum'] or 0,
        'total_bookings': Booking.objects.count(),
        'report_date': timezone.now(),
    }
    return render(request, 'staff/analytics.html', context)

@staff_member_required
def staff_customers(request):
    """
    View for staff to see all registered customers with search 
    and a count of their total bookings.
    """
    # 1. Get the search term from the URL (e.g., ?q=trizah)
    query = request.GET.get('q', '')

    # 2. Start with all non-staff users and count their related 'bookings'
    # Note: 'bookings' must match the related_name in your Booking model
    customers = User.objects.filter(is_staff=False).annotate(
        num_bookings=Count('bookings')
    )

    # 3. Apply search filters if a query exists
    if query:
        customers = customers.filter(
            Q(first_name__icontains=query) | 
            Q(last_name__icontains=query) | 
            Q(email__icontains=query) |
            Q(username__icontains=query)
        )

    # 4. Sort by most bookings first
    customers = customers.order_by('-num_bookings')

    context = {
        'customers': customers,
        'query': query,
    }
    return render(request, 'staff/customers.html', context)
@staff_member_required
def delete_customer(request, customer_id):
    customer = get_object_or_404(User, id=customer_id)
    if request.method == "POST":
        customer.delete()
        messages.success(request, "Customer deleted.")
        return redirect('staff_customers')
    return render(request, 'staff/customer_confirm_delete.html', {'customer': customer})

@staff_member_required
def staff_settings(request):
    return render(request, 'staff/settings.html', {'user': request.user, 'garage_name': "Randini Auto Garage"})