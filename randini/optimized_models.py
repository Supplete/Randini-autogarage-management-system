#django imports
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import RegexValidator

# Python imports
import random
import string


# ─────────────────────────────────────────────────────────────
# UNIFIED USER PROFILE (replaces Customer, StaffProfile, OTPVerification)
# ─────────────────────────────────────────────────────────────
class UserProfile(models.Model):
    """
    Unified profile extending Django User with customer, staff, and OTP functionality.
    Replaces 3 separate tables: Customer, StaffProfile, OTPVerification
    """
    # Link to Django User model
    user = models.OneToOneField(
        User, on_delete=models.CASCADE,
        related_name='profile', null=True, blank=True
    )
    
    # Customer fields
    phone_number = models.CharField(
        max_length=15,
        default='0000000000',
        validators=[RegexValidator(regex=r'^\+?1?\d{9,15}$', message="Phone number must be valid")]
    )
    
    # Staff fields (null for customers)
    ROLE_CHOICES = [
        ('customer', 'Customer'),
        ('mechanic', 'Mechanic'),
        ('inventory', 'Inventory Manager'),
        ('inquiries', 'Customer Inquiries Officer'),
        ('admin', 'Admin'),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='customer')
    bio = models.TextField(blank=True)
    
    # OTP fields
    otp = models.CharField(max_length=6, blank=True, null=True)
    otp_created_at = models.DateTimeField(blank=True, null=True)
    otp_is_used = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        if self.user and self.user.get_full_name():
            return f"{self.user.get_full_name()} ({self.get_role_display()})"
        return f"{self.phone_number} ({self.get_role_display()})"

    def is_expired_otp(self):
        """Check if OTP has expired (10-minute validity period)."""
        if not self.otp_created_at:
            return True
        from datetime import timedelta
        return timezone.now() > self.otp_created_at + timedelta(minutes=10)

    def generate_otp(self):
        """Generate and set a new 6-digit OTP."""
        self.otp = ''.join(random.choices(string.digits, k=6))
        self.otp_created_at = timezone.now()
        self.otp_is_used = False
        self.save()

    def is_staff_user(self):
        """Check if user is a staff member."""
        return self.role in ['mechanic', 'inventory', 'inquiries', 'admin']

    def is_customer(self):
        """Check if user is a customer."""
        return self.role == 'customer'

    # Legacy methods for compatibility
    def total_bookings(self):
        return self.user.bookings.count() if self.user else 0

    def total_orders(self):
        return self.user.order_set.count() if self.user else 0

    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"


