from django.db import models
from django.contrib.auth.models import User
from django.conf import settings

# ----------------------------
# CUSTOMER PROFILE
# ----------------------------
class Customer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='customer_profile')
    phone = models.CharField(max_length=15)

    def __str__(self):
        return f"{self.user.username} - {self.phone}"

# ----------------------------
# SPARE PARTS INVENTORY
# ----------------------------
class SparePart(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)
    image = models.ImageField(upload_to="spareparts/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} (Ksh {self.price})"

# ----------------------------
# SERVICE BOOKINGS
# ----------------------------
class Booking(models.Model):
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
        ('motorbike', 'Motorbike'),
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
    phone = models.CharField(max_length=20)
    location = models.CharField(max_length=150)
    
    # Service Details
    service_type = models.CharField(max_length=20, choices=SERVICE_CHOICES)
    vehicle_type = models.CharField(max_length=20, choices=VEHICLE_TYPES)
    preferred_time = models.DateTimeField()
    
    # Garage Management
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    vehicle_image = models.ImageField(upload_to='vehicle_images/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Booking #{self.id}: {self.full_name} - {self.service_type}"

# ----------------------------
# ORDERS & M-PESA PAYMENTS
# ----------------------------
class Order(models.Model):
    PAYMENT_STATUS = (
        ('Pending', 'Pending'),
        ('Completed', 'Completed'),
        ('Failed', 'Failed'),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=15)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    # M-PESA HANDSHAKE FIELDS
    # Crucial: CheckoutRequestID from Safaricom to link callback to this order
    mpesa_checkout_id = models.CharField(max_length=100, blank=True, null=True, unique=True)
    # M-Pesa Receipt Number (e.g., RBC123XYZ)
    transaction_id = models.CharField(max_length=100, blank=True, null=True) 
    
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order {self.id} by {self.user.username}"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(SparePart, on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2) # Price at time of purchase
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"

# ----------------------------
# COMMUNICATIONS
# ----------------------------
class ContactMessage(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    subject = models.CharField(max_length=200)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"Message from {self.name} - {self.subject}"