#django imports
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import RegexValidator

# Python imports
import random
import string


# ─────────────────────────────────────────────────────────────
# CUSTOMER PROFILE
# ─────────────────────────────────────────────────────────────
class Customer(models.Model):
    """
    Extends Django's built-in User model with garage-specific info.
    Each registered customer gets exactly one Customer profile (OneToOne).
    """
    user = models.OneToOneField(
        User, on_delete=models.CASCADE,
        related_name='customer_profile', null=True, blank=True
    )
    phone_number = models.CharField(
        max_length=15,
        default='0000000000',
        validators=[RegexValidator(regex=r'^\+?1?\d{9,15}$', message="Phone number must be valid")]
    )

    def __str__(self):
        if self.user and self.user.get_full_name():
            return self.user.get_full_name()
        return self.phone_number

    def total_bookings(self):
        return self.user.bookings.count() if self.user else 0

    class Meta:
        verbose_name = "Customer"
        verbose_name_plural = "Customers"

    def total_orders(self):
        return self.user.order_set.count() if self.user else 0


# ─────────────────────────────────────────────────────────────
# STAFF PROFILE (Role-Based Access)
# ─────────────────────────────────────────────────────────────
class StaffProfile(models.Model):
    """
    Assigns a specific operational role to each staff member.
    Role determines which dashboard/page they see on login:
      mechanic   → /staff/bookings/
      inventory  → /staff/inventory/
      inquiries  → /staff/inquiries/
      admin      → /staff/dashboard/ (full access)
    """
    # Define available staff roles with human-readable labels
    # These roles determine dashboard access and system permissions
    ROLE_CHOICES = [
        ('mechanic',   'Mechanic'),              # Handles service bookings and repairs
        ('inventory',  'Inventory Manager'),     # Manages spare parts and stock
        ('inquiries',  'Customer Inquiries Officer'), # Handles customer communications
        ('admin',      'Admin'),                # Full system access and management
    ]

    # One-to-one relationship with Django User model
    # Staff profile is deleted when corresponding User is deleted
    user      = models.OneToOneField(User, on_delete=models.CASCADE, related_name='staff_profile')
    # Staff role determines dashboard access and permissions
    role      = models.CharField(max_length=20, choices=ROLE_CHOICES, default='mechanic')
    # Optional staff biography/description
    bio       = models.TextField(blank=True)
    # Optional staff profile photo
    photo     = models.ImageField(upload_to='staff_photos/', blank=True, null=True)
    # Timestamp when staff profile was created
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        """String representation of StaffProfile object.
        
        Returns:
            str: Staff member's full name and role
        """
        return f"{self.user.get_full_name()} — {self.get_role_display()}"


# ─────────────────────────────────────────────────────────────
# OTP VERIFICATION
# ─────────────────────────────────────────────────────────────
class OTPVerification(models.Model):
    """
    Stores a 6-digit OTP sent to the user's email during registration.
    OTPs expire after 10 minutes. Accounts are only activated after OTP is verified.
    """
    # Email address of user requesting OTP verification
    email      = models.EmailField()
    # 6-digit one-time password for email verification
    otp        = models.CharField(max_length=6)
    # Timestamp when OTP was generated
    created_at = models.DateTimeField(auto_now_add=True)
    # Flag to track if OTP has been used (prevents reuse)
    is_used    = models.BooleanField(default=False)

    def is_expired(self):
        """Check if OTP has expired (10-minute validity period).
        
        Returns:
            bool: True if OTP is expired, False otherwise
        """
        from datetime import timedelta
        return timezone.now() > self.created_at + timedelta(minutes=10)

    @staticmethod
    def generate_otp():
        """Generate a random 6-digit OTP.
        
        Returns:
            str: 6-digit numeric OTP
        """
        return ''.join(random.choices(string.digits, k=6))

    def __str__(self):
        """String representation of OTPVerification object.
        
        Returns:
            str: OTP status information including email and usage status
        """
        return f"OTP for {self.email} — {'Used' if self.is_used else 'Active'}"


