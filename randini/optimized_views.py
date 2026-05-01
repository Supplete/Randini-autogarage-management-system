"""
Optimized views.py with consolidated UserProfile model
Key changes:
- Customer, StaffProfile, OTPVerification → UserProfile
- Updated role checking logic
- Simplified user profile management
"""

# Standard Python library imports
import json
import logging
import random
import string
from decimal import Decimal
from datetime import timedelta

# Django core imports
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.forms import PasswordChangeForm
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import IntegrityError
from django.db.models import Sum, Count, F
from django.db.models.functions import TruncDay

# Import custom forms
from .forms import InvoiceForm, QuickInvoiceForm

# Import optimized models
from .optimized_models import UserProfile, SparePart, ContactMessage, Order, Booking

User = get_user_model()

# ─────────────────────────────────────────────────────────────
# ROLE-BASED ACCESS CONTROL DECORATORS (Updated)
# ─────────────────────────────────────────────────────────────

def role_required(*roles):
    """Decorator to require specific staff roles for view access.
    
    Updated to use UserProfile instead of StaffProfile
    """
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('staff_login')
            
            if not (request.user.is_staff or request.user.is_superuser):
                return redirect('staff_login')
            
            # Get user's role from UserProfile
            try:
                user_role = request.user.profile.role
            except UserProfile.DoesNotExist:
                user_role = 'admin'  # Default for superusers without profile
            
            if user_role not in roles and not request.user.is_superuser:
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
    """Check if user is a mechanic."""
    try:
        return user.profile.role == 'mechanic'
    except UserProfile.DoesNotExist:
        return False

def is_inventory_manager(user):
    """Check if user is an inventory manager."""
    try:
        return user.profile.role == 'inventory'
    except UserProfile.DoesNotExist:
        return False

def is_inquiries_officer(user):
    """Check if user is an inquiries officer."""
    try:
        return user.profile.role == 'inquiries'
    except UserProfile.DoesNotExist:
        return False

def is_admin(user):
    """Check if user is admin."""
    try:
        return user.profile.role == 'admin'
    except UserProfile.DoesNotExist:
        return False

# ─────────────────────────────────────────────────────────────
# AUTHENTICATION VIEWS (Updated for UserProfile)
# ─────────────────────────────────────────────────────────────

def register_view(request):
    """User registration with OTP verification."""
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        phone_number = request.POST.get('phone_number')
        
        if password != confirm_password:
            messages.error(request, "Passwords do not match!")
            return render(request, 'register.html')
        
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists!")
            return render(request, 'register.html')
        
        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already registered!")
            return render(request, 'register.html')
        
        # Create user
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            is_active=False  # Will be activated after OTP verification
        )
        
        # Create user profile with OTP
        profile = UserProfile.objects.create(
            user=user,
            phone_number=phone_number,
            role='customer'
        )
        profile.generate_otp()
        
        # Send OTP email (you'll need to implement email sending)
        # send_otp_email(email, profile.otp)
        
        messages.success(request, "Registration successful! Please check your email for OTP.")
        return redirect('otp_verify', email=email)
    
    return render(request, 'register.html')

def otp_verify_view(request, email):
    """OTP verification for user activation."""
    if request.method == 'POST':
        otp = request.POST.get('otp')
        
        try:
            user = User.objects.get(email=email)
            profile = user.profile
            
            if profile.otp == otp and not profile.otp_is_used and not profile.is_expired_otp():
                # Activate user and mark OTP as used
                user.is_active = True
                user.save()
                profile.otp_is_used = True
                profile.save()
                
                messages.success(request, "Email verified successfully! You can now login.")
                return redirect('login')
            else:
                messages.error(request, "Invalid or expired OTP!")
        except User.DoesNotExist:
            messages.error(request, "User not found!")
    
    return render(request, 'otp_verify.html', {'email': email})

# ─────────────────────────────────────────────────────────────
# CUSTOMER PROFILE VIEWS (Updated)
# ─────────────────────────────────────────────────────────────

@login_required
def customer_profile(request):
    """Customer profile view."""
    try:
        profile = request.user.profile
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(
            user=request.user,
            phone_number='0000000000',
            role='customer'
        )
    
    if request.method == 'POST':
        profile.phone_number = request.POST.get('phone_number')
        profile.save()
        
        messages.success(request, "Profile updated successfully!")
        return redirect('customer_profile')
    
    context = {
        'profile': profile,
        'total_bookings': profile.total_bookings(),
        'total_orders': profile.total_orders(),
    }
    return render(request, 'customer/profile.html', context)

