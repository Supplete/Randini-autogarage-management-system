"""
urls.py — Randini Auto Garage URL Configuration
=================================================
Maps URL paths to view functions.

Sections:
  1. Public & Customer routes  — home, about, services, contact, booking, profile
  2. Authentication routes     — register, OTP verify, login, logout, password reset
  3. Shopping & Payment routes — spare parts, cart, checkout, M-Pesa callback
  4. Staff Administration      — dashboard, bookings, inventory, orders, analytics, etc.
"""

from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [

    # ─────────────────────────────────────────────────────
    # 1. PUBLIC & CUSTOMER ROUTES
    # ─────────────────────────────────────────────────────
    path('',            views.home,         name='home'),
    path('about/',      views.about,        name='about'),
    path('services/',   views.services,     name='services'),
    path('contact/',    views.contact,      name='contact'),
    path('booking/',    views.booking_view, name='booking'),
    path('my-account/', views.user_profile, name='user_profile'),
    path('customer-report/', views.print_customer_report, name='customer_report'),

    # ─────────────────────────────────────────────────────
    # 2. AUTHENTICATION ROUTES
    # ─────────────────────────────────────────────────────
    path('register/',    views.register,      name='register'),
    path('verify-otp/',  views.verify_otp,    name='verify_otp'),
    path('confirm-registration/', views.confirm_registration, name='confirm_registration'),
    path('resend-otp/',  views.resend_otp,    name='resend_otp'),
    path('login/',       views.login_view,    name='login'),
    path('logout/',      views.logout_view,   name='logout'),

    # Password Reset Flow (Custom view)
    path('password-reset/', views.password_reset_request, name='password_reset_request'),

    path('password-reset-done/', auth_views.PasswordResetDoneView.as_view(
        template_name='password_reset_done.html'
    ), name='password_reset_done'),

    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='password_reset_confirm.html'
    ), name='password_reset_confirm'),

    path('password-reset-complete/', auth_views.PasswordResetCompleteView.as_view(
        template_name='password_reset_complete.html'
    ), name='password_reset_complete'),

    # ─────────────────────────────────────────────────────
    # 3. SHOPPING & PAYMENT ROUTES
    # ─────────────────────────────────────────────────────
    path('spareparts/',                    views.spareparts,       name='spareparts'),
    path('cart/',                          views.cart,             name='cart'),
    path('cart/add/<int:part_id>/',        views.add_to_cart,      name='add_to_cart'),
    path('cart/increase/<int:part_id>/',   views.increase_cart,    name='increase_cart'),
    path('cart/decrease/<int:part_id>/',   views.decrease_cart,    name='decrease_cart'),
    path('cart/remove/<int:part_id>/',     views.remove_from_cart, name='remove_from_cart'),
    path('checkout/',                      views.checkout,         name='checkout'),
    path('order-success/<int:order_id>/',  views.order_success,    name='order_success'),
    path('mpesa-callback/',                views.mpesa_callback,   name='mpesa_callback'),

    # ─────────────────────────────────────────────────────
    # 4. STAFF ADMINISTRATION ROUTES
    # ─────────────────────────────────────────────────────

    # Login & Dashboard
    path('staff/login/',     views.staff_login,           name='staff_login'),
    path('staff/dashboard/', views.staff_dashboard,       name='staff_dashboard'),
    path('staff/bookings/',  views.mechanic_dashboard,    name='staff_bookings'),
    path('staff/inventory/', views.inventory_dashboard,   name='staff_inventory'),
    path('staff/inquiries/', views.inquiries_dashboard,   name='staff_inquiries'),
    
    # Role-specific Dashboards
    path('staff/mechanic-dashboard/', views.mechanic_dashboard, name='mechanic_dashboard'),
    path('staff/inventory-dashboard/', views.inventory_dashboard, name='inventory_dashboard'),
    path('staff/inquiries-dashboard/', views.inquiries_dashboard, name='inquiries_dashboard'),
    
    # Additional Booking Management (if needed)
    path('staff/bookings/manage/',              views.staff_bookings,    name='staff_bookings_manage'),

    # Orders
    path('staff/orders/',                                views.staff_orders,      name='staff_orders'),
    path('staff/order/<int:order_id>/',                  views.staff_order_detail, name='staff_order_detail'),
    path('staff/orders/<int:order_id>/complete/',        views.complete_order,     name='complete_order'),

    # Inventory Management
    path('staff/inventory/add/',                   views.add_sparepart,    name='add_sparepart'),
    path('staff/inventory/edit/<int:pk>/',         views.edit_sparepart,   name='edit_sparepart'),
    path('staff/inventory/delete/<int:part_id>/', views.delete_sparepart,  name='delete_sparepart'),
    path('staff/inventory/stock-report/',          views.stock_report,     name='stock_report'),

    # Customers
    path('staff/customers/',                        views.staff_customers,      name='staff_customers'),
    path('staff/customer/<int:customer_id>/',       views.staff_customer_detail, name='customer_detail'),
    path('staff/customer/add/',                    views.add_customer,         name='add_customer'),
    path('staff/customer/toggle/<int:customer_id>/', views.toggle_customer_status, name='toggle_customer_status'),
    path('staff/customer/delete/<int:customer_id>/', views.delete_customer,     name='delete_customer'),

    # Inquiries
    path('staff/inquiries/manage/', views.staff_inquiries, name='staff_inquiries_manage'),

    # Analytics
    path('staff/analytics/', views.staff_analytics, name='staff_analytics'),

    # User / Staff Management (Admin Only)
    path('staff/manage-staff/',                   views.manage_staff, name='manage_staff'),
    path('staff/add-staff/',                      views.add_staff, name='add_staff'),
    path('staff/edit-staff/<int:staff_id>/',      views.edit_staff, name='edit_staff'),
    path('staff/toggle-staff/<int:staff_id>/',    views.toggle_staff_status, name='toggle_staff_status'),
    path('staff/delete-staff/<int:staff_id>/',    views.delete_staff, name='delete_staff'),

    # Settings
    path('staff/settings/', views.staff_settings, name='staff_settings'),
    
    # Admin Password Management
    path('staff/admin/change-password/', views.admin_change_user_password, name='admin_change_user_password'),
    path('staff/admin/change-password/<int:user_id>/', views.admin_change_user_password, name='admin_change_user_password_with_id'),
    
    # Invoice Management
    path('staff/invoice/create/', views.create_invoice, name='create_invoice'),
    path('staff/invoice/create/<int:booking_id>/', views.create_invoice, name='create_invoice_from_booking'),
    path('staff/invoice/preview/<int:invoice_id>/', views.invoice_preview, name='invoice_preview'),
    path('staff/invoice/list/', views.invoice_list, name='staff_invoice_list'),
    
    # Service Pricing Management
    path('staff/service-prices/', views.service_prices, name='service_prices'),
    path('staff/api/service-price/', views.service_price_api, name='service_price_api'),
    path('staff/api/service-price/<int:price_id>/', views.service_price_api, name='service_price_api_detail'),
    
    # Printing Reports
    path('staff/print/receipt/<int:booking_id>/', views.print_receipt, name='print_receipt'),
    path('staff/print/order-receipt/<int:order_id>/', views.print_order_receipt, name='print_order_receipt'),
    path('staff/print/booking-report/', views.print_booking_report, name='print_booking_report'),
    path('staff/print/inventory-report/', views.print_inventory_report, name='print_inventory_report'),
    path('staff/print/revenue-report/', views.print_revenue_report, name='print_revenue_report'),
]

# Serve uploaded media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