# ─────────────────────────────────────────────────────────────
# SPARE PARTS INVENTORY
# ─────────────────────────────────────────────────────────────
class SparePart(models.Model):
    """
    A spare part available for sale in the garage shop.
    Stock is automatically decremented when an order is completed.
    """
    # Spare part name (e.g., "Oil Filter", "Brake Pads")
    name        = models.CharField(max_length=200)
    # Detailed description of the spare part
    description = models.TextField(blank=True)
    # Selling price in Kenyan Shillings (2 decimal places for cents)
    price       = models.DecimalField(max_digits=10, decimal_places=2)
    # Current stock quantity (automatically decremented on orders)
    stock       = models.PositiveIntegerField(default=0)
    # Optional product image for display in shop
    image       = models.ImageField(upload_to='spareparts/', blank=True, null=True)
    # Timestamp when spare part was added to inventory
    created_at  = models.DateTimeField(auto_now_add=True)
    # Timestamp when spare part details were last updated
    updated_at  = models.DateTimeField(auto_now=True)

    def __str__(self):
        """String representation of SparePart object.
        
        Returns:
            str: Spare part name and price in Kenyan Shillings
        """
        return f"{self.name} (Ksh {self.price})"

    def is_low_stock(self):
        """Check if spare part stock is running low.
        
        Returns:
            bool: True if stock is 5 or less units (needs reordering)
        """
        return self.stock <= 5


# ─────────────────────────────────────────────────────────────
# SERVICE PRICING
# ─────────────────────────────────────────────────────────────
class Service(models.Model):
    """
    Fixed pricing for garage services.
    Used to automatically calculate service costs for bookings.
    """
    # Define available service types with human-readable labels
    SERVICE_CHOICES = [
        ('engine', 'Engine Repair'),        # Engine diagnostics and repairs
        ('body', 'Body Work'),              # Dent repair, body work
        ('painting', 'Car Painting'),       # Vehicle painting and detailing
        ('oil', 'Oil Change'),             # Oil and filter changes
        ('diagnostic', 'Vehicle Diagnostic'), # Computer diagnostics
        ('other', 'Other'),                 # Miscellaneous services
    ]
    
    # Define vehicle types for differential pricing
    VEHICLE_TYPE_CHOICES = [
        ('sedan', 'Sedan'),                 # Standard passenger cars
        ('suv', 'SUV'),                     # Sport Utility Vehicles
        ('truck', 'Truck'),                 # Commercial trucks
        ('van', 'Van'),                     # Passenger and cargo vans
        ('other', 'Other'),                 # Other vehicle types
    ]
    
    # Type of service (engine, body, painting, etc.)
    service_type = models.CharField(max_length=20, choices=SERVICE_CHOICES)
    # Vehicle type for this service pricing (sedan, SUV, etc.)
    vehicle_type = models.CharField(max_length=20, choices=VEHICLE_TYPE_CHOICES)
    # Base price for this service/vehicle combination
    base_price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Base price for this service")
    # Detailed description of what's included in this service
    description = models.TextField(blank=True, help_text="Description of what's included in this service")
    # Whether this service is currently available for booking
    is_active = models.BooleanField(default=True, help_text="Whether this service is currently offered")
    # Timestamp when service pricing was created
    created_at = models.DateTimeField(auto_now_add=True)
    # Timestamp when service pricing was last updated
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['service_type', 'vehicle_type']
        ordering = ['service_type', 'vehicle_type']
    
    def __str__(self):
        """String representation of Service object.
        
        Returns:
            str: Service type, vehicle type, and price in Kenyan Shillings
        """
        return f"{self.get_service_type_display()} - {self.get_vehicle_type_display()} - KSh {self.base_price}"
    
    def get_price_for_vehicle(self, vehicle_type):
        """Get price for specific vehicle type.
        
        Args:
            vehicle_type (str): Target vehicle type (sedan, SUV, etc.)
            
        Returns:
            Decimal: Price for the specified vehicle type
        """
        try:
            service = Service.objects.get(service_type=self.service_type, vehicle_type=vehicle_type, is_active=True)
            return service.base_price
        except Service.DoesNotExist:
            return self.base_price  # Return base price if specific vehicle type not found


