from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # ============================================================
    # 1. PUBLIC & CUSTOMER ROUTES
    # ============================================================
    path('', views.register_view, name='register'),
    path('home/', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('services/', views.services, name='services'),
    path('contact/', views.contact, name='contact'),
    path('booking/', views.booking_view, name='booking'),
    path('my-account/', views.user_profile, name='user_profile'),

    # ============================================================
    # 2. AUTHENTICATION ROUTES
    # ============================================================
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Password Reset Flow
    path('password-reset/', auth_views.PasswordResetView.as_view(
        template_name='password_reset.html',
        email_template_name='password_reset_email.html',
        subject_template_name='password_reset_subject.txt'
    ), name='password_reset'),
    
    path('password-reset-done/', auth_views.PasswordResetDoneView.as_view(
        template_name='password_reset_done.html'
    ), name='password_reset_done'),
    
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='password_reset_confirm.html'
    ), name='password_reset_confirm'),
    
    path('password-reset-complete/', auth_views.PasswordResetCompleteView.as_view(
        template_name='password_reset_complete.html'
    ), name='password_reset_complete'),

    # ============================================================
    # 3. SHOPPING & PAYMENT ROUTES
    # ============================================================
    path('spareparts/', views.spareparts, name='spareparts'),
    path('cart/', views.cart, name='cart'),
    path('cart/add/<int:part_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/increase/<int:part_id>/', views.increase_cart, name='increase_cart'),
    path('cart/decrease/<int:part_id>/', views.decrease_cart, name='decrease_cart'),
    path('cart/remove/<int:part_id>/', views.remove_from_cart, name='remove_from_cart'),
    
    path('checkout/', views.checkout, name='checkout'),
    path('order-success/', views.order_success, name='order_success'),
    path('mpesa-callback/', views.mpesa_callback, name='mpesa_callback'),
    path('staff/orders/<int:order_id>/complete/', views.complete_order, name='complete_order'),
    # ============================================================
    # 4. STAFF ADMINISTRATION ROUTES
    # ============================================================
    path("staff/login/", views.staff_login, name="staff_login"),
    path('staff/dashboard/', views.staff_dashboard, name='staff_dashboard'),
    
    # Booking & Inquiry Management
    path('staff/bookings/', views.staff_bookings, name='staff_bookings'),
    path('staff/receipt/<int:booking_id>/', views.print_receipt, name='print_receipt'),
    path('staff/inquiries/', views.staff_inquiries, name='staff_inquiries'),
    
    # Inventory Management
    path('staff/inventory/', views.staff_inventory, name='staff_inventory'),
    path('staff/inventory/add/', views.add_sparepart, name='add_sparepart'),
    path('staff/inventory/edit/<int:pk>/', views.edit_sparepart, name='edit_sparepart'),
    path('staff/inventory/delete/<int:part_id>/', views.delete_sparepart, name='delete_sparepart'),
    path('staff/inventory/stock-report/', views.stock_report, name='stock_report'),
    
    path('staff/analytics/', views.analytics_report, name='analytics_report'),
   
    # Customer Management
    path('staff/customers/', views.staff_customers, name='staff_customers'),
    path('staff/customers/delete/<int:customer_id>/', views.delete_customer, name='delete_customer'),
    
    # Settings
    path('staff/settings/', views.staff_settings, name='staff_settings'),
     path('staff/orders/', views.staff_orders, name='staff_orders'),
]

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)