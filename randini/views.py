"""
views.py — Randini Auto Garage
================================
All view functions organised into clear sections:

  1. Public & Customer Pages  — home, about, services, contact, booking, profile
  2. Cart & Shopping          — add, remove, increase, decrease cart items
  3. Checkout & M-Pesa        — checkout form, STK push, payment callback
  4. Authentication           — register (with OTP), OTP verify, login, logout
  5. Staff Dashboard          — role-aware dashboard, stats, charts
  6. Staff — Orders           — list orders, view order detail, complete order
  7. Staff — Bookings         — list bookings, update status/price
  8. Staff — Inventory        — list/add/edit/delete spare parts, stock report
  9. Staff — Customers        — list customers, view customer detail, delete
 10. Staff — Analytics        — sales charts, revenue, part popularity
 11. Staff — Inquiries        — view/mark-read/delete contact messages
 12. Staff — User Management  — admin creates/edits/deletes staff accounts
 13. Staff — Settings         — staff personal settings page
"""

# Standard Python library imports
import json          # JSON serialization for API responses
import logging       # Logging for debugging and error tracking
import random        # Random number generation for OTP
import string        # String manipulation for OTP generation
from decimal import Decimal  # Precise decimal arithmetic for financial calculations
from datetime import timedelta  # Date/time calculations for expirations

# Django core imports
from django.shortcuts import render, redirect, get_object_or_404  # Common view utilities
from django.contrib.auth.forms import PasswordChangeForm  # Password change form
from django.http import JsonResponse  # JSON response handling for AJAX
from django.contrib import messages  # Flash messages for user feedback
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash  # User authentication
from django.contrib.auth.models import User  # Django's built-in User model
from django.contrib.auth.decorators import login_required, user_passes_test  # Authentication decorators
from django.contrib.admin.views.decorators import staff_member_required  # Staff access control
from django.contrib.auth import get_user_model  # Get active User model
from django.utils import timezone  # Timezone-aware datetime utilities
from django.core.mail import send_mail  # Email sending functionality
from django.db import IntegrityError
from django.db.models import Sum, Count, F  # Database aggregation functions
from django.db.models.functions import TruncDay, TruncDate  # Database date truncation functions
from django.views.decorators.csrf import csrf_exempt  # CSRF exemption decorator

# Import custom forms from local forms module
from .forms import InvoiceForm, QuickInvoiceForm  # Invoice generation forms

# Import models from local models module
from .models import SparePart, ContactMessage, Order, Booking, UserProfile  # Core business models

# Get the active User model (allows for custom User models)
User = get_user_model()

# ─────────────────────────────────────────────────────────────
# ROLE-BASED ACCESS CONTROL DECORATORS
# ─────────────────────────────────────────────────────────────

def role_required(*roles):
    """Decorator to require specific staff roles for view access.
    
    This decorator ensures that only users with specified roles can access
    certain views. Superusers bypass role restrictions.
    
    Args:
        *roles (str): Variable number of allowed role names
        
    Returns:
        function: Decorated view function with role checking
    """
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            # Check if user is authenticated
            if not request.user.is_authenticated:
                return redirect('staff_login')
            
            # Check if user has staff or superuser privileges
            if not (request.user.is_staff or request.user.is_superuser):
                return redirect('staff_login')
            
            # Get user's role from UserProfile
            try:
                user_role = request.user.profile.role
            except UserProfile.DoesNotExist:
                user_role = 'admin'  # Default for superusers without profile
            
            # Check if user's role is in allowed roles or is superuser
            if user_role not in roles and not request.user.is_superuser:
                # Redirect unauthorized users to their appropriate dashboard
                role_redirects = {
                    'mechanic': 'mechanic_dashboard',
                    'inventory': 'inventory_dashboard', 
                    'inquiries': 'inquiries_dashboard',
                    'admin': 'staff_dashboard'
                }
                return redirect(role_redirects.get(user_role, 'staff_dashboard'))
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator

def is_mechanic(user):
    """Check if user has mechanic role.
    
    Args:
        user: Django User object
        
    Returns:
        bool: True if user is authenticated and has mechanic role
    """
    return user.is_authenticated and (user.is_staff or user.is_superuser) and hasattr(user, 'staff_profile') and user.staff_profile.role == 'mechanic'

def is_inventory_manager(user):
    """Check if user has inventory manager role.
    
    Args:
        user: Django User object
        
    Returns:
        bool: True if user is authenticated and has inventory role
    """
    return user.is_authenticated and (user.is_staff or user.is_superuser) and hasattr(user, 'staff_profile') and user.staff_profile.role == 'inventory'

def is_inquiries_officer(user):
    """Check if user has inquiries officer role.
    
    Args:
        user: Django User object
        
    Returns:
        bool: True if user is authenticated and has inquiries role
    """
    return user.is_authenticated and (user.is_staff or user.is_superuser) and hasattr(user, 'staff_profile') and user.staff_profile.role == 'inquiries'

def is_admin(user):
    """Check if user has admin role or is superuser.
    
    Args:
        user: Django User object
        
    Returns:
        bool: True if user is superuser or has admin role
    """
    return user.is_authenticated and (user.is_staff or user.is_superuser) and (user.is_superuser or (hasattr(user, 'staff_profile') and user.staff_profile.role == 'admin'))


# Import all required models for comprehensive functionality
from .models import (
    UserProfile,         # Unified user profile model
    SparePart,          # Inventory management model
    Booking,            # Service booking model
    Order,              # Parts purchase order model
    OrderItem,          # Order line items model
    ContactMessage,     # Customer inquiry model
    Service             # Service pricing model
)
from .forms import (
    SparePartForm, BookingForm, StaffRegistrationForm,
    CustomerRegistrationForm, CustomerProfileForm
)

# Import M-Pesa utility (falls back gracefully if not configured)
try:
    from .utils import trigger_stk_push
except ImportError:
    def trigger_stk_push(phone, amount):
        return {'ResponseCode': '1', 'errorMessage': 'M-Pesa utils not configured'}

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════
# HELPER: send feedback toast to template
# ════════════════════════════════════════════════════════════
def _flash(request, level, msg):
    """Shorthand for adding a Bootstrap-styled Django message."""
    getattr(messages, level)(request, msg)


# ════════════════════════════════════════════════════════════
# 1. PUBLIC & CUSTOMER PAGES
# ════════════════════════════════════════════════════════════

def home(request):
    """Public landing page - shows featured services from database."""
    services = Service.objects.filter(is_active=True).order_by('service_type')[:4]
    return render(request, 'home.html', {'services': services})


def about(request):
    """About the garage."""
    return render(request, 'about.html')


def services(request):
    """Services listing page - displays active services from database."""
    services = Service.objects.filter(is_active=True).order_by('service_type')
    return render(request, 'services.html', {'services': services})


def contact(request):
    """
    Contact form — saves a ContactMessage to the database.
    Staff can read and respond from the Inquiries module.
    Enhanced with proper validation and error handling.
    """
    if request.method == 'POST':
        try:
            # Validate required fields
            name = request.POST.get('name', '').strip()
            email = request.POST.get('email', '').strip()
            phone = request.POST.get('phone', '').strip()
            inquiry_type = request.POST.get('inquiry_type', 'general').strip()
            subject = request.POST.get('subject', '').strip()
            message = request.POST.get('message', '').strip()
            
            # Basic validation
            if not name or len(name) < 2:
                _flash(request, 'error', 'Please enter your full name (minimum 2 characters).')
                return redirect('contact')
            
            if not email or '@' not in email:
                _flash(request, 'error', 'Please enter a valid email address.')
                return redirect('contact')
            
            if not phone or len(phone) < 9:
                _flash(request, 'error', 'Please enter a valid phone number (minimum 9 digits).')
                return redirect('contact')
            
            if not subject or len(subject) < 3:
                _flash(request, 'error', 'Please enter a subject (minimum 3 characters).')
                return redirect('contact')
            
            if not message or len(message) < 10:
                _flash(request, 'error', 'Please enter a message (minimum 10 characters).')
                return redirect('contact')

            # Validate inquiry type
            valid_types = ['general', 'service', 'parts', 'booking', 'complaint', 'feedback', 'other']
            if inquiry_type not in valid_types:
                _flash(request, 'error', 'Please select a valid inquiry type.')
                return redirect('contact')

            # Create the contact message
            contact_msg = ContactMessage.objects.create(
                name=name,
                email=email,
                phone=phone,
                inquiry_type=inquiry_type,
                subject=subject,
                message=message
            )
            
            logger.info(f"Contact message #{contact_msg.id} created by {name} ({email})")
            _flash(request, 'success', 'Your message has been sent! We will get back to you shortly.')
            return redirect('contact')
            
        except Exception as e:
            logger.error(f"Contact form submission error: {e}")
            _flash(request, 'error', f'Failed to send message: {str(e)}')
            
    return render(request, 'contact.html')


@login_required
def booking_view(request):
    """
    Customer books a vehicle service appointment.
    Links the booking to the logged-in user automatically.
    Enhanced with proper validation and error handling.
    """
    if request.method == 'POST':
        form = BookingForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                with transaction.atomic():
                    booking = form.save(commit=False)
                    booking.user = request.user
                    
                    # Ensure required fields are properly set
                    if not booking.full_name:
                        booking.full_name = f"{request.user.first_name} {request.user.last_name}".strip()
                    if not booking.email:
                        booking.email = request.user.email
                    
                    booking.save()
                    
                    # Log successful booking
                    logger.info(f"Booking #{booking.id} created for user {request.user.email}")
                    
                    _flash(request, 'success', 'Booking submitted successfully! We will confirm shortly.')
                    return redirect('user_profile')
                    
            except Exception as e:
                logger.error(f"Booking creation error: {e}")
                _flash(request, 'error', f'Failed to create booking: {str(e)}')
        else:
            # Log form errors for debugging
            logger.error(f"Booking form errors: {form.errors}")
            for field, errors in form.errors.items():
                for error in errors:
                    _flash(request, 'error', f'{field}: {error}')
    else:
        form = BookingForm()
    
    return render(request, 'booking.html', {'form': form})


@login_required
def spareparts(request):
    """Spare parts catalogue — all customers can browse and add to cart."""
    query = request.GET.get('q', '')
    parts = SparePart.objects.filter(stock__gt=0).order_by('-id')
    if query:
        parts = parts.filter(Q(name__icontains=query) | Q(description__icontains=query))
    return render(request, 'spareparts.html', {'parts': parts, 'query': query})





# ════════════════════════════════════════════════════════════
# 2. CART & SHOPPING SYSTEM
# ════════════════════════════════════════════════════════════

@login_required
def cart(request):
    """
    Reads the cart from the session and renders it.
    Cart is stored as {part_id: {quantity, price}} in request.session['cart'].
    """
    cart_session = request.session.get('cart', {})
    cart_items = []
    subtotal = Decimal('0.00')

    for part_id, item_data in cart_session.items():
        try:
            part = SparePart.objects.get(id=part_id)
            qty = item_data.get('quantity', 0)
            item_total = part.price * qty
            subtotal += item_total
            cart_items.append({'part': part, 'quantity': qty, 'total': item_total})
        except SparePart.DoesNotExist:
            continue  # Skip if a part was deleted from inventory

    return render(request, 'cart.html', {
        'cart_items': cart_items, 'subtotal': subtotal, 'total': subtotal
    })