# ─────────────────────────────────────────────────────────────
# STAFF DASHBOARD VIEWS (Updated)
# ─────────────────────────────────────────────────────────────

@role_required('admin', 'mechanic', 'inventory', 'inquiries')
def staff_dashboard(request):
    """Main staff dashboard with role-based content."""
    try:
        profile = request.user.profile
        user_role = profile.role
    except UserProfile.DoesNotExist:
        user_role = 'admin'
    
    # Get statistics based on role
    context = {
        'user_role': user_role,
        'total_bookings': Booking.objects.count(),
        'pending_bookings': Booking.objects.filter(status='Pending').count(),
        'total_orders': Order.objects.count(),
        'pending_orders': Order.objects.filter(status='Pending').count(),
        'total_spare_parts': SparePart.objects.count(),
        'low_stock_parts': SparePart.objects.filter(stock__lte=5).count(),
        'unread_messages': ContactMessage.objects.filter(is_read=False).count(),
    }
    
    return render(request, f'staff/{user_role}_dashboard.html', context)

@role_required('admin')
def staff_user_management(request):
    """Admin user management - create/edit staff accounts."""
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        role = request.POST.get('role')
        phone_number = request.POST.get('phone_number')
        
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists!")
            return redirect('staff_user_management')
        
        # Create user
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            is_staff=True
        )
        
        # Create staff profile
        UserProfile.objects.create(
            user=user,
            phone_number=phone_number,
            role=role
        )
        
        messages.success(request, f"Staff account created for {username}!")
        return redirect('staff_user_management')
    
    # Get all staff profiles
    staff_profiles = UserProfile.objects.filter(role__in=['mechanic', 'inventory', 'inquiries', 'admin'])
    
    context = {
        'staff_profiles': staff_profiles,
        'role_choices': UserProfile.ROLE_CHOICES[1:],  # Exclude 'customer'
    }
    return render(request, 'staff/user_management.html', context)

@role_required('admin')
def edit_staff_user(request, profile_id):
    """Edit existing staff user."""
    profile = get_object_or_404(UserProfile, id=profile_id)
    
    if request.method == 'POST':
        profile.role = request.POST.get('role')
        profile.phone_number = request.POST.get('phone_number')
        profile.bio = request.POST.get('bio')
        
        profile.save()
        
        # Update user staff status
        profile.user.is_staff = profile.role != 'customer'
        profile.user.save()
        
        messages.success(request, f"Updated {profile.user.username}'s profile!")
        return redirect('staff_user_management')
    
    context = {'profile': profile}
    return render(request, 'staff/edit_staff_user.html', context)

# ─────────────────────────────────────────────────────────────
# CUSTOMER MANAGEMENT VIEWS (Updated)
# ─────────────────────────────────────────────────────────────

@role_required('admin', 'inquiries')
def staff_customers(request):
    """List all customers."""
    customers = UserProfile.objects.filter(role='customer')
    
    context = {
        'customers': customers,
    }
    return render(request, 'staff/customers.html', context)

@role_required('admin', 'inquiries')
def staff_customer_detail(request, profile_id):
    """View customer details."""
    customer = get_object_or_404(UserProfile, id=profile_id, role='customer')
    
    context = {
        'customer': customer,
        'bookings': Booking.objects.filter(user=customer.user),
        'orders': Order.objects.filter(user=customer.user),
    }
    return render(request, 'staff/customer_detail.html', context)

# ─────────────────────────────────────────────────────────────
# STAFF SETTINGS VIEW (Updated)
# ─────────────────────────────────────────────────────────────

@role_required('admin', 'mechanic', 'inventory', 'inquiries')
def staff_settings(request):
    """Staff personal settings page."""
    try:
        profile = request.user.profile
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(
            user=request.user,
            role='admin'  # Default role
        )
    
    if request.method == 'POST':
        profile.phone_number = request.POST.get('phone_number')
        profile.bio = request.POST.get('bio')
        
        profile.save()
        
        # Handle password change
        password_form = PasswordChangeForm(request.user, request.POST)
        if password_form.is_valid():
            password_form.save()
            update_session_auth_hash(request, request.user)
            messages.success(request, "Settings updated successfully!")
        else:
            messages.error(request, "Error updating password!")
        
        return redirect('staff_settings')
    
    password_form = PasswordChangeForm(request.user)
    
    context = {
        'profile': profile,
        'password_form': password_form,
    }
    return render(request, 'staff/settings.html', context)

# Note: Other views (bookings, orders, inventory, etc.) remain largely the same
# but would need similar updates for user profile references