# ─────────────────────────────────────────────────────────────
# SPARE PARTS INVENTORY
# ─────────────────────────────────────────────────────────────
class SparePart(models.Model):
    """
    A spare part available for sale in the garage shop.
    Stock is automatically decremented when an order is completed.
    """
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)
    image = models.ImageField(upload_to='spareparts/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} (Ksh {self.price})"

    def is_low_stock(self):
        return self.stock <= 5

    class Meta:
        verbose_name = "Spare Part"
        verbose_name_plural = "Spare Parts"


# ─────────────────────────────────────────────────────────────
# SERVICE PRICING
# ─────────────────────────────────────────────────────────────
class Service(models.Model):
    """
    Fixed pricing for garage services.
    Used to automatically calculate service costs for bookings.
    """
    SERVICE_CHOICES = [
        ('engine', 'Engine Repair'),
        ('body', 'Body Work'),
        ('painting', 'Car Painting'),
        ('oil', 'Oil Change'),
        ('diagnostic', 'Vehicle Diagnostic'),
        ('other', 'Other'),
    ]
    
    VEHICLE_TYPE_CHOICES = [
        ('sedan', 'Sedan'),
        ('suv', 'SUV'),
        ('truck', 'Truck'),
        ('van', 'Van'),
        ('other', 'Other'),
    ]
    
    service_type = models.CharField(max_length=20, choices=SERVICE_CHOICES)
    vehicle_type = models.CharField(max_length=20, choices=VEHICLE_TYPE_CHOICES)
    base_price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Base price for this service")
    description = models.TextField(blank=True, help_text="Description of what's included in this service")
    is_active = models.BooleanField(default=True, help_text="Whether this service is currently offered")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['service_type', 'vehicle_type']
        ordering = ['service_type', 'vehicle_type']
    
    def __str__(self):
        return f"{self.get_service_type_display()} - {self.get_vehicle_type_display()} - KSh {self.base_price}"


# ─────────────────────────────────────────────────────────────
# SERVICE BOOKINGS
# ─────────────────────────────────────────────────────────────
class Booking(models.Model):
    """
    A customer's request for vehicle service/repair.
    Staff update status and price through the Bookings module.
    """
    SERVICE_CHOICES = [
        ('engine', 'Engine Repair'),
        ('body', 'Body Work'),
        ('painting', 'Car Painting'),
        ('oil', 'Oil Change'),
        ('diagnostic', 'Vehicle Diagnostic'),
        ('other', 'Other'),
    ]
    
    VEHICLE_TYPES = [
        ('sedan', 'Sedan'),
        ('suv', 'SUV'),
        ('truck', 'Truck'),
        ('van', 'Van'),
        ('other', 'Other'),
    ]
    
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('In Progress', 'In Progress'),
        ('Completed', 'Completed'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookings', null=True, blank=True)
    full_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(
        max_length=20,
        validators=[RegexValidator(regex=r'^\+?1?\d{9,15}$', message="Phone number must be valid")]
    )
    location = models.CharField(max_length=150)
    service_type = models.CharField(max_length=20, choices=SERVICE_CHOICES)
    vehicle_type = models.CharField(max_length=20, choices=VEHICLE_TYPES)
    preferred_time = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    vehicle_image = models.ImageField(upload_to='vehicle_images/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Booking #{self.id}: {self.full_name} — {self.service_type}"
    
    def calculate_service_price(self):
        """Calculate price based on fixed service pricing."""
        try:
            service = Service.objects.get(
                service_type=self.service_type, 
                vehicle_type=self.vehicle_type, 
                is_active=True
            )
            return service.base_price
        except Service.DoesNotExist:
            default_prices = {
                'engine': 15000.00,
                'body': 25000.00,
                'painting': 20000.00,
                'oil': 3000.00,
                'diagnostic': 5000.00,
                'other': 10000.00,
            }
            return default_prices.get(self.service_type, 10000.00)
    
    def save(self, *args, **kwargs):
        """Override save to automatically calculate price if not set."""
        if self.price == 0.00:
            self.price = self.calculate_service_price()
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Booking"
        verbose_name_plural = "Bookings"


# ─────────────────────────────────────────────────────────────
# ORDERS & M-PESA PAYMENTS
# ─────────────────────────────────────────────────────────────
class Order(models.Model):
    """
    A spare-parts purchase transaction.
    Linked to M-Pesa via mpesa_checkout_id; confirmed via transaction_id from Safaricom callback.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=255)
    email = models.EmailField()
    phone_number = models.CharField(
        max_length=20,
        validators=[RegexValidator(regex=r'^\+?1?\d{9,15}$', message="Phone number must be valid")]
    )
    address = models.TextField()
    city = models.CharField(max_length=100)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=50)
    status = models.CharField(max_length=20, default='Pending')
    mpesa_checkout_id = models.CharField(max_length=100, null=True, blank=True)
    transaction_id = models.CharField(max_length=100, null=True, blank=True)
    mpesa_phone = models.CharField(max_length=20, null=True, blank=True)
    mpesa_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    mpesa_error = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order #{self.id} by {self.full_name}"

    class Meta:
        verbose_name = "Order"
        verbose_name_plural = "Orders"


class OrderItem(models.Model):
    """
    One line item inside an Order (spare part + quantity).
    Price is frozen at purchase time for accurate historical records.
    """
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(SparePart, on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)

    def get_total_item_price(self):
        return self.price * self.quantity

    def __str__(self):
        return f"{self.quantity} × {self.product.name}"

    class Meta:
        verbose_name = "Order Item"
        verbose_name_plural = "Order Items"


# ─────────────────────────────────────────────────────────────
# COMMUNICATIONS
# ─────────────────────────────────────────────────────────────
class ContactMessage(models.Model):
    """
    A message submitted via the public Contact Us form.
    Staff mark messages as read or delete from the Inquiries module.
    """
    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(
        max_length=20,
        validators=[RegexValidator(regex=r'^\+?1?\d{9,15}$', message="Phone number must be valid")]
    )
    inquiry_type = models.CharField(max_length=50, choices=[
        ('general', 'General Inquiry'),
        ('service', 'Service Request'),
        ('parts', 'Spare Parts'),
        ('booking', 'Booking Inquiry'),
        ('complaint', 'Complaint'),
        ('feedback', 'Feedback'),
        ('other', 'Other')
    ], default='general')
    subject = models.CharField(max_length=200)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"[{self.get_inquiry_type_display}] Message from {self.name} — {self.subject}"

    class Meta:
        verbose_name = "Contact Message"
        verbose_name_plural = "Contact Messages"