@login_required
def add_to_cart(request, part_id):
    """Adds one unit of a spare part to the session cart."""
    part = get_object_or_404(SparePart, id=part_id)
    cart = request.session.get('cart', {})
    key  = str(part_id)
    if key in cart:
        cart[key]['quantity'] += 1
    else:
        cart[key] = {'quantity': 1, 'price': str(part.price)}
    request.session['cart'] = cart
    _flash(request, 'success', f'{part.name} added to cart!')
    return redirect('spareparts')


@login_required
def increase_cart(request, part_id):
    """Increases the quantity of a cart item by 1."""
    cart = request.session.get('cart', {})
    key  = str(part_id)
    if key in cart:
        cart[key]['quantity'] += 1
        request.session.modified = True
    return redirect('cart')


@login_required
def decrease_cart(request, part_id):
    """Decreases the quantity of a cart item by 1; removes it if quantity hits 0."""
    cart = request.session.get('cart', {})
    key  = str(part_id)
    if key in cart:
        cart[key]['quantity'] -= 1
        if cart[key]['quantity'] <= 0:
            del cart[key]
        request.session.modified = True
    return redirect('cart')


@login_required
def remove_from_cart(request, part_id):
    """Removes a spare part entirely from the session cart."""
    cart = request.session.get('cart', {})
    key  = str(part_id)
    if key in cart:
        del cart[key]
        request.session.modified = True
    return redirect('cart')


# ════════════════════════════════════════════════════════════
# 3. CHECKOUT & M-PESA PAYMENT
# ════════════════════════════════════════════════════════════

@login_required
def checkout(request):
    """
    Handles the two-step checkout:
      GET  → renders the form with cart summary
      POST → creates Order + OrderItems, then either triggers M-Pesa STK push
             or marks Cash-on-Delivery order as pending for staff confirmation.
    """
    cart = request.session.get('cart', {})
    if not cart:
        _flash(request, 'error', 'Your cart is empty!')
        return redirect('spareparts')

    subtotal     = sum(Decimal(item['price']) * item['quantity'] for item in cart.values())
    total_amount = subtotal

    if request.method == 'POST':
        phone          = request.POST.get('phone', '')
        full_name      = request.POST.get('full_name', '')
        email          = request.POST.get('email', '')
        address        = request.POST.get('address', '')
        city           = request.POST.get('city', '')
        payment_method = request.POST.get('payment_method', 'cash')

        # Normalise Kenyan phone to 2547XXXXXXXX format
        clean_phone    = ''.join(filter(str.isdigit, phone))
        formatted_phone = '254' + clean_phone[-9:]

        try:
            with transaction.atomic():
                # Create the parent Order record
                order = Order.objects.create(
                    user=request.user,
                    full_name=full_name, email=email,
                    phone_number=formatted_phone, address=address,
                    city=city, total_amount=total_amount,
                    payment_method=payment_method, status='Pending'
                )

                # Create one OrderItem per cart entry
                for item_id, item_data in cart.items():
                    part = SparePart.objects.get(id=item_id)
                    OrderItem.objects.create(
                        order=order, product=part,
                        price=Decimal(item_data['price']),
                        quantity=item_data['quantity']
                    )

                # ── M-Pesa path ──────────────────────────────────
                if payment_method == 'mpesa':
                    res_data = trigger_stk_push(formatted_phone, int(total_amount))
                    logger.debug(f"M-Pesa STK response for Order #{order.id}: {res_data}")

                    if res_data.get('ResponseCode') == '0':
                        order.mpesa_checkout_id = res_data.get('CheckoutRequestID')
                        order.save()
                        request.session['cart'] = {}
                        _flash(request, 'success', 'M-Pesa prompt sent! Check your phone and enter your PIN.')
                        return redirect('order_success', order_id=order.id)
                    else:
                        error_msg = res_data.get('CustomerMessage') or res_data.get('errorMessage') or 'STK Push failed'
                        raise Exception(error_msg)

                # ── Cash-on-Delivery path ────────────────────────
                elif payment_method == 'cash':
                    request.session['cart'] = {}
                    _flash(request, 'success', 'Order placed! You will pay on delivery.')
                    return redirect('order_success', order_id=order.id)

        except Exception as e:
            logger.error(f"Checkout error: {e}")
            _flash(request, 'error', f'Checkout failed: {e}')
            return redirect('checkout')

    return render(request, 'checkout.html', {
        'cart_items': cart.values(), 'subtotal': subtotal, 'total': total_amount
    })


@login_required
def order_success(request, order_id):
    """
    Confirmation page shown after a successful order is placed.
    Security: ensures the order belongs to the currently logged-in user.
    """
    order       = get_object_or_404(Order, id=order_id, user=request.user)
    order_items = OrderItem.objects.filter(order=order)
    return render(request, 'order_success.html', {'order': order, 'order_items': order_items})