# ─────────────────────────────────────────────────────────────
# SERVICE BOOKINGS
# ─────────────────────────────────────────────────────────────
class Booking(models.Model):
    """
    A customer's request for vehicle service/repair.
    Staff update status and price through the Bookings module.
    updated_at is auto-stamped whenever a staff member saves changes.
    """
    # Define available service types for booking
    SERVICE_CHOICES = [
        ('engine', 'Engine Repair'),         # Engine diagnostics and repairs
        ('body', 'Body Work'),               # Dent repair, body work
        ('painting', 'Car Painting'),        # Vehicle painting and detailing
        ('oil', 'Oil Change'),              # Oil and filter changes
        ('diagnostic', 'Vehicle Diagnostic'), # Computer diagnostics
        ('other', 'Other'),                  # Miscellaneous services
    ]
    # Define vehicle types for service booking
    VEHICLE_TYPES = [
        ('sedan', 'Sedan'),                  # Standard passenger cars
        ('suv', 'SUV'),                      # Sport Utility Vehicles
        ('truck', 'Truck'),                  # Commercial trucks
        ('van', 'Van'),                      # Passenger and cargo vans
        ('other', 'Other'),                  # Other vehicle types
    ]
    # Define booking status progression
    STATUS_CHOICES = [
        ('Pending', 'Pending'),              # New booking awaiting assignment
        ('In Progress', 'In Progress'),     # Service currently being performed
        ('Completed', 'Completed'),          # Service finished and invoiced
    ]

    # Optional link to registered user (null for guest bookings)
    user          = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookings', null=True, blank=True)
    # Customer's full name (required even for registered users)
    full_name     = models.CharField(max_length=100)
    # Customer's email address for notifications
    email         = models.EmailField()
    # Customer's phone number with international format validation
    phone = models.CharField(
        max_length=20,
        validators=[RegexValidator(regex=r'^\+?1?\d{9,15}$', message="Phone number must be valid")]
    )
    # Customer's location/address for service
    location      = models.CharField(max_length=150)
    # Type of service requested (engine, body, painting, etc.)
    service_type  = models.CharField(max_length=20, choices=SERVICE_CHOICES)
    # Customer's vehicle type for pricing and service planning
    vehicle_type  = models.CharField(max_length=20, choices=VEHICLE_TYPES)
    # Customer's preferred appointment date and time
    preferred_time = models.DateTimeField()
    # Current status of the booking (Pending, In Progress, Completed)
    status        = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    # Service price (auto-calculated or manually set by staff)
    price         = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    # Optional image of vehicle for reference
    vehicle_image = models.ImageField(upload_to='vehicle_images/', blank=True, null=True)
    # Timestamp when booking was created by customer
    created_at    = models.DateTimeField(auto_now_add=True)
    # Timestamp when booking was last updated by staff
    updated_at    = models.DateTimeField(auto_now=True)

    def __str__(self):
        """String representation of Booking object.
        
        Returns:
            str: Booking ID, customer name, and service type
        """
        return f"Booking #{self.id}: {self.full_name} — {self.service_type}"
    
    def calculate_service_price(self):
        """Calculate price based on fixed service pricing.
        
        Returns:
            Decimal: Calculated service price based on service and vehicle type
        """
        try:
            service = Service.objects.get(
                service_type=self.service_type, 
                vehicle_type=self.vehicle_type, 
                is_active=True
            )
            return service.base_price
        except Service.DoesNotExist:
            # Return default price if no fixed pricing found
            default_prices = {
                'engine': 15000.00,      # Engine repair pricing
                'body': 25000.00,        # Body work pricing
                'painting': 20000.00,    # Painting services
                'oil': 3000.00,          # Oil change pricing
                'diagnostic': 5000.00,  # Diagnostic services
                'other': 10000.00,      # Miscellaneous services
            }
            return default_prices.get(self.service_type, 10000.00)
    
    def save(self, *args, **kwargs):
        """Override save to automatically calculate price if not set.
        
        This method ensures that every booking has a price calculated
        based on the service pricing matrix unless manually overridden.
        """
        if self.price == 0.00:  # Only calculate if price is not manually set
            self.price = self.calculate_service_price()
        super().save(*args, **kwargs)


# ─────────────────────────────────────────────────────────────
# ORDERS & M-PESA PAYMENTS
# ─────────────────────────────────────────────────────────────
class Order(models.Model):
    """
    A spare-parts purchase transaction.
    Linked to M-Pesa via mpesa_checkout_id; confirmed via transaction_id from Safaricom callback.
    Status lifecycle: Pending → Completed (paid) or Failed (cancelled/error)
    """
    # Customer who placed the order (required)
    user           = models.ForeignKey(User, on_delete=models.CASCADE)
    # Customer's full name for delivery and records
    full_name      = models.CharField(max_length=255)
    # Customer's email for order confirmation
    email          = models.EmailField()
    # Customer's phone number with validation
    phone_number   = models.CharField(
        max_length=20,
        validators=[RegexValidator(regex=r'^\+?1?\d{9,15}$', message="Phone number must be valid")]
    )
    # Delivery address for the order
    address        = models.TextField()
    # City for delivery and logistics
    city           = models.CharField(max_length=100)
    # Total order amount (sum of all items)
    total_amount   = models.DecimalField(max_digits=10, decimal_places=2)
    # Payment method used ('mpesa' or 'cash')
    payment_method = models.CharField(max_length=50)
    # Order status (Pending, Completed, Failed)
    status         = models.CharField(max_length=20, default='Pending')
    # M-Pesa checkout request ID for payment initiation
    mpesa_checkout_id = models.CharField(max_length=100, null=True, blank=True)
    # M-Pesa transaction ID from payment confirmation
    transaction_id    = models.CharField(max_length=100, null=True, blank=True)
    # Phone number used for M-Pesa payment
    mpesa_phone        = models.CharField(max_length=20, null=True, blank=True)
    # Amount actually paid via M-Pesa
    mpesa_amount       = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    # Error message if M-Pesa payment failed
    mpesa_error        = models.TextField(null=True, blank=True)
    # Timestamp when order was created
    created_at     = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        """String representation of Order object.
        
        Returns:
            str: Order ID and customer name
        """
        return f"Order #{self.id} by {self.full_name}"


class OrderItem(models.Model):
    """
    One line item inside an Order (spare part + quantity).
    Price is frozen at purchase time for accurate historical records.
    """
    # Link to the parent order (deleted if order is deleted)
    order    = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    # Link to the spare part product (deleted if part is deleted)
    product  = models.ForeignKey(SparePart, on_delete=models.CASCADE)
    # Price at time of purchase (frozen for historical accuracy)
    price    = models.DecimalField(max_digits=10, decimal_places=2)
    # Quantity of this item ordered
    quantity = models.PositiveIntegerField(default=1)

    def get_total_item_price(self):
        """Calculate total price for this order item.
        
        Returns:
            Decimal: Total price (price × quantity)
        """
        return self.price * self.quantity

    def __str__(self):
        """String representation of OrderItem object.
        
        Returns:
            str: Quantity and product name
        """
        return f"{self.quantity} × {self.product.name}"


# ─────────────────────────────────────────────────────────────
# COMMUNICATIONS
# ─────────────────────────────────────────────────────────────
class ContactMessage(models.Model):
    """
    A message submitted via the public Contact Us form.
    Staff mark messages as read or delete from the Inquiries module.
    """
    # Name of person sending the message
    name    = models.CharField(max_length=100)
    # Email address for response
    email   = models.EmailField()
    # Phone number for contact (optional)
    phone   = models.CharField(
        max_length=20,
        validators=[RegexValidator(regex=r'^\+?1?\d{9,15}$', message="Phone number must be valid")]
    )
    # Inquiry type/category
    inquiry_type = models.CharField(max_length=50, choices=[
        ('general', 'General Inquiry'),
        ('service', 'Service Request'),
        ('parts', 'Spare Parts'),
        ('booking', 'Booking Inquiry'),
        ('complaint', 'Complaint'),
        ('feedback', 'Feedback'),
        ('other', 'Other')
    ], default='general')
    # Subject line of the message
    subject = models.CharField(max_length=200)
    # Full message content
    message = models.TextField()
    # Timestamp when message was sent
    created_at = models.DateTimeField(auto_now_add=True)
    # Whether message has been read by staff
    is_read = models.BooleanField(default=False)

    def __str__(self):
        """String representation of ContactMessage object.

        Returns:
            str: Sender name and message subject
        """
        return f"[{self.get_inquiry_type_display}] Message from {self.name} — {self.subject}"