@csrf_exempt
def mpesa_callback(request):
    """
    Webhook called by Safaricom after a customer enters their M-Pesa PIN.
    Receives JSON payload and updates Order status accordingly.
    Must be publicly accessible (not behind @login_required).
    """
    if request.method == 'POST':
        try:
            # Log the raw callback data for debugging
            raw_data = request.body.decode('utf-8')
            logger.info(f"M-Pesa callback received: {raw_data}")
            
            data = json.loads(request.body)
            
            # Handle both callback formats
            if 'Body' in data and 'stkCallback' in data['Body']:
                stk_callback = data['Body']['stkCallback']
                result_code = stk_callback.get('ResultCode')
                checkout_id = stk_callback.get('CheckoutRequestID')
                
                logger.info(f"Processing M-Pesa callback - CheckoutID: {checkout_id}, ResultCode: {result_code}")
                
                order = Order.objects.filter(mpesa_checkout_id=checkout_id).first()
                if order:
                    if result_code == 0:
                        # Extract the M-Pesa receipt number from the callback metadata
                        callback_metadata = stk_callback.get('CallbackMetadata', {})
                        items = callback_metadata.get('Item', [])
                        
                        receipt = None
                        phone = None
                        amount = None
                        
                        for item in items:
                            if item.get('Name') == 'MpesaReceiptNumber':
                                receipt = item.get('Value')
                            elif item.get('Name') == 'PhoneNumber':
                                phone = item.get('Value')
                            elif item.get('Name') == 'Amount':
                                amount = item.get('Value')
                        
                        order.status = 'Completed'
                        order.transaction_id = receipt
                        order.mpesa_phone = phone
                        order.mpesa_amount = amount
                        logger.info(f"Order #{order.id} marked as completed with receipt {receipt}")
                    else:
                        order.status = 'Failed'
                        error_desc = stk_callback.get('ResultDesc', 'Unknown error')
                        order.mpesa_error = error_desc
                        logger.warning(f"Order #{order.id} marked as failed: {error_desc}")
                    
                    order.save()
                else:
                    logger.error(f"No order found for CheckoutRequestID: {checkout_id}")
            else:
                logger.error(f"Invalid M-Pesa callback format: {data}")
                
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error in M-Pesa callback: {e}")
        except Exception as e:
            logger.error(f"M-Pesa callback processing error: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
    
    return JsonResponse({'ResultCode': 0, 'ResultDesc': 'Accepted'})


# ════════════════════════════════════════════════════════════
# 4. AUTHENTICATION  (Register with OTP, Login, Logout)
# ════════════════════════════════════════════════════════════

def register(request):
    """
    Simplified customer registration with OTP verification.
    Step 1: Collect user info and send OTP.
    """
    if request.method == 'POST':
        form = CustomerRegistrationForm(request.POST)
        profile_form = CustomerProfileForm(request.POST)
        
        if form.is_valid() and profile_form.is_valid():
            first_name = form.cleaned_data['first_name']
            last_name = form.cleaned_data['last_name']
            email = form.cleaned_data['email'].lower().strip()
            password = form.cleaned_data['password1']
            phone = profile_form.cleaned_data['phone_number']

            # Store pending registration in session
            request.session['pending_registration'] = {
                'first_name': first_name,
                'last_name': last_name,
                'email': email,
                'password': password,
                'phone': phone
            }

            # Generate and send OTP
            import random, string, time
            from django.utils import timezone
            from .utils import send_otp_email
            
            otp_code = ''.join(random.choices(string.digits, k=6))
            print("OTP for {} is {}".format(email, otp_code))
            
            # Create temporary user for OTP storage
            temp_user = User.objects.create_user(
                username=f"temp_{email}_{int(time.time())}",
                email=email,
                password='temp_password',
                first_name=first_name,
                last_name=last_name,
                is_active=False
            )
            temp_profile = UserProfile.objects.create(user=temp_user, phone_number=phone, role='customer')
            temp_profile.otp = otp_code
            temp_profile.otp_created_at = timezone.now()
            temp_profile.otp_is_used = False
            temp_profile.save()
            
            # Store temp user ID in session for cleanup
            request.session['temp_user_id'] = temp_user.id
            
            # Send OTP via email
            if send_otp_email(email, otp_code, first_name):
                _flash(request, 'success', f'A 6-digit verification code has been sent to {email}.')
                return redirect('verify_otp')
            else:
                _flash(request, 'error', 'Could not send verification email. Please try again.')
                return redirect('register')
    else:
        form = CustomerRegistrationForm()
        profile_form = CustomerProfileForm()

    return render(request, 'register.html', {
        'form': form,
        'profile_form': profile_form
    })


def verify_otp(request):
    """
    Step 2 of registration: verify the OTP sent to the user's email.
    On success, creates the User + Customer profile and logs them in.
    """
    pending = request.session.get('pending_registration')
    if not pending:
        return redirect('register')

    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        entered_otp = request.POST.get('otp', '').strip()
        email       = pending['email']
        
        print(f"DEBUG: Entered OTP: '{entered_otp}' for email: {email}")

        # Find most recent unused OTP for this email (including temp users)
        otp_record = UserProfile.objects.filter(
            user__email=email, otp_is_used=False
        ).order_by('-created_at').first()

        if not otp_record:
            print("DEBUG: No OTP record found")
            _flash(request, 'error', 'Invalid verification code. Please check and try again.')
            return redirect('verify_otp')

        print(f"DEBUG: Found OTP record: {otp_record.otp} for user: {otp_record.user.username}")

        # Check if OTP is expired using the model method
        if otp_record.is_expired_otp():
            print("DEBUG: OTP is expired")
            _flash(request, 'error', 'Your code has expired. Please request a new one.')
            # Clean up expired temp user
            if otp_record.user.username.startswith('temp_'):
                otp_record.user.delete()
            return redirect('verify_otp')

        if otp_record.otp != entered_otp:
            print(f"DEBUG: OTP mismatch. Stored: '{otp_record.otp}', Entered: '{entered_otp}'")
            _flash(request, 'error', 'Invalid verification code. Please check and try again.')
            return redirect('verify_otp')

        # Store OTP id for marking as used after successful registration
        pending['otp_id'] = otp_record.id

        # Store confirmed data for final registration
        request.session['confirmed_registration'] = pending
        return redirect('confirm_registration')

    context = {'email': pending.get('email', '')}
    if settings.DEBUG:
        # For development, show the OTP for testing
        otp_record = UserProfile.objects.filter(user__email=pending['email'], otp_is_used=False).order_by('-created_at').first()
        if otp_record:
            context['debug_otp'] = otp_record.otp
    return render(request, 'verify_otp.html', context)


def confirm_registration(request):
    """
    Final step of registration: confirm user details and create account.
    """
    confirmed = request.session.get('confirmed_registration')
    if not confirmed:
        return redirect('register')

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'accept':
            try:
                # Get the temporary user and convert it to permanent
                temp_user_id = request.session.get('temp_user_id')
                if temp_user_id:
                    temp_user = User.objects.get(id=temp_user_id)
                    temp_user.username = confirmed['email']
                    temp_user.set_password(confirmed['password'])
                    temp_user.first_name = confirmed['first_name']
                    temp_user.last_name = confirmed['last_name']
                    temp_user.is_active = True
                    temp_user.save()
                    
                    # Update the user profile
                    customer = temp_user.profile
                    customer.phone_number = confirmed.get('phone', '0000000000')
                    customer.role = 'customer'
                    customer.save()
                    
                    user = temp_user
                else:
                    # Fallback: create new user if no temp user found
                    user = User.objects.create_user(
                        username=confirmed['email'],               # email IS the username
                        email=confirmed['email'],
                        password=confirmed['password'],
                        first_name=confirmed['first_name'],
                        last_name=confirmed['last_name'],
                    )
                    customer = UserProfile.objects.create(user=user, phone_number=confirmed.get('phone', '0000000000'), role='customer')
            except (IntegrityError, User.DoesNotExist):
                _flash(request, 'error', 'This email is already registered. Please try logging in instead.')
                return render(request, 'confirm_registration.html', confirmed)

            # Mark OTP as used
            otp_id = confirmed.get('otp_id')
            if otp_id:
                try:
                    otp_record = UserProfile.objects.get(id=otp_id)
                    otp_record.otp_is_used = True
                    otp_record.save()
                except UserProfile.DoesNotExist:
                    pass  # OTP already handled

            # Send welcome email
            try:
                from .utils import send_welcome_email
                send_welcome_email(customer)
            except Exception as e:
                logger.error(f"Welcome email error: {e}")
                # Don't fail registration if welcome email fails

            # Clean up session and log the user in immediately
            del request.session['confirmed_registration']
            del request.session['pending_registration']  # Clean up pending as well
            del request.session['temp_user_id']  # Clean up temp user reference
            login(request, user)
            _flash(request, 'success', f'Welcome to Randini Garage, {user.first_name}!')
            return redirect('home')

        elif action == 'cancel':
            # Clean up temporary user and redirect to register
            temp_user_id = request.session.get('temp_user_id')
            if temp_user_id:
                try:
                    temp_user = User.objects.get(id=temp_user_id)
                    temp_user.delete()
                except User.DoesNotExist:
                    pass
            
            del request.session['confirmed_registration']
            del request.session['pending_registration']  # Clean up pending as well
            del request.session['temp_user_id']  # Clean up temp user reference
            _flash(request, 'info', 'Registration cancelled. You can register again if needed.')
            return redirect('register')
    
def resend_otp(request):
    """Resends a fresh OTP to pending registration email with rate limiting."""
    pending = request.session.get('pending_registration')
    if not pending:
        return redirect('register')
    
    # Rate limiting: Check last resend time
    last_resend = request.session.get('last_otp_resend')
    from django.utils import timezone
    now = timezone.now()
    
    if last_resend:
        time_diff = (now - last_resend).total_seconds()
        if time_diff < 60:  # Only allow resend every 60 seconds
            _flash(request, 'error', f'Please wait {60 - int(time_diff)} seconds before requesting another code.')
            return redirect('verify_otp')
    
    email = pending['email']
    first_name = pending['first_name']
    last_name = pending['last_name']
    phone = pending['phone']
    
    import random, string, time
    from .utils import send_otp_email
    
    otp_code = ''.join(random.choices(string.digits, k=6))
    print("OTP for {} is {}".format(email, otp_code))
    
    # Clean up any existing temp user for this email
    temp_user_id = request.session.get('temp_user_id')
    if temp_user_id:
        try:
            old_temp_user = User.objects.get(id=temp_user_id)
            old_temp_user.delete()
        except User.DoesNotExist:
            pass
    
    # Create new temporary user for OTP storage
    temp_user = User.objects.create_user(
        username=f"temp_{email}_{int(time.time())}",
        email=email,
        password='temp_password',
        first_name=first_name,
        last_name=last_name,
        is_active=False
    )
    temp_profile = UserProfile.objects.create(user=temp_user, phone_number=phone, role='customer')
    temp_profile.otp = otp_code
    temp_profile.otp_created_at = timezone.now()
    temp_profile.otp_is_used = False
    temp_profile.save()
    
    # Store new temp user ID in session
    request.session['temp_user_id'] = temp_user.id
    request.session['last_otp_resend'] = now
    
    # Send OTP via email
    if send_otp_email(email, otp_code, first_name):
        _flash(request, 'success', 'A new verification code has been sent to your email.')
    else:
        _flash(request, 'error', 'Could not send verification email. Please try again.')
    
    return redirect('verify_otp')


def login_view(request):
    """
    Customers and staff log in with EMAIL + password.
    After login, staff are redirected based on their StaffProfile role:
      mechanic   → bookings
      inventory  → inventory
      inquiries  → inquiries
      admin      → dashboard
    Customers → home page.
    """
    if request.method == 'POST':
        email    = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')

        # Username field in DB is set to the email address
        user = authenticate(request, username=email, password=password)

        if user is not None:
            login(request, user)
            if user.is_staff:
                # Route to role-specific page
                try:
                    role = user.profile.role
                except UserProfile.DoesNotExist:
                    role = 'admin'
                role_redirects = {
                    'mechanic':  'staff_bookings',
                    'inventory': 'staff_inventory', 
                    'inquiries': 'staff_inquiries',
                }
                return redirect(role_redirects.get(role, 'staff_dashboard'))
            else:
                return redirect('home')

        _flash(request, 'error', 'Invalid email or password. Please try again.')

    return render(request, 'login.html')


def staff_login(request):
    """
    Dedicated staff login page at /staff/login/.
    Accepts staff and superuser credentials.
    """
    if request.method == 'POST':
        email    = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')
        user = authenticate(request, username=email, password=password)
        
        if user and (user.is_staff or user.is_superuser):
            login(request, user)
            try:
                role = user.profile.role
            except UserProfile.DoesNotExist:
                role = 'admin'
            role_redirects = {
                'mechanic':  'mechanic_dashboard',
                'inventory': 'inventory_dashboard',
                'inquiries': 'inquiries_dashboard',
            }
            return redirect(role_redirects.get(role, 'staff_dashboard'))
        elif user:
            _flash(request, 'error', 'Access Denied: This account exists but does not have staff privileges.')
        else:
            _flash(request, 'error', 'Invalid email or password. Please check your credentials.')
            
    return render(request, 'staff/login.html')


def logout_view(request):
    """Logs out any user (customer or staff) and redirects to login."""
    logout(request)
    _flash(request, 'info', 'You have been logged out successfully.')
    return redirect('login')


# ════════════════════════════════════════════════════════════
# 5. CUSTOMER DASHBOARD
# ════════════════════════════════════════════════════════════

@login_required
def user_profile(request):
    """
    Customer dashboard showing service history, orders, and quick actions.
    Displays personalized statistics and navigation options.
    """
    try:
        # Get user's bookings and orders with optimized queries
        bookings = Booking.objects.filter(user=request.user).order_by('-created_at')
        orders = Order.objects.filter(user=request.user).order_by('-created_at')

        # Get customer profile if exists
        customer_profile = UserProfile.objects.filter(user=request.user).first()

        # Calculate dashboard statistics efficiently
        total_bookings = bookings.count()
        total_orders = orders.count()

        # Calculate profile completion percentage
        profile_completion = sum([
            25 if request.user.first_name and request.user.last_name else 0,
            25 if request.user.email else 0,
            25 if customer_profile and customer_profile.phone_number and customer_profile.phone_number != '0000000000' else 0,
            25 if bookings.exists() or orders.exists() else 0
        ])

        # Calculate days as member
        member_days = (timezone.now().date() - request.user.date_joined.date()).days if request.user.date_joined else 0

        # Get recent activity for display
        recent_bookings = bookings[:5]
        recent_orders = orders[:5]

        # Handle POST requests
        if request.method == 'POST':
            if 'update_profile' in request.POST:
                try:
                    # Update user information
                    request.user.first_name = request.POST.get('first_name', '').strip()
                    request.user.last_name = request.POST.get('last_name', '').strip()
                    request.user.email = request.POST.get('email', '').strip()
                    request.user.save()
                    
                    # Update customer profile if exists
                    if customer_profile:
                        customer_profile.phone_number = request.POST.get('phone_number', '').strip()
                        customer_profile.save()
                    
                    messages.success(request, 'Your profile has been successfully updated!')
                    return redirect('user_profile')
                except Exception as e:
                    messages.error(request, f'Error updating profile: {str(e)}')
            
            elif 'change_password' in request.POST:
                password_form = PasswordChangeForm(user=request.user, data=request.POST)
                if password_form.is_valid():
                    password_form.save()
                    update_session_auth_hash(request, password_form.user)
                    messages.success(request, 'Your password has been successfully updated!')
                    return redirect('user_profile')
                else:
                    messages.error(request, 'Please correct the errors below.')
        else:
            password_form = PasswordChangeForm(user=request.user)

        # Get user role for template
        user_role = None
        if customer_profile:
            user_role = customer_profile.role
        elif request.user.is_staff:
            user_role = 'admin'  # Default for staff without profile

        context = {
            'bookings': bookings,
            'orders': orders,
            'customer_profile': customer_profile,
            'user_role': user_role,
            'total_bookings': total_bookings,
            'total_orders': total_orders,
            'profile_completion': profile_completion,
            'member_days': member_days,
            'recent_bookings': recent_bookings,
            'recent_orders': recent_orders,
            'password_form': password_form,
        }
        return render(request, 'profile.html', context)
        
    except Exception as e:
        # Log error and provide fallback context
        logger.error(f"Error in user_profile view: {e}")
        context = {
            'bookings': [],
            'orders': [],
            'customer_profile': None,
            'user_role': 'customer' if not request.user.is_staff else 'admin',
            'total_bookings': 0,
            'total_orders': 0,
            'profile_completion': 25,  # At least email is required
            'member_days': 0,
            'recent_bookings': [],
            'recent_orders': [],
            'error_message': 'Unable to load some dashboard data. Please try again later.'
        }
        return render(request, 'profile.html', context)





def password_reset_request(request):
    """
    Handle password reset requests for users who forgot their password.
    """
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        
        if not email:
            messages.error(request, 'Please enter your email address.')
            return render(request, 'password_reset.html')
        
        try:
            user = User.objects.get(email=email.lower())
            # Generate password reset token and send email
            from django.contrib.auth.tokens import default_token_generator
            token = default_token_generator.make_token(user)
            
            # Build reset URL
            current_site = getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000')
            reset_url = f"{current_site}/reset/{token}/{user.pk}/"
            
            # Send password reset email
            from django.core.mail import send_mail
            subject = 'Password Reset Request - Randini Garage'
            message = f'''
Hello {user.first_name or user.username},

We received a request to reset your password for your Randini Garage account.

Click the link below to reset your password:
{reset_url}

This link will expire in 24 hours for security reasons.

If you didn't request this password reset, please ignore this email or contact our support team.

Best regards,
The Randini Garage Team
            '''
            
            try:
                send_mail(
                    subject=subject,
                    message=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[email],
                    fail_silently=False,
                )
                messages.success(request, 'Password reset link has been sent to your email address.')
                logger.info(f"Password reset email sent to {email}")
            except Exception as e:
                logger.error(f"Failed to send password reset email to {email}: {e}")
                messages.error(request, 'Failed to send reset email. Please try again later.')
                
        except User.DoesNotExist:
            # Don't reveal if email exists or not for security
            messages.info(request, 'If your email is registered, you will receive reset instructions shortly.')
            logger.info(f"Password reset requested for non-existent email: {email}")
        
        except Exception as e:
            logger.error(f"Error in password reset request: {e}")
            messages.error(request, 'An error occurred. Please try again later.')
        
        return render(request, 'password_reset.html')
    
    return render(request, 'password_reset.html')


# ════════════════════════════════════════════════════════════
# 6. STAFF DASHBOARD
# ════════════════════════════════════════════════════════════

@staff_member_required(login_url='/staff/login/')
@role_required('admin')
def staff_dashboard(request):
    """
    Admin/full-access dashboard.
    Shows KPI cards, revenue trend chart, service-mix chart, and recent orders.
    """
    orders         = Order.objects.all()
    today          = timezone.now()
    seven_days_ago = today - timedelta(days=7)

    # Revenue trend: sum completed orders per day for the last 7 days
    daily_revenue = (
        Order.objects.filter(status='Completed', created_at__gte=seven_days_ago)
        .annotate(day=TruncDay('created_at'))
        .values('day').annotate(total=Sum('total_amount'))
        .order_by('day')
    )
    chart_labels = [e['day'].strftime('%a') for e in daily_revenue]
    chart_data   = [float(e['total']) for e in daily_revenue]

    # Service mix: count each booking service type
    service_counts = Booking.objects.values('service_type').annotate(count=Count('id'))
    service_labels = [s['service_type'].title() for s in service_counts]
    service_data   = [s['count'] for s in service_counts]

    context = {
        'total_sales':    orders.filter(status='Completed').aggregate(Sum('total_amount'))['total_amount__sum'] or 0,
        'orders_count':   orders.count(),
        'pending_count':  orders.filter(status='Pending').count(),
        'bookings_count': Booking.objects.count(),
        'inquiries_count': ContactMessage.objects.filter(is_read=False).count(),
        'customers_count': UserProfile.objects.filter(role='customer').count(),
        'staff_count':    User.objects.filter(is_staff=True).count(),
        'recent_orders':  orders.order_by('-created_at')[:5],
        'today':          today,
        'chart_labels':   chart_labels,
        'chart_data':     chart_data,
        'service_labels': service_labels,
        'service_data':   service_data,
        # Inventory statistics
        'parts_count':    SparePart.objects.count(),
        'total_stock':    SparePart.objects.aggregate(Sum('stock'))['stock__sum'] or 0,
        'low_stock_count': SparePart.objects.filter(stock__lte=5).count(),
        'inventory_value': SparePart.objects.aggregate(total=Sum(F('stock') * F('price')))['total'] or 0,
        'recent_parts':  SparePart.objects.order_by('-created_at')[:5],
    }
    return render(request, 'staff/dashboard.html', context)


@staff_member_required(login_url='/staff/login/')
@role_required('mechanic')
def mechanic_dashboard(request):
    """
    Lightweight dashboard for Mechanics — shows only their relevant stats.
    Also handles booking status updates and invoice sending.
    """
    if request.method == 'POST':
        booking = get_object_or_404(Booking, id=request.POST.get('booking_id'))
        if request.POST.get('price'):
            booking.price = Decimal(request.POST.get('price'))
        
        if 'send_invoice' in request.POST:
            # Send invoice email
            try:
                from .utils import send_service_invoice_email
                # Get any spare parts used in this booking (if applicable)
                spare_parts = None  # You can add logic to get spare parts if needed
                # Create a customer-like object from booking data
                customer_data = type('Customer', (), {
                    'name': booking.full_name,
                    'email': booking.email,
                    'phone': booking.phone,
                    'user': booking.user
                })()
                success = send_service_invoice_email(booking, customer_data, spare_parts)
                if success:
                    _flash(request, 'success', f'Invoice sent to {booking.email} for booking #{booking.id}.')
                else:
                    _flash(request, 'error', 'Failed to send invoice. Please try again.')
            except Exception as e:
                logger.error(f"Invoice sending error: {e}")
                _flash(request, 'error', 'Failed to send invoice. Please try again.')
        
        elif 'set_pending' in request.POST: 
            booking.status = 'Pending'
            _flash(request, 'success', f'Booking #{booking.id} set to Pending.')
        elif 'set_inprogress' in request.POST: 
            booking.status = 'In Progress'
            _flash(request, 'success', f'Booking #{booking.id} set to In Progress.')
        elif 'set_completed' in request.POST: 
            booking.status = 'Completed'
            # Automatically send invoice when booking is completed
            try:
                from .utils import send_service_invoice_email
                spare_parts = None  # You can add logic to get spare parts if needed
                # Create a customer-like object from booking data
                customer_data = type('Customer', (), {
                    'name': booking.full_name,
                    'email': booking.email,
                    'phone': booking.phone,
                    'user': booking.user
                })()
                success = send_service_invoice_email(booking, customer_data, spare_parts)
                if success:
                    _flash(request, 'success', f'Booking #{booking.id} completed and invoice sent to {booking.email}.')
                else:
                    _flash(request, 'success', f'Booking #{booking.id} completed. (Invoice sending failed)')
            except Exception as e:
                logger.error(f"Invoice sending error: {e}")
                _flash(request, 'success', f'Booking #{booking.id} completed. (Invoice sending failed)')
        
        elif 'delete_booking' in request.POST:
            booking.delete()
            _flash(request, 'success', 'Booking deleted.')
            return redirect('mechanic_dashboard')
        
        booking.save()
        if 'send_invoice' not in request.POST:  # Avoid double redirect
            return redirect('mechanic_dashboard')

    context = {
        'pending_bookings':    Booking.objects.filter(status='Pending').count(),
        'inprogress_bookings': Booking.objects.filter(status='In Progress').count(),
        'completed_today':     Booking.objects.filter(status='Completed', updated_at__date=timezone.now().date()).count(),
        'recent_bookings':     Booking.objects.order_by('-created_at')[:8],
    }
    return render(request, 'staff/mechanic_dashboard.html', context)


@staff_member_required(login_url='/staff/login/')
@role_required('inventory')
def inventory_dashboard(request):
    """Dashboard for Inventory Managers — stock overview and orders."""
    context = {
        'total_parts':     SparePart.objects.count(),
        'low_stock_count': SparePart.objects.filter(stock__lte=5).count(),
        'out_of_stock':    SparePart.objects.filter(stock=0).count(),
        'recent_parts':    SparePart.objects.order_by('-updated_at')[:8],
        'orders_count':    Order.objects.count(),
        'recent_orders':   Order.objects.order_by('-created_at')[:5],
    }
    return render(request, 'staff/inventory_dashboard.html', context)


@staff_member_required(login_url='/staff/login/')
@role_required('inquiries')
def inquiries_dashboard(request):
    """Dashboard for Customer Inquiries Officers — unread messages."""
    context = {
        'unread_count':  ContactMessage.objects.filter(is_read=False).count(),
        'total_messages': ContactMessage.objects.count(),
        'recent_messages': ContactMessage.objects.order_by('-created_at')[:8],
    }
    return render(request, 'staff/inquiries_dashboard.html', context)


# ════════════════════════════════════════════════════════════
# 6. STAFF — ORDERS
# ════════════════════════════════════════════════════════════

@staff_member_required(login_url='/staff/login/')
def staff_orders(request):
    """Lists all spare-part orders newest first."""
    orders = Order.objects.all().order_by('-created_at')
    return render(request, 'staff/orders.html', {'orders': orders})


@staff_member_required(login_url='/staff/login/')
def staff_order_detail(request, order_id):
    """
    Shows full detail of a single order including all spare-part line items.
    Staff can also mark Cash orders as complete from here.
    """
    order       = get_object_or_404(Order, id=order_id)
    order_items = OrderItem.objects.filter(order=order).select_related('product')
    return render(request, 'staff/order_detail.html', {
        'order': order, 'order_items': order_items
    })


@staff_member_required(login_url='/staff/login/')
def complete_order(request, order_id):
    """
    Marks an order as Completed and decrements stock for each part.
    Uses transaction.atomic() so either ALL stock changes succeed or NONE do.
    """
    order = get_object_or_404(Order, id=order_id)
    if request.method == 'POST':
        try:
            with transaction.atomic():
                for item in order.items.all():
                    part = item.product
                    if part.stock >= item.quantity:
                        part.stock -= item.quantity
                        part.save()
                    else:
                        _flash(request, 'error', f'Insufficient stock for {part.name} (only {part.stock} left).')
                        return redirect('staff_order_detail', order_id=order.id)
                order.status = 'Completed'
                order.save()
                _flash(request, 'success', f'Order #{order.id} marked as complete. Stock updated.')
        except Exception as e:
            _flash(request, 'error', f'Error completing order: {e}')
    return redirect('staff_order_detail', order_id=order.id)


# ════════════════════════════════════════════════════════════
# 7. STAFF — BOOKINGS
# ════════════════════════════════════════════════════════════

@staff_member_required(login_url='/staff/login/')
def staff_bookings(request):
    """
    Lists all service bookings. Staff can update status, set price,
    send invoices, and delete bookings via POST buttons in the table.
    """
    if request.method == 'POST':
        booking = get_object_or_404(Booking, id=request.POST.get('booking_id'))
        if request.POST.get('price'):
            booking.price = Decimal(request.POST.get('price'))
        
        if 'send_invoice' in request.POST:
            # Send invoice email
            try:
                from .utils import send_service_invoice_email
                # Get any spare parts used in this booking (if applicable)
                spare_parts = None  # You can add logic to get spare parts if needed
                # Create a customer-like object from booking data
                customer_data = type('Customer', (), {
                    'name': booking.full_name,
                    'email': booking.email,
                    'phone': booking.phone,
                    'user': booking.user
                })()
                success = send_service_invoice_email(booking, customer_data, spare_parts)
                if success:
                    _flash(request, 'success', f'Invoice sent to {booking.email} for booking #{booking.id}.')
                else:
                    _flash(request, 'error', 'Failed to send invoice. Please try again.')
            except Exception as e:
                logger.error(f"Invoice sending error: {e}")
                _flash(request, 'error', 'Failed to send invoice. Please try again.')
        
        elif 'set_pending' in request.POST: 
            booking.status = 'Pending'
            _flash(request, 'success', f'Booking #{booking.id} set to Pending.')
        elif 'set_inprogress' in request.POST: 
            booking.status = 'In Progress'
            _flash(request, 'success', f'Booking #{booking.id} set to In Progress.')
        elif 'set_completed' in request.POST: 
            booking.status = 'Completed'
            # Automatically send invoice when booking is completed
            try:
                from .utils import send_service_invoice_email
                spare_parts = None  # You can add logic to get spare parts if needed
                # Create a customer-like object from booking data
                customer_data = type('Customer', (), {
                    'name': booking.full_name,
                    'email': booking.email,
                    'phone': booking.phone,
                    'user': booking.user
                })()
                success = send_service_invoice_email(booking, customer_data, spare_parts)
                if success:
                    _flash(request, 'success', f'Booking #{booking.id} completed and invoice sent to {booking.email}.')
                else:
                    _flash(request, 'success', f'Booking #{booking.id} completed. (Invoice sending failed)')
            except Exception as e:
                logger.error(f"Invoice sending error: {e}")
                _flash(request, 'success', f'Booking #{booking.id} completed. (Invoice sending failed)')
        
        elif 'delete_booking' in request.POST:
            booking.delete()
            _flash(request, 'success', 'Booking deleted.')
            return redirect('staff_bookings')
        
        booking.save()
        if 'send_invoice' not in request.POST:  # Avoid double redirect
            return redirect('staff_bookings')

    return render(request, 'staff/bookings.html', {
        'bookings':      Booking.objects.all().order_by('-created_at'),
        'total_revenue': Booking.objects.filter(status='Completed').aggregate(Sum('price'))['price__sum'] or 0,
    })


@staff_member_required(login_url='/staff/login/')
def print_receipt(request, booking_id):
    """Print receipt for a specific booking with comprehensive data."""
    booking = get_object_or_404(Booking, id=booking_id)
    
    # Check if user has permission to view this booking
    if not request.user.is_superuser:
        try:
            user_role = request.user.userprofile.role
            # Only mechanics and admin can print receipts
            if user_role not in ['mechanic', 'admin']:
                return redirect('staff_login')
        except UserProfile.DoesNotExist:
            return redirect('staff_login')
    
    # Calculate comprehensive payment details
    service_price = float(booking.price)
    parts_cost = float(getattr(booking, 'parts_cost', 0) or 0)
    labor_cost = float(getattr(booking, 'labor_cost', 0) or 0)
    
    # Calculate tax (16% VAT on service + parts)
    tax_rate = 0.16
    taxable_amount = service_price + parts_cost
    tax_amount = round(taxable_amount * tax_rate, 2)
    
    # Calculate discount if applicable
    discount_amount = float(getattr(booking, 'discount_amount', 0) or 0)
    
    # Calculate total amount
    subtotal = service_price + parts_cost + labor_cost
    total_amount = subtotal + tax_amount - discount_amount
    
    # Get customer information
    customer_info = {
        'id': booking.user.customer.id if booking.user and hasattr(booking.user, 'customer') else None,
        'name': booking.full_name,
        'email': booking.email,
        'phone': booking.phone,
        'location': booking.location,
        'is_guest': booking.user is None or not hasattr(booking.user, 'customer')
    }
    
    # Get service details
    service_details = {
        'service_type': booking.get_service_type_display(),
        'vehicle_type': booking.get_vehicle_type_display(),
        'vehicle_make': getattr(booking, 'vehicle_make', ''),
        'vehicle_model': getattr(booking, 'vehicle_model', ''),
        'vehicle_year': getattr(booking, 'vehicle_year', ''),
        'license_plate': getattr(booking, 'license_plate', ''),
        'preferred_time': booking.preferred_time,
        'actual_start_time': getattr(booking, 'actual_start_time', None),
        'actual_end_time': getattr(booking, 'actual_end_time', None),
        'service_description': getattr(booking, 'service_description', ''),
        'parts_used': getattr(booking, 'parts_used', ''),
        'labor_hours': getattr(booking, 'labor_hours', 0),
        'status': booking.status
    }
    
    # Get payment information
    payment_info = {
        'payment_method': getattr(booking, 'payment_method', ''),
        'payment_date': getattr(booking, 'payment_date', None),
        'payment_status': getattr(booking, 'payment_status', 'Pending'),
        'mpesa_transaction_id': getattr(booking, 'mpesa_transaction_id', ''),
        'mpesa_phone': getattr(booking, 'mpesa_phone', ''),
        'mpesa_amount': getattr(booking, 'mpesa_amount', 0)
    }
    
    # Add calculated values to booking object for template access
    booking.total_amount = total_amount
    booking.tax_amount = tax_amount
    booking.parts_cost = parts_cost
    booking.labor_cost = labor_cost
    booking.discount_amount = discount_amount
    booking.subtotal = subtotal
    
    context = {
        'booking': booking,
        'customer_info': customer_info,
        'service_details': service_details,
        'payment_info': payment_info,
        'calculated_totals': {
            'service_price': service_price,
            'parts_cost': parts_cost,
            'labor_cost': labor_cost,
            'tax_amount': tax_amount,
            'discount_amount': discount_amount,
            'subtotal': subtotal,
            'total_amount': total_amount
        },
        'garage_info': {
            'name': 'Randini Auto Garage',
            'address': 'Bungoma, Kenya',
            'phone': '+254 711962088',
            'email': 'randinigarage@gmail.com',
            'vat_number': 'VAT123456789',
            'license_number': 'AUTO-GARAGE-2023'
        },
        'today': timezone.now()
    }
    return render(request, 'staff/print_receipt.html', context)


@staff_member_required(login_url='/staff/login/')
def print_order_receipt(request, order_id):
    """
    Print receipt for a specific order.
    """
    order = get_object_or_404(Order, id=order_id)

    # Check if user has permission
    if not request.user.is_superuser:
        try:
            user_role = request.user.userprofile.role
            if user_role not in ['mechanic', 'admin']:
                return redirect('staff_login')
        except UserProfile.DoesNotExist:
            return redirect('staff_login')

    context = {
        'order': order,
        'garage_info': {
            'name': 'Randini Auto Garage',
            'address': 'Bungoma, Kenya',
            'phone': '+254 711962088',
            'email': 'randinigarage@gmail.com'
        },
        'today': timezone.now()
    }
    return render(request, 'staff/order_receipt_print.html', context)


@staff_member_required(login_url='/staff/login/')
def print_booking_report(request):
    """Print booking report for mechanics."""
    if not request.user.is_superuser:
        try:
            user_role = request.user.userprofile.role
            if user_role not in ['mechanic', 'admin']:
                return redirect('staff_login')
        except UserProfile.DoesNotExist:
            return redirect('staff_login')
    
    # Get date range from request or default to today
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')
    
    bookings = Booking.objects.all()
    
    if from_date:
        bookings = bookings.filter(created_at__date__gte=from_date)
    if to_date:
        bookings = bookings.filter(created_at__date__lte=to_date)
    
    context = {
        'bookings': bookings.order_by('-created_at'),
        'from_date': from_date,
        'to_date': to_date,
        'total_bookings': bookings.count(),
        'total_revenue': sum(b.price for b in bookings if b.price),
        'garage_info': {
            'name': 'Randini Auto Garage',
            'address': 'Bungoma, Kenya',
            'phone': '+254 711962088',
            'email': 'randinigarage@gmail.com'
        }
    }
    return render(request, 'staff/print_booking_report.html', context)


@staff_member_required(login_url='/staff/login/')
def print_inventory_report(request):
    """Print inventory report for inventory managers."""
    if not request.user.is_superuser:
        try:
            user_role = request.user.userprofile.role
            if user_role not in ['inventory', 'admin']:
                return redirect('staff_login')
        except UserProfile.DoesNotExist:
            return redirect('staff_login')
    
    parts = SparePart.objects.all()
    low_stock_parts = parts.filter(stock__lte=5)
    out_of_stock_parts = parts.filter(stock=0)
    
    context = {
        'parts': parts.order_by('name'),
        'low_stock_parts': low_stock_parts,
        'out_of_stock_parts': out_of_stock_parts,
        'total_parts': parts.count(),
        'total_value': sum(p.price * p.stock for p in parts),
        'garage_info': {
            'name': 'Randini Auto Garage',
            'address': 'Bungoma, Kenya',
            'phone': '+254 711962088',
            'email': 'randinigarage@gmail.com'
        }
    }
    return render(request, 'staff/print_inventory_report.html', context)


@login_required(login_url='/login/')
def print_customer_report(request):
    """Print customer report for logged-in customers."""
    # Allow both customers and staff to view customer report
    # Staff can see all customers, customers can see their own info
    
    if request.user.is_staff:
        # Staff members can see all customers
        customers = UserProfile.objects.select_related('user').filter(user__is_staff=False)
        
        # Calculate statistics
        from datetime import datetime, timedelta
        thirty_days_ago = datetime.now() - timedelta(days=30)
        new_customers = customers.filter(user__date_joined__gte=thirty_days_ago)
        active_customers = customers.filter(user__is_active=True)
        inactive_customers = customers.filter(user__is_active=False)
        
        context = {
            'customers': customers.order_by('-user__date_joined'),
            'total_customers': customers.count(),
            'new_customers_count': new_customers.count(),
            'active_customers_count': active_customers.count(),
            'inactive_customers_count': inactive_customers.count(),
            'is_staff_view': True,
            'garage_info': {
                'name': 'Randini Auto Garage',
                'address': 'Bungoma, Kenya',
                'phone': '+254 711962088',
                'email': 'randinigarage@gmail.com'
            }
        }
    else:
        # Regular customers can only see their own information
        try:
            customer = UserProfile.objects.get(user=request.user)
            context = {
                'customers': [customer],
                'total_customers': 1,
                'new_customers_count': 1,
                'active_customers_count': 1 if customer.user.is_active else 0,
                'inactive_customers_count': 0 if customer.user.is_active else 1,
                'is_staff_view': False,
                'garage_info': {
                    'name': 'Randini Auto Garage',
                    'address': 'Bungoma, Kenya',
                    'phone': '+254 711962088',
                    'email': 'randinigarage@gmail.com'
                }
            }
        except Customer.DoesNotExist:
            # User doesn't have a customer profile
            context = {
                'customers': [],
                'total_customers': 0,
                'new_customers_count': 0,
                'active_customers_count': 0,
                'inactive_customers_count': 0,
                'is_staff_view': False,
                'garage_info': {
                    'name': 'Randini Auto Garage',
                    'address': 'Bungoma, Kenya',
                    'phone': '+254 711962088',
                    'email': 'randinigarage@gmail.com'
                }
            }
    
    return render(request, 'staff/print_customer_report.html', context)


# ════════════════════════════════════════════════════════════
# 8. STAFF — INVENTORY
# ════════════════════════════════════════════════════════════

@staff_member_required(login_url='/staff/login/')
def staff_inventory(request):
    """
    Lists all spare parts with search and low-stock indicators.
    """
    query = request.GET.get('q', '')
    parts = SparePart.objects.all()
    if query:
        parts = parts.filter(Q(name__icontains=query) | Q(description__icontains=query))
    return render(request, 'staff/inventory.html', {
        'parts':          parts.order_by('name'),
        'query':          query,
        'total_items':    SparePart.objects.count(),
        'low_stock_count': SparePart.objects.filter(stock__lte=5).count(),
    })


@staff_member_required(login_url='/staff/login/')
def add_sparepart(request):
    """Add a new spare part to the inventory."""
    form = SparePartForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        form.save()
        _flash(request, 'success', 'Spare part added successfully.')
        return redirect('staff_inventory')
    return render(request, 'staff/add_sparepart.html', {'form': form})


@staff_member_required(login_url='/staff/login/')
def edit_sparepart(request, pk):
    """Edit an existing spare part's details or price."""
    part = get_object_or_404(SparePart, pk=pk)
    form = SparePartForm(request.POST or None, request.FILES or None, instance=part)
    if form.is_valid():
        form.save()
        _flash(request, 'success', f'{part.name} updated successfully.')
        return redirect('staff_inventory')
    return render(request, 'staff/edit_sparepart.html', {'form': form, 'part': part})


@staff_member_required(login_url='/staff/login/')
def delete_sparepart(request, part_id):
    """Deletes a spare part (POST only for safety)."""
    if request.method == 'POST':
        part = get_object_or_404(SparePart, id=part_id)
        name = part.name
        part.delete()
        _flash(request, 'success', f'{name} removed from inventory.')
    return redirect('staff_inventory')


@staff_member_required(login_url='/staff/login/')
def stock_report(request):
    """Shows low-stock and out-of-stock parts, plus total inventory value."""
    low_stock  = SparePart.objects.filter(stock__lte=5).order_by('stock')
    all_parts  = SparePart.objects.all()
    total_value = all_parts.aggregate(total=Sum(F('price') * F('stock')))['total'] or 0
    return render(request, 'staff/stock_report.html', {
        'low_stock_parts':       low_stock,
        'total_inventory_value': total_value,
        'all_parts_count':       all_parts.count(),
        'low_stock_count':       low_stock.count(),
    })


# ════════════════════════════════════════════════════════════
# 9. STAFF — CUSTOMERS
# ════════════════════════════════════════════════════════════

@staff_member_required(login_url='/staff/login/')
def staff_customers(request):
    """
    Lists all registered customers with booking counts and total spend.
    Supports live search by name, email, or username.
    """
    query     = request.GET.get('q', '').strip()
    # Use Customer model to ensure we only get users with customer profiles
    customers = UserProfile.objects.select_related('user').filter(user__is_staff=False)

    if query:
        parts = query.split()
        if len(parts) > 1:
            name_filter = Q(user__first_name__icontains=parts[0]) & Q(user__last_name__icontains=parts[1])
        else:
            name_filter = Q(user__first_name__icontains=query) | Q(user__last_name__icontains=query)
        customers = customers.filter(name_filter | Q(user__email__icontains=query))

    customers = customers.annotate(
        num_bookings=Count('user__bookings'),
        total_spent=Sum('user__bookings__price')
    ).order_by('-num_bookings', 'user__first_name')

    return render(request, 'staff/customers.html', {
        'customers': customers, 'query': query,
        'total_customer_count': customers.count()
    })


@staff_member_required(login_url='/staff/login/')
def staff_customer_detail(request, customer_id):
    """Shows full profile + booking + order history for one customer."""
    customer_user = get_object_or_404(User, id=customer_id)
    bookings = Booking.objects.filter(user=customer_user).order_by('-created_at')
    orders   = Order.objects.filter(user=customer_user).order_by('-created_at')
    return render(request, 'staff/customers_detail.html', {
        'customer_user': customer_user, 'bookings': bookings, 'orders': orders
    })


@staff_member_required(login_url='/staff/login/')
def add_customer(request):
    """Add a new customer manually (staff only)."""
    if request.method == 'POST':
        # Get form data directly from POST
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip().lower()
        phone_number = request.POST.get('phone_number', '').strip()
        
        # Validate required fields
        if not first_name or not last_name or not email or not phone_number:
            _flash(request, 'error', 'All fields are required.')
            return render(request, 'staff/add_customer.html', {})
        
        # Check if email already exists
        if User.objects.filter(email=email).exists():
            _flash(request, 'error', 'A customer with this email already exists.')
            return render(request, 'staff/add_customer.html', {})
        
        try:
            # Create user account
            user = User.objects.create_user(
                username=email,
                email=email,
                password='Customer@123',  # Temporary password
                first_name=first_name,
                last_name=last_name
            )
            
            # Create customer profile
            customer = UserProfile.objects.create(
                user=user,
                phone_number=phone_number,
                role='customer'
            )
            
            # Send welcome email
            try:
                send_mail(
                    subject='Welcome to Randini Garage - Your Account Details',
                    message=f'''Dear {first_name} {last_name},

Welcome to Randini Auto Garage!

Your account has been created successfully. Here are your login details:

Email: {email}
Temporary Password: Customer@123

You can login at: http://127.0.0.1:8000/login/

Please change your password after logging in for security.

If you have any questions, feel free to contact us.

Best regards,
Randini Auto Garage Team''',
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[email],
                    fail_silently=True,
                )
            except Exception as e:
                # Log error but don't fail the customer creation
                print(f"Failed to send welcome email to {email}: {e}")
            
            _flash(request, 'success', f'Customer {user.get_full_name()} added successfully!')
            return redirect('staff_customers')
            
        except Exception as e:
            _flash(request, 'error', f'Error creating customer: {str(e)}')
            return render(request, 'staff/add_customer.html', {})
    else:
        return render(request, 'staff/add_customer.html', {})


@staff_member_required(login_url='/staff/login/')
def toggle_customer_status(request, customer_id):
    """Toggle customer active/inactive status (staff only)."""
    try:
        customer = UserProfile.objects.get(id=customer_id)
    except UserProfile.DoesNotExist:
        _flash(request, 'error', 'Customer not found or may have been already deleted.')
        return redirect('staff_customers')
    
    customer.user.is_active = not customer.user.is_active
    customer.user.save()
    
    status = "activated" if customer.user.is_active else "deactivated"
    _flash(request, 'success', f'Customer {customer.user.get_full_name()} {status} successfully!')
    return redirect('staff_customers')


@staff_member_required(login_url='/staff/login/')
def delete_customer(request, customer_id):
    """Deletes a customer account and all associated records (CASCADE)."""
    try:
        customer = User.objects.get(id=customer_id, is_staff=False)
    except User.DoesNotExist:
        _flash(request, 'error', 'Customer not found or may have been already deleted.')
        return redirect('staff_customers')
    
    if request.method == 'POST':
        name = customer.get_full_name() or customer.email
        customer.delete()
        _flash(request, 'success', f'Customer "{name}" deleted successfully.')
        return redirect('staff_customers')
    return redirect('staff_customers')


# ════════════════════════════════════════════════════════════
# 10. STAFF — ANALYTICS
# ════════════════════════════════════════════════════════════

@staff_member_required(login_url='/staff/login/')
def print_revenue_report(request):
    """
    Generates a printable revenue report for the last 7 days.
    Shows daily revenue trends and total revenue summary.
    """
    today = timezone.now().date()
    last_week = today - timedelta(days=6)

    # Get daily sales data for the last 7 days
    daily_sales = (
        Order.objects.filter(status='Completed', created_at__date__gte=last_week)
        .annotate(day=TruncDate('created_at'))
        .values('day').annotate(daily_total=Sum('total_amount'))
        .order_by('day')
    )
    
    # Prepare data for template
    sales_dict = {item['day']: item['daily_total'] for item in daily_sales}
    daily_data = []
    
    for i in range(7):
        day = last_week + timedelta(days=i)
        revenue = float(sales_dict.get(day, 0))
        daily_data.append({
            'day_name': day.strftime('%A'),
            'date': day.strftime('%B %d, %Y'),
            'revenue': revenue
        })
    
    # Calculate totals
    total_revenue = sum(item['revenue'] for item in daily_data)
    average_revenue = total_revenue / 7 if daily_data else 0
    
    # Calculate day counts for template
    days_with_revenue = len([item['revenue'] for item in daily_data if item['revenue'] > 0])
    days_with_no_revenue = len([item['revenue'] for item in daily_data if item['revenue'] == 0])
    
    return render(request, 'staff/print_revenue_report.html', {
        'report_date': timezone.now(),
        'daily_data': daily_data,
        'total_revenue': total_revenue,
        'average_revenue': average_revenue,
        'period_start': last_week,
        'period_end': today,
        'days_with_revenue': days_with_revenue,
        'days_with_no_revenue': days_with_no_revenue,
    })


@staff_member_required(login_url='/staff/login/')
def staff_analytics(request):
    """
    Business analytics dashboard.
    - Daily Sales Trend chart (last 7 days, completed orders only)
    - Monthly Sales Trend chart (last 30 days, completed orders only)
    - Custom date range reports
    - Most Popular Spare Parts doughnut chart
    - Total revenue and booking count summary
    """
    today = timezone.now().date()
    
    # Get period parameters
    period = request.GET.get('period', 'daily')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    # Validate and set date ranges
    if period == 'today':
        days_back = 1
        report_start = today
        report_end = today
        period_label = 'Today\'s Performance Overview'
    elif period == 'monthly':
        days_back = 30
        report_start = today - timedelta(days=29)
        report_end = today
        period_label = 'Monthly Performance Overview — Last 30 Days'
    elif period == 'custom' and start_date and end_date:
        try:
            report_start = datetime.strptime(start_date, '%Y-%m-%d').date()
            report_end = datetime.strptime(end_date, '%Y-%m-%d').date()
            # Ensure dates don't go beyond today
            if report_end > today:
                report_end = today
            if report_start > today:
                report_start = today - timedelta(days=30)
            days_back = (report_end - report_start).days
            period_label = f'Custom Report: {report_start.strftime("%B d, Y")} to {report_end.strftime("%B d, Y")}'
        except ValueError:
            # Fallback to daily if invalid dates
            period = 'daily'
            days_back = 7
            report_start = today - timedelta(days=6)
            report_end = today
            period_label = 'Daily Performance Overview — Last 7 Days'
    else:
        # Default to daily
        days_back = 7
        report_start = today - timedelta(days=6)
        report_end = today
        period_label = 'Daily Performance Overview — Last 7 Days'

    # Get sales data for the period
    sales_data = (
        Order.objects.filter(
            status='Completed',
            created_at__date__gte=report_start,
            created_at__date__lte=report_end
        )
        .annotate(day=TruncDate('created_at'))
        .values('day').annotate(daily_total=Sum('total_amount'))
        .order_by('day')
    )
    
    sales_dict = {item['day']: item['daily_total'] for item in sales_data}
    
    # Generate labels and revenue data for charts
    if days_back <= 7:
        # Daily view - show day names
        days_list = []
        revenue_list = []
        for i in range(days_back):
            day = report_start + timedelta(days=i)
            days_list.append(day.strftime('%A'))
            revenue_list.append(float(sales_dict.get(day, 0)))
    else:
        # Monthly/Custom view - show dates
        days_list = []
        revenue_list = []
        current_day = report_start
        while current_day <= report_end:
            days_list.append(current_day.strftime('%m/%d'))
            revenue_list.append(float(sales_dict.get(current_day, 0)))
            current_day += timedelta(days=1)

    # Get total revenue for the period
    total_revenue = (
        Order.objects.filter(
            status='Completed',
            created_at__date__gte=report_start,
            created_at__date__lte=report_end
        )
        .aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    )

    # Get parts data for the period
    parts_data = (
        OrderItem.objects
        .filter(order__status='Completed', order__created_at__date__gte=report_start, order__created_at__date__lte=report_end)
        .values('product__name')
        .annotate(total_qty=Sum('quantity'))
        .order_by('-total_qty')[:5]
    )

    return render(request, 'staff/analytics.html', {
        'period': period,
        'start_date': start_date or report_start.strftime('%Y-%m-%d'),
        'end_date': end_date or report_end.strftime('%Y-%m-%d'),
        'today': today.strftime('%Y-%m-%d'),
        'report_date': timezone.now(),
        'total_revenue': total_revenue,
        'total_bookings': Booking.objects.filter(created_at__date__gte=report_start, created_at__date__lte=report_end).count(),
        'days': days_list,
        'revenue_data': revenue_list,
        'part_labels': [p['product__name'] for p in parts_data],
        'part_counts': [p['total_qty'] for p in parts_data],
    })


# ════════════════════════════════════════════════════════════
# 11. STAFF — INQUIRIES
# ════════════════════════════════════════════════════════════

@staff_member_required(login_url='/staff/login/')
def staff_inquiries(request):
    """
    Lists all customer contact messages. Staff can:
    - Mark individual messages as read/unread
    - Mark all as read at once
    - Delete messages
    - Send email replies
    """
    inquiries = ContactMessage.objects.all().order_by('-created_at')
    if request.method == 'POST':
        msg_id = request.POST.get('msg_id')
        if 'mark_all_read' in request.POST:
            ContactMessage.objects.filter(is_read=False).update(is_read=True)
            _flash(request, 'success', 'All messages marked as read.')
        elif msg_id:
            msg = get_object_or_404(ContactMessage, id=msg_id)
            if 'mark_read' in request.POST:
                msg.is_read = True; msg.save()
                _flash(request, 'success', 'Message marked as read.')
            elif 'mark_unread' in request.POST:
                msg.is_read = False; msg.save()
                _flash(request, 'success', 'Message marked as unread.')
            elif 'delete' in request.POST:
                msg.delete()
                _flash(request, 'success', 'Message deleted.')
            elif 'send_reply' in request.POST:
                reply_subject = request.POST.get('reply_subject', '')
                reply_message = request.POST.get('reply_message', '')
                
                if reply_subject and reply_message:
                    try:
                        # Send email reply
                        send_mail(
                            subject=reply_subject,
                            message=reply_message,
                            from_email=settings.DEFAULT_FROM_EMAIL,
                            recipient_list=[msg.email],
                            fail_silently=False,
                        )
                        
                        # Mark message as read when replied
                        msg.is_read = True
                        msg.save()
                        
                        _flash(request, 'success', f'Reply sent to {msg.name} ({msg.email})')
                    except Exception as e:
                        _flash(request, 'error', f'Failed to send email: {str(e)}')
                else:
                    _flash(request, 'error', 'Please provide both subject and message.')
        return redirect('staff_inquiries')
    return render(request, 'staff/inquiries.html', {
        'inquiries':    inquiries,
        'unread_count': inquiries.filter(is_read=False).count(),
        'read_count':   inquiries.filter(is_read=True).count(),
        'total_messages': inquiries.count()
    })


# ════════════════════════════════════════════════════════════
# 12. STAFF — USER MANAGEMENT (Admin Only)
# ════════════════════════════════════════════════════════════
def manage_staff(request):
    """
    Admin-only page to view all staff accounts and their roles.
    Enhanced with status filtering dropdown for active/inactive staff.
    Only superusers can add, edit, or delete staff.
    """
    if not request.user.is_superuser:
        _flash(request, 'error', 'Access denied. Administrator privileges required.')
        return redirect('staff_dashboard')
    
    # Get status filter from GET parameter
    status_filter = request.GET.get('status', 'all')
    
    # Filter staff based on status
    if status_filter == 'active':
        staff_users = User.objects.filter(is_staff=True, is_active=True).order_by('first_name')
    elif status_filter == 'inactive':
        staff_users = User.objects.filter(is_staff=True, is_active=False).order_by('first_name')
    else:  # 'all' or any other value
        staff_users = User.objects.filter(is_staff=True).order_by('first_name')
    
    # Get counts for template
    total_staff = staff_users.count()
    active_staff = User.objects.filter(is_staff=True, is_active=True).count()
    inactive_staff = User.objects.filter(is_staff=True, is_active=False).count()
    
    return render(request, 'staff/manage_staff.html', {
        'staff_users': staff_users,
        'total_staff': total_staff,
        'active_staff': active_staff,
        'inactive_staff': inactive_staff,
        'current_filter': status_filter
    })


@staff_member_required(login_url='/staff/login/')
def add_staff(request):
    """
    Admin creates a new staff account with a chosen role using forms.
    The account is immediately active. Staff receive their credentials via email.
    """
    if not request.user.is_superuser:
        _flash(request, 'error', 'Access denied.')
        return redirect('staff_dashboard')

    if request.method == 'POST':
        form = StaffRegistrationForm(request.POST)
        if form.is_valid():
            first_name = form.cleaned_data['first_name']
            last_name = form.cleaned_data['last_name']
            email = form.cleaned_data['email'].lower()
            role = form.cleaned_data['role']
            password = form.cleaned_data['password']
            bio = form.cleaned_data.get('bio', '')
            is_active = form.cleaned_data.get('is_active', True)  # Default to True if not specified

            user = User.objects.create_user(
                username=email, email=email, password=password,
                first_name=first_name, last_name=last_name,
                is_staff=True, is_active=is_active
            )
            UserProfile.objects.create(user=user, role=role, bio=bio)

            # Send welcome email
            try:
                send_mail(
                    subject='Welcome to Randini Garage Staff Portal',
                    message=(
                        f"Hello {first_name},\n\n"
                        f"Your staff account has been created at Randini Auto Garage.\n\n"
                        f"Login URL: http://your-domain/staff/login/\n"
                        f"Email: {email}\n"
                        f"Password: {password}\n"
                        f"Role: {role.title()}\n"
                        f"Status: {'Active' if is_active else 'Inactive'}\n\n"
                        f"Please change your password after first login.\n\n"
                        f"— Admin, Randini Auto Garage"
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[email],
                )
                status_text = "activated" if is_active else "created as inactive"
                _flash(request, 'success', f'Staff account {status_text} for {first_name} {last_name}. Welcome email sent.')
            except Exception as e:
                logger.warning(f"Could not send staff welcome email: {e}")
                status_text = "activated" if is_active else "created as inactive"
                _flash(request, 'success', f'Staff account {status_text} for {first_name} {last_name}. (Email not sent)')
            
            return redirect('manage_staff')
    else:
        form = StaffRegistrationForm()

    return render(request, 'staff/add_staff.html', {'form': form})


@staff_member_required(login_url='/staff/login/')
def edit_staff(request, staff_id):
    """Admin edits a staff member's name, role, and bio."""
    if not request.user.is_superuser:
        _flash(request, 'error', 'Access denied.')
        return redirect('staff_dashboard')

    staff_user = get_object_or_404(User, id=staff_id, is_staff=True)
    try:
        profile = staff_user.profile
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=staff_user, role='mechanic')

    if request.method == 'POST':
        staff_user.first_name = request.POST.get('first_name', staff_user.first_name)
        staff_user.last_name  = request.POST.get('last_name', staff_user.last_name)
        staff_user.email      = request.POST.get('email', staff_user.email)
        staff_user.username   = staff_user.email
        staff_user.save()
        profile.role = request.POST.get('role', profile.role)
        profile.bio  = request.POST.get('bio', profile.bio)
        if request.FILES.get('photo'):
            profile.photo = request.FILES['photo']
        profile.save()
        _flash(request, 'success', f'{staff_user.get_full_name()} updated successfully.')
        return redirect('manage_staff')

    return render(request, 'staff/edit_staff.html', {
        'staff_user': staff_user, 'profile': profile
    })


@staff_member_required(login_url='/staff/login/')
def toggle_staff_status(request, staff_id):
    """Toggle staff active/inactive status (admin only)."""
    if not request.user.is_superuser:
        return redirect('staff_login')
    
    staff_user = get_object_or_404(User, id=staff_id, is_staff=True)
    staff_user.is_active = not staff_user.is_active
    staff_user.save()
    
    status = "activated" if staff_user.is_active else "deactivated"
    _flash(request, 'success', f'Staff member {staff_user.get_full_name()} {status} successfully!')
    return redirect('manage_staff')


@staff_member_required(login_url='/staff/login/')
def delete_staff(request, staff_id):
    """Admin deletes a staff account (cannot delete own account)."""
    if not request.user.is_superuser:
        _flash(request, 'error', 'Access denied.')
        return redirect('staff_dashboard')
    if request.method == 'POST':
        staff_user = get_object_or_404(User, id=staff_id, is_staff=True)
        if staff_user == request.user:
            _flash(request, 'error', 'You cannot delete your own account.')
            return redirect('manage_staff')
        name = staff_user.get_full_name()
        staff_user.delete()
        _flash(request, 'success', f'Staff account "{name}" deleted.')
    return redirect('manage_staff')


# ════════════════════════════════════════════════════════════
# 13. STAFF — SETTINGS
# ════════════════════════════════════════════════════════════

@staff_member_required(login_url='/staff/login/')
def staff_settings(request):
    """
    Staff can update their own first/last name, email, and change their password.
    """
    user = request.user
    if request.method == 'POST':
        user.first_name = request.POST.get('first_name', user.first_name)
        user.last_name  = request.POST.get('last_name', user.last_name)
        new_email       = request.POST.get('email', user.email).strip().lower()
        if new_email != user.email and User.objects.filter(email=new_email).exclude(pk=user.pk).exists():
            _flash(request, 'error', 'That email is already in use.')
        else:
            user.email    = new_email
            user.username = new_email
        user.save()

        # Optional password change
        new_pw = request.POST.get('new_password', '')
        confirm_pw = request.POST.get('confirm_password', '')
        if new_pw:
            if new_pw != confirm_pw:
                _flash(request, 'error', 'Passwords do not match.')
            elif len(new_pw) < 8:
                _flash(request, 'error', 'Password must be at least 8 characters.')
            else:
                user.set_password(new_pw)
                user.save()
                login(request, user)  # Re-authenticate after password change
                _flash(request, 'success', 'Password updated successfully.')
        else:
            _flash(request, 'success', 'Profile updated successfully.')
        return redirect('staff_settings')

    return render(request, 'staff/settings.html', {
        'user': user, 'garage_name': 'Randini Auto Garage'
    })


# ─────────────────────────────────────────────────────────────
# INVOICE MANAGEMENT
# ─────────────────────────────────────────────────────────────

@staff_member_required(login_url='/staff/login/')
def create_invoice(request, booking_id=None):
    """
    Create a new invoice or generate from existing booking.
    Supports both full invoice creation and quick invoice from booking.
    """
    booking = None
    if booking_id:
        booking = get_object_or_404(Booking, id=booking_id)
    
    if request.method == 'POST':
        # Use appropriate form based on whether we have a booking
        if booking:
            form = QuickInvoiceForm(request.POST)
        else:
            form = InvoiceForm(request.POST)
        
        if form.is_valid():
            try:
                # Generate invoice number if not provided
                invoice_number = form.cleaned_data.get('invoice_number')
                if not invoice_number:
                    invoice_number = f"INV-{timezone.now().year}-{timezone.now().strftime('%m')}-{Booking.objects.count() + 1:03d}"
                
                # Calculate totals
                totals = form.get_total_amount()
                
                # Prepare invoice data
                invoice_data = {
                    'invoice_number': invoice_number,
                    'issue_date': form.cleaned_data.get('issue_date'),
                    'due_date': form.cleaned_data.get('due_date'),
                     'payment_method': form.cleaned_data.get('payment_method', 'mpesa'),
                     'status': 'issued',
                    'labor_cost': form.cleaned_data.get('labor_cost'),
                    'parts_cost': form.cleaned_data.get('parts_cost'),
                    'tax_rate': form.cleaned_data.get('tax_rate'),
                    'subtotal': totals['subtotal'],
                    'tax_amount': totals['tax_amount'],
                    'total': totals['total'],
                    'notes': form.cleaned_data.get('notes', ''),
                    'spare_parts': form.get_spare_parts_list(),
                    'garage_info': {
                        'name': 'Randini Auto Garage',
                        'address': 'Bungoma, Kenya',
                        'phone': '+254 711962088',
                        'email': 'randinigarage@gmail.com'
                    }
                }
                
                # Add customer information
                if booking:
                    invoice_data.update({
                        'customer_name': booking.full_name,
                        'customer_email': booking.email,
                        'customer_phone': booking.phone,
                        'service_type': booking.get_service_type_display(),
                        'vehicle_type': booking.get_vehicle_type_display(),
                    })
                else:
                    invoice_data.update({
                        'customer_name': form.cleaned_data.get('customer_name'),
                        'customer_email': form.cleaned_data.get('customer_email'),
                        'customer_phone': form.cleaned_data.get('customer_phone'),
                        'customer_address': form.cleaned_data.get('customer_address'),
                        'service_type': form.cleaned_data.get('service_type'),
                        'vehicle_type': form.cleaned_data.get('vehicle_type'),
                        'vehicle_make': form.cleaned_data.get('vehicle_make'),
                        'vehicle_model': form.cleaned_data.get('vehicle_model'),
                        'vehicle_registration': form.cleaned_data.get('vehicle_registration'),
                    })
                
                # Handle different actions
                action = request.POST.get('action')
                if action == 'save_draft':
                    # Save as draft - show preview with success message
                    from django.contrib import messages
                    messages.success(request, 'Invoice created successfully. You can now send it to the customer.')
                    return render(request, 'staff/invoice_preview.html', {
                        'invoice': invoice_data,
                        'booking': booking
                    })

                elif action == 'send_invoice':
                    # Send invoice via email
                    try:
                        from django.core.mail import send_mail
                        from django.template.loader import render_to_string
                        from django.conf import settings

                        # Render HTML invoice
                        html_content = render_to_string('staff/invoice_print.html', {
                            'invoice': invoice_data,
                            'booking': booking
                        })
                        text_content = f'''
                        Dear {invoice_data['customer_name']},

                        Your invoice {invoice_number} has been generated.

                        Invoice Number: {invoice_number}
                        Issue Date: {invoice_data['issue_date']}
                        Due Date: {invoice_data['due_date']}

                        Subtotal: KSh {invoice_data['subtotal']:.2f}
                        Tax Amount: KSh {invoice_data['tax_amount']:.2f}
                        Total Amount: KSh {invoice_data['total']:.2f}

                        Thank you for choosing Randini Garage!

                        Best regards,
                        Randini Garage Team
                        Bungoma, Kenya
                        +254 711962088
                        '''

                        send_mail(
                            subject=f'Invoice {invoice_number} - Randini Garage',
                            message=text_content,
                            from_email=settings.DEFAULT_FROM_EMAIL,
                            recipient_list=[invoice_data['customer_email']],
                            html_message=html_content,
                            fail_silently=True,
                        )

                        _flash(request, 'success', f'Invoice {invoice_number} sent to {invoice_data["customer_email"]}.')
                        return redirect('staff_bookings')
                        
                    except Exception as e:
                        logger.error(f"Invoice sending error: {e}")
                        _flash(request, 'error', f'Failed to send invoice: {str(e)}')
                        logger.error(f"Invoice sending error: {e}")
                        _flash(request, 'error', 'Failed to send invoice. Please try again.')
                
                elif 'print_invoice' in request.POST:
                    # Generate printable invoice
                    return render(request, 'staff/invoice_print.html', {
                        'invoice': invoice_data,
                        'booking': booking
                    })
                
                # Default: show preview
                return render(request, 'staff/invoice_preview.html', {
                    'invoice': invoice_data,
                    'booking': booking
                })
                
            except Exception as e:
                logger.error(f"Invoice creation error: {e}")
                _flash(request, 'error', f'Error creating invoice: {str(e)}')
    
    else:
        # Initialize form for GET request
        if booking:
            # Pre-fill quick invoice form with booking data
            # Calculate service price if not already set
            if booking.price == 0.00:
                booking.price = booking.calculate_service_price()
                booking.save()
            
            form = QuickInvoiceForm(initial={
                'labor_cost': booking.price or 0,
                'tax_rate': 16.0,
                'due_date': timezone.now().date() + timezone.timedelta(days=14),
                'payment_method': 'mpesa'
            })
        else:
            # Empty full invoice form
            form = InvoiceForm()
    
    return render(request, 'staff/create_invoice_simple.html', {
        'form': form,
        'booking': booking
    })


@staff_member_required(login_url='/staff/login/')
def invoice_preview(request, invoice_id):
    """
    Preview an existing invoice.
    """
    pass


# ─────────────────────────────────────────────────────────────
# SERVICE PRICING MANAGEMENT
# ─────────────────────────────────────────────────────────────

@staff_member_required(login_url='/staff/login/')
def service_prices(request):
    """
    Display and manage service pricing.
    """
    services = Service.objects.all().order_by('service_type', 'vehicle_type')
    
    context = {
        'services': services,
        'total_services': services.count(),
        'active_services': services.filter(is_active=True).count(),
    }
    
    return render(request, 'staff/service_prices.html', context)


@staff_member_required(login_url='/staff/login/')
def service_price_api(request, price_id=None):
    """
    API endpoint for service price CRUD operations.
    """
    if request.method == 'GET' and price_id:
        # Get single service price
        try:
            service = Service.objects.get(id=price_id)
            return JsonResponse({
                'id': service.id,
                'service_type': service.service_type,
                'vehicle_type': service.vehicle_type,
                'base_price': float(service.base_price),
                'description': service.description,
                'is_active': service.is_active,
                'created_at': service.created_at.isoformat(),
                'updated_at': service.updated_at.isoformat(),
            })
        except Service.DoesNotExist:
            return JsonResponse({'error': 'Service price not found'}, status=404)
    
    elif request.method == 'POST':
        # Create new service price
        try:
            data = json.loads(request.body)
            
            service = Service.objects.create(
                service_type=data['service_type'],
                vehicle_type=data['vehicle_type'],
                base_price=data['base_price'],
                description=data.get('description', ''),
                is_active=data.get('is_active', True),
            )
            
            return JsonResponse({
                'success': True,
                'id': service.id,
                'message': 'Service price created successfully'
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    elif request.method == 'PATCH' and price_id:
        # Update service price
        try:
            service = Service.objects.get(id=price_id)
            data = json.loads(request.body)
            
            if 'service_type' in data:
                service.service_type = data['service_type']
            if 'vehicle_type' in data:
                service.vehicle_type = data['vehicle_type']
            if 'base_price' in data:
                service.base_price = data['base_price']
            if 'description' in data:
                service.description = data['description']
            if 'is_active' in data:
                service.is_active = data['is_active']
            
            service.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Service price updated successfully'
            })
            
        except Service.DoesNotExist:
            return JsonResponse({'error': 'Service price not found'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    elif request.method == 'DELETE' and price_id:
        # Delete service price
        try:
            service = Service.objects.get(id=price_id)
            service.delete()
            return JsonResponse({
                'success': True,
                'message': 'Service price deleted successfully'
            })
        except Service.DoesNotExist:
            return JsonResponse({'error': 'Service price not found'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@staff_member_required(login_url='/staff/login/')
def invoice_list(request):
    """
    List all invoices.
    """
    # This would typically fetch from a database Invoice model
    # For now, we'll redirect to bookings
    return redirect('staff_bookings')


# ════════════════════════════════════════════════════════════
# 8. ADMIN PASSWORD MANAGEMENT (Change any user's password)
# ════════════════════════════════════════════════════════════

@staff_member_required(login_url='/staff/login/')
@role_required('admin')
def admin_change_user_password(request, user_id=None):
    """
    Admin view to change any user's password.
    Superusers and staff with admin role can change passwords of other users.
    Renders the profile.html template with admin password management section.
    
    Args:
        request: HTTP request
        user_id: Optional user ID to pre-select a specific user
        
    Returns:
        Rendered profile.html with admin password change context
    """
    from django.contrib.auth.forms import SetPasswordForm
    from django.contrib.auth.forms import PasswordChangeForm
    
    # Get current user's profile data for the profile page
    user = request.user
    bookings = Booking.objects.filter(user=user).order_by('-created_at')
    orders = Order.objects.filter(user=user).order_by('-created_at')
    
    # Get customer profile if exists
    customer_profile = None
    try:
        customer_profile = UserProfile.objects.get(user=user)
    except UserProfile.DoesNotExist:
        pass
    
    # Calculate stats
    total_bookings = bookings.count()
    total_orders = orders.count()
    
    # Calculate profile completion
    profile_completion = 0
    if user.first_name and user.last_name:
        profile_completion += 25
    if user.email:
        profile_completion += 25
    if customer_profile and customer_profile.phone_number and customer_profile.phone_number != '0000000000':
        profile_completion += 25
    if bookings.exists() or orders.exists():
        profile_completion += 25
    
    # Member days
    member_days = (timezone.now().date() - user.date_joined.date()).days if user.date_joined else 0
    
    # Get all users for admin dropdown (excluding self)
    all_users = User.objects.exclude(id=user.id).order_by('first_name', 'last_name', 'email')
    
    # Admin password change variables
    admin_selected_user = None
    password_form = PasswordChangeForm(user)
    
    # Handle user selection
    if user_id:
        try:
            admin_selected_user = User.objects.get(id=user_id)
            if admin_selected_user == user:
                messages.error(request, "You cannot change your own password here. Use the sidebar form instead.")
                return redirect('admin_change_user_password')
        except User.DoesNotExist:
            messages.error(request, "User not found.")
            return redirect('admin_change_user_password')
    
    # Handle POST request
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'select_user':
            selected_user_id = request.POST.get('user_id')
            if selected_user_id:
                return redirect('admin_change_user_password_with_id', user_id=selected_user_id)
                
        elif action == 'change_password':
            selected_user_id = request.POST.get('user_id')
            try:
                admin_selected_user = User.objects.get(id=selected_user_id)
                set_password_form = SetPasswordForm(admin_selected_user, request.POST)
                
                if set_password_form.is_valid():
                    set_password_form.save()
                    messages.success(
                        request, 
                        f"Password successfully changed for {admin_selected_user.get_full_name() or admin_selected_user.email}"
                    )
                    logger.info(f"Admin {user.email} changed password for user {admin_selected_user.email}")
                    return redirect('admin_change_user_password')
                else:
                    # Keep selected user and show errors
                    pass
                    
            except User.DoesNotExist:
                messages.error(request, "User not found.")
                return redirect('admin_change_user_password')
    
    context = {
        'user': user,
        'bookings': bookings,
        'orders': orders,
        'customer_profile': customer_profile,
        'total_bookings': total_bookings,
        'total_orders': total_orders,
        'profile_completion': profile_completion,
        'member_days': member_days,
        'recent_bookings': bookings[:5],
        'recent_orders': orders[:5],
        'password_form': password_form,
        # Admin-specific context
        'all_users': all_users,
        'admin_selected_user': admin_selected_user,
    }
    
    return render(request, 'profile.html', context)
