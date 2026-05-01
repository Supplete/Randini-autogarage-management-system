
from django import forms
from django.contrib.auth.models import User
from django.core.validators import RegexValidator, EmailValidator
from django.utils import timezone
from datetime import timedelta
from .models import Booking, SparePart, UserProfile


# INVENTORY FORMs

class SparePartForm(forms.ModelForm):

    class Meta:
        model = SparePart
        fields = ['name', 'price', 'stock', 'image']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'stock': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'image': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
        }

    def clean_price(self):
        """Validate that price is positive and reasonable."""
        price = self.cleaned_data.get('price')
        if price <= 0:
            raise forms.ValidationError("Price must be greater than 0.")
        if price > 1000000:  # Sanity check for very high prices
            raise forms.ValidationError("Price seems too high. Please verify.")
        return price

    def clean_stock(self):
        """Validate that stock is not negative."""
        stock = self.cleaned_data.get('stock')
        if stock < 0:
            raise forms.ValidationError("Stock cannot be negative.")
        return stock

    def clean_image(self):
        """
        Validate uploaded spare part image.
        
        Restrictions:
        - Max file size: 5MB
        - Allowed formats: JPEG, PNG, GIF, WebP
        """
        image = self.cleaned_data.get('image', False)
        if image:
            # Only validate new uploads, not existing images
            if hasattr(image, 'content_type'):
                # Check file size (max 5MB)
                if image.size > 5 * 1024 * 1024:
                    raise forms.ValidationError("Image must be less than 5MB.")
                
                # Check file type
                allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
                if image.content_type not in allowed_types:
                    raise forms.ValidationError("Image must be JPEG, PNG, GIF, or WebP format.")
        
        return image


# ─────────────────────────────────────────────────────────────
# CUSTOMER BOOKING FORM
# ─────────────────────────────────────────────────────────────

class BookingForm(forms.ModelForm):
    """
    Form for customers to book vehicle services.
    
    Handles service appointment requests with comprehensive validation.
    Includes date/time validation and file upload restrictions.
    
    Fields:
        - full_name: Customer's full name
        - email: Customer's email address
        - phone: Customer's phone number
        - location: Customer's location/address
        - preferred_time: Desired appointment time
        - vehicle_type: Type of vehicle
        - service_type: Type of service needed
        - vehicle_image: Optional vehicle photo
    """
    class Meta:
        model = Booking
        fields = [
            'full_name', 'email', 'phone', 'location', 
            'preferred_time', 'vehicle_type', 'service_type', 'vehicle_image'
        ]
        widgets = {
            'preferred_time': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        """Initialize form with Bootstrap classes and date restrictions."""
        super().__init__(*args, **kwargs)
        # Apply Bootstrap form-control class to all fields
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})
        
        # Set minimum date to current datetime to prevent past bookings
        self.fields['preferred_time'].widget.attrs.update({
            'min': timezone.now().strftime('%Y-%m-%dT%H:%M')
        })

    def clean_full_name(self):
        """Validate and format customer's full name."""
        full_name = self.cleaned_data.get('full_name')
        if not full_name or len(full_name.strip()) < 2:
            raise forms.ValidationError("Full name must be at least 2 characters long.")
        if not all(char.isalpha() or char.isspace() or char in "-'" for char in full_name):
            raise forms.ValidationError("Full name can only contain letters, spaces, hyphens, and apostrophes.")
        return full_name.strip().title()

    def clean_email(self):
        """Validate email format and convert to lowercase."""
        email = self.cleaned_data.get('email')
        if not email:
            raise forms.ValidationError("Email is required.")
        validator = EmailValidator()
        try:
            validator(email)
        except forms.ValidationError:
            raise forms.ValidationError("Please enter a valid email address.")
        return email.lower()

    def clean_phone(self):
        """Validate phone number format and length."""
        phone = self.cleaned_data.get('phone')
        if not phone:
            raise forms.ValidationError("Phone number is required.")
        # Remove any non-digit characters except +
        clean_phone = ''.join(char for char in phone if char.isdigit() or char == '+')
        if not clean_phone.isdigit() or len(clean_phone) < 9 or len(clean_phone) > 15:
            raise forms.ValidationError("Please enter a valid phone number (9-15 digits).")
        return clean_phone

    def clean_location(self):
        """Validate customer location."""
        location = self.cleaned_data.get('location')
        if not location or len(location.strip()) < 3:
            raise forms.ValidationError("Location must be at least 3 characters long.")
        return location.strip()

    def clean_preferred_time(self):
        """
        Validate appointment date and time.
        
        Ensures:
        - Time is not in the past
        - Time is not too far in the future (3 months max)
        - Time is during reasonable business hours
        """
        preferred_time = self.cleaned_data.get('preferred_time')
        if not preferred_time:
            raise forms.ValidationError("Preferred time is required.")
        
        # Check if the date is in the past
        if preferred_time < timezone.now():
            raise forms.ValidationError("Preferred time cannot be in the past.")
        
        # Check if the date is too far in the future (more than 3 months)
        three_months_from_now = timezone.now() + timedelta(days=90)
        if preferred_time > three_months_from_now:
            raise forms.ValidationError("Preferred time cannot be more than 3 months in the future.")
        
        # Optional: Check business hours (8 AM - 6 PM)
        if preferred_time.hour < 8 or preferred_time.hour > 18:
            raise forms.ValidationError("Preferred time must be between 8 AM and 6 PM.")
        
        return preferred_time

    def clean_vehicle_image(self):
        """
        Validate uploaded vehicle image.
        
        Restrictions:
        - Max file size: 5MB
        - Allowed formats: JPEG, PNG, GIF, WebP
        """
        vehicle_image = self.cleaned_data.get('vehicle_image', False)
        if vehicle_image:
            # Check file size (max 5MB)
            if vehicle_image.size > 5 * 1024 * 1024:
                raise forms.ValidationError("Vehicle image must be less than 5MB.")
            
            # Check file type
            allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
            if vehicle_image.content_type not in allowed_types:
                raise forms.ValidationError("Vehicle image must be JPEG, PNG, GIF, or WebP format.")
        
        return vehicle_image


# ─────────────────────────────────────────────────────────────
# STAFF REGISTRATION FORM
# ─────────────────────────────────────────────────────────────

class StaffRegistrationForm(forms.ModelForm):
    """
    Form for registering new staff members by administrators.
    
    Creates User account and StaffProfile with role assignment.
    Includes strong password requirements and email uniqueness.
    
    Fields:
        - first_name, last_name: Staff member's name
        - email: Staff email (must be unique)
        - password: Strong password with complexity requirements
        - confirm_password: Password confirmation
        - role: Staff role (mechanic, inventory, inquiries, admin)
        - bio: Optional staff biography
        - is_active: Staff account status (active/inactive)
    """
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        min_length=8,
        help_text="Minimum 8 characters with letters, numbers, and special characters"
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        label="Confirm Password"
    )
    role = forms.ChoiceField(
        choices=UserProfile.ROLE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    bio = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        required=False
    )
    is_active = forms.BooleanField(
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label="Active Account",
        initial=True,
        required=False,
        help_text="Uncheck to create staff account as inactive (cannot login)"
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        """Initialize form with required field settings."""
        super().__init__(*args, **kwargs)
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True

    def clean_first_name(self):
        """Validate and format first name."""
        first_name = self.cleaned_data.get('first_name')
        if not first_name or len(first_name.strip()) < 2:
            raise forms.ValidationError("First name must be at least 2 characters long.")
        if not first_name.replace(' ', '').replace('-', '').replace("'", '').isalpha():
            raise forms.ValidationError("First name can only contain letters, spaces, hyphens, and apostrophes.")
        return first_name.strip().title()

    def clean_last_name(self):
        """Validate and format last name."""
        last_name = self.cleaned_data.get('last_name')
        if not last_name or len(last_name.strip()) < 2:
            raise forms.ValidationError("Last name must be at least 2 characters long.")
        if not last_name.replace(' ', '').replace('-', '').replace("'", '').isalpha():
            raise forms.ValidationError("Last name can only contain letters, spaces, hyphens, and apostrophes.")
        return last_name.strip().title()

    def clean_email(self):
        """Validate email format and uniqueness."""
        email = self.cleaned_data.get('email')
        if not email:
            raise forms.ValidationError("Email is required.")
        validator = EmailValidator()
        try:
            validator(email)
        except forms.ValidationError:
            raise forms.ValidationError("Please enter a valid email address.")
        
        email = email.lower()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("A user with this email already exists.")
        return email

    def clean_password(self):
        """
        Validate password strength requirements.
        
        Requirements:
        - Minimum 8 characters
        - At least one letter
        - At least one number
        - At least one special character
        """
        password = self.cleaned_data.get('password')
        if len(password) < 8:
            raise forms.ValidationError("Password must be at least 8 characters long.")
        
        # Check for at least one letter
        if not any(char.isalpha() for char in password):
            raise forms.ValidationError("Password must contain at least one letter.")
        
        # Check for at least one number
        if not any(char.isdigit() for char in password):
            raise forms.ValidationError("Password must contain at least one number.")
        
        # Check for at least one special character
        special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
        if not any(char in special_chars for char in password):
            raise forms.ValidationError("Password must contain at least one special character.")
        
        return password

    def clean(self):
        """Validate that passwords match."""
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        
        if password and confirm_password and password != confirm_password:
            raise forms.ValidationError("Passwords do not match.")
        
        return cleaned_data


# ─────────────────────────────────────────────────────────────
# CUSTOMER REGISTRATION FORM
# ─────────────────────────────────────────────────────────────

class CustomerRegistrationForm(forms.ModelForm):
    """
    Form for customer registration with OTP verification.
    
    Creates User account for customers with email verification.
    Similar validation to staff form but without role assignment.
    
    Fields:
        - first_name, last_name: Customer's name
        - email: Customer email (must be unique)
        - password1, password2: Password and confirmation
    """
    password1 = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        min_length=8,
        help_text="Minimum 8 characters with letters, numbers, and special characters"
    )
    password2 = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )
    
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }

    def clean_email(self):
        """Validate email format and uniqueness."""
        email = self.cleaned_data.get('email')
        if not email:
            raise forms.ValidationError("Email is required.")
        validator = EmailValidator()
        try:
            validator(email)
        except forms.ValidationError:
            raise forms.ValidationError("Please enter a valid email address.")
        
        email = email.lower()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("A user with this email already exists.")
        return email

    def clean_password1(self):
        """Validate password strength (same as staff form)."""
        password = self.cleaned_data.get('password1')
        if len(password) < 8:
            raise forms.ValidationError("Password must be at least 8 characters long.")
        
        # Check for at least one letter
        if not any(char.isalpha() for char in password):
            raise forms.ValidationError("Password must contain at least one letter.")
        
        # Check for at least one number
        if not any(char.isdigit() for char in password):
            raise forms.ValidationError("Password must contain at least one number.")
        
        # Check for at least one special character
        special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
        if not any(char in special_chars for char in password):
            raise forms.ValidationError("Password must contain at least one special character.")
        
        return password

    def clean(self):
        """Validate that passwords match."""
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')
        
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords do not match.")
        
        return cleaned_data


class StaffCustomerForm(forms.ModelForm):
    """
    Form for staff to add customers (simplified version).
    """
    phone_number = forms.CharField(
        label="Phone Number",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+254 XXX XXX XXX'}),
        required=True,
        help_text="Enter customer's phone number with country code"
    )
    
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }
    
    def clean_email(self):
        """Validate email is unique."""
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("A customer with this email already exists.")
        return email
    
    def clean_phone_number(self):
        """Validate phone number format."""
        phone_number = self.cleaned_data.get('phone_number')
        if not phone_number:
            raise forms.ValidationError("Phone number is required.")
        
        # Remove any non-digit characters except +
        clean_phone = ''.join(char for char in phone_number if char.isdigit() or char == '+')
        if not clean_phone.isdigit() or len(clean_phone) < 9 or len(clean_phone) > 15:
            raise forms.ValidationError("Please enter a valid phone number (9-15 digits).")
        return clean_phone


# ─────────────────────────────────────────────────────────────
# CUSTOMER PROFILE FORM
# ─────────────────────────────────────────────────────────────

class CustomerProfileForm(forms.ModelForm):
    """
    Form for customers to update their profile information.
    
    Allows customers to update phone number and address.
    Phone number validation ensures Kenyan format compatibility.
    
    Fields:
        - phone_number: Customer's phone number
        - address: Customer's address (optional)
    """
    phone_number = forms.CharField(
        validators=[RegexValidator(regex=r'^\+?1?\d{9,15}$', message="Phone number must be valid (9-15 digits)")],
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 0712345678 or +254712345678'})
    )
    
    class Meta:
        model = UserProfile
        fields = ['phone_number']

    def clean_phone_number(self):
        """Validate and format phone number."""
        phone_number = self.cleaned_data.get('phone_number')
        if not phone_number:
            raise forms.ValidationError("Phone number is required.")
        
        # Remove any non-digit characters except +
        clean_phone = ''.join(char for char in phone_number if char.isdigit() or char == '+')
        
        if not clean_phone.isdigit() or len(clean_phone) < 9 or len(clean_phone) > 15:
            raise forms.ValidationError("Please enter a valid phone number (9-15 digits).")
        
        return clean_phone


# ─────────────────────────────────────────────────────────────
# CONTACT FORM
# ─────────────────────────────────────────────────────────────

class ContactForm(forms.Form):
    """
    Form for customers to send inquiries via the Contact Us page.
    
    Captures customer inquiries with validation for all fields.
    Messages are stored and can be managed by staff.
    
    Fields:
        - name: Customer's full name
        - email: Customer's email address
        - phone: Customer's phone number
        - subject: Inquiry subject
        - message: Detailed inquiry message
    """
    name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'John Doe'}),
        help_text="Enter your full name"
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'john@example.com'}),
        help_text="We'll never share your email with anyone else"
    )
    phone = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+254712345678'}),
        help_text="Include country code for international numbers"
    )
    subject = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Subject of your inquiry'}),
        help_text="Brief description of your inquiry"
    )
    message = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Write your message here...'}),
        help_text="Provide details about your inquiry"
    )

    def clean_name(self):
        """Validate and format customer name."""
        name = self.cleaned_data.get('name')
        if not name or len(name.strip()) < 2:
            raise forms.ValidationError("Name must be at least 2 characters long.")
        if not all(char.isalpha() or char.isspace() or char in "-'" for char in name):
            raise forms.ValidationError("Name can only contain letters, spaces, hyphens, and apostrophes.")
        return name.strip().title()

    def clean_email(self):
        """Validate email format."""
        email = self.cleaned_data.get('email')
        if not email:
            raise forms.ValidationError("Email is required.")
        validator = EmailValidator()
        try:
            validator(email)
        except forms.ValidationError:
            raise forms.ValidationError("Please enter a valid email address.")
        return email.lower()

    def clean_phone(self):
        """Validate phone number format."""
        phone = self.cleaned_data.get('phone')
        if not phone:
            raise forms.ValidationError("Phone number is required.")
        
        # Remove any non-digit characters except +
        clean_phone = ''.join(char for char in phone if char.isdigit() or char == '+')
        
        # Check if phone starts with + followed by digits, or just digits
        if clean_phone.startswith('+'):
            digits_part = clean_phone[1:]
            if not digits_part.isdigit() or len(digits_part) < 9 or len(digits_part) > 15:
                raise forms.ValidationError("Please enter a valid phone number (9-15 digits after country code).")
        else:
            if not clean_phone.isdigit() or len(clean_phone) < 9 or len(clean_phone) > 15:
                raise forms.ValidationError("Please enter a valid phone number (9-15 digits).")
        
        return clean_phone

    def clean_subject(self):
        """Validate inquiry subject."""
        subject = self.cleaned_data.get('subject')
        if not subject or len(subject.strip()) < 3:
            raise forms.ValidationError("Subject must be at least 3 characters long.")
        return subject.strip()

    def clean_message(self):
        """Validate inquiry message."""
        message = self.cleaned_data.get('message')
        if not message or len(message.strip()) < 10:
            raise forms.ValidationError("Message must be at least 10 characters long.")
        return message.strip()


# ─────────────────────────────────────────────────────────────
# INVOICE FORMS
# ─────────────────────────────────────────────────────────────

class InvoiceForm(forms.Form):
    """
    Form for creating and managing service invoices.
    Includes service details, pricing, and customer information.
    """
    
    PAYMENT_METHODS = [
        ('cash', 'Cash'),
        ('mpesa', 'M-Pesa'),
        ('card', 'Card'),
        ('bank_transfer', 'Bank Transfer'),
    ]
    
    INVOICE_STATUS = [
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('paid', 'Paid'),
        ('overdue', 'Overdue'),
        ('cancelled', 'Cancelled'),
    ]
    
    # Customer Information
    customer_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter customer full name'
        })
    )
    
    customer_email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'customer@example.com'
        })
    )
    
    customer_phone = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+254 7XX XXX XXX'
        })
    )
    
    customer_address = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Customer address'
        })
    )
    
    # Service Information
    service_type = forms.ChoiceField(
        choices=[
            ('engine', 'Engine Repair'),
            ('body', 'Body Work'),
            ('painting', 'Car Painting'),
            ('oil', 'Oil Change'),
            ('diagnostic', 'Vehicle Diagnostic'),
            ('other', 'Other'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    vehicle_type = forms.ChoiceField(
        choices=[
            ('sedan', 'Sedan'),
            ('suv', 'SUV'),
            ('truck', 'Truck'),
            ('van', 'Van'),
            ('other', 'Other'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    vehicle_make = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., Toyota, Honda, Nissan'
        })
    )
    
    vehicle_model = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., Corolla, CR-V, Frontier'
        })
    )
    
    vehicle_registration = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'KXX 123X'
        })
    )
    
    # Pricing
    labor_cost = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '0.00',
            'step': '0.01'
        })
    )
    
    parts_cost = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '0.00',
            'step': '0.01'
        })
    )
    
    tax_rate = forms.DecimalField(
        max_digits=5,
        decimal_places=2,
        min_value=0,
        max_value=100,
        initial=16.0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '16.0',
            'step': '0.1'
        })
    )
    
    # Invoice Details
    invoice_number = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'INV-2026-001'
        })
    )
    
    issue_date = forms.DateField(
        initial=timezone.now().date(),
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    due_date = forms.DateField(
        initial=timezone.now().date() + timezone.timedelta(days=14),
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    payment_method = forms.ChoiceField(
        choices=PAYMENT_METHODS,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    status = forms.ChoiceField(
        choices=INVOICE_STATUS,
        initial='draft',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    # Additional Information
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Additional notes or terms...'
        })
    )
    
    # Spare Parts (for multiple parts)
    spare_parts = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'List spare parts (one per line):\nPart 1 - KSh 1500\nPart 2 - KSh 2000'
        })
    )
    
    def __init__(self, *args, **kwargs):
        """Initialize form with required field settings."""
        super().__init__(*args, **kwargs)
        self.fields['customer_name'].required = True
        self.fields['customer_email'].required = True
        self.fields['customer_phone'].required = True
        self.fields['service_type'].required = True
        self.fields['vehicle_type'].required = True
        self.fields['vehicle_make'].required = True
        self.fields['vehicle_model'].required = True
        self.fields['labor_cost'].required = True
        self.fields['parts_cost'].required = True
    
    def clean_customer_phone(self):
        """Validate phone number format."""
        phone = self.cleaned_data.get('customer_phone')
        if phone:
            # Basic phone validation for Kenyan numbers
            import re
            if not re.match(r'^\+?254?\s?\d{3}\s?\d{3}\s?\d{4}$', phone):
                raise forms.ValidationError("Please enter a valid Kenyan phone number (e.g., +254 7XX XXX XXX)")
        return phone
    
    def clean_due_date(self):
        """Validate that due date is after issue date."""
        issue_date = self.cleaned_data.get('issue_date')
        due_date = self.cleaned_data.get('due_date')
        
        if issue_date and due_date and due_date < issue_date:
            raise forms.ValidationError("Due date must be after issue date.")
        
        return due_date
    
    def get_total_amount(self):
        """Calculate total amount including tax."""
        labor_cost = self.cleaned_data.get('labor_cost', 0)
        parts_cost = self.cleaned_data.get('parts_cost', 0)
        tax_rate = self.cleaned_data.get('tax_rate', 0)
        
        subtotal = labor_cost + parts_cost
        tax_amount = subtotal * (tax_rate / 100)
        total = subtotal + tax_amount
        
        return {
            'subtotal': subtotal,
            'tax_amount': tax_amount,
            'total': total
        }
    
    def get_spare_parts_list(self):
        """Parse spare parts into a list of dictionaries."""
        parts_text = self.cleaned_data.get('spare_parts', '')
        parts_list = []
        
        if parts_text:
            for line in parts_text.strip().split('\n'):
                if line.strip():
                    parts_list.append({'description': line.strip()})
        
        return parts_list


class QuickInvoiceForm(forms.Form):
    """
    Quick invoice form for generating invoices from existing bookings.
    Simplified version with pre-filled customer and service information.
    """
    
    # Pricing (editable)
    labor_cost = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '0.00',
            'step': '0.01'
        })
    )
    
    parts_cost = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '0.00',
            'step': '0.01'
        })
    )
    
    tax_rate = forms.DecimalField(
        max_digits=5,
        decimal_places=2,
        min_value=0,
        max_value=100,
        initial=16.0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '16.0',
            'step': '0.1'
        })
    )
    
    # Invoice Details
    invoice_number = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'INV-2026-001'
        })
    )

    issue_date = forms.DateField(
        initial=timezone.now().date(),
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )

    due_date = forms.DateField(
        initial=timezone.now().date() + timezone.timedelta(days=14),
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    payment_method = forms.ChoiceField(
        choices=InvoiceForm.PAYMENT_METHODS,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Additional notes or terms...'
        })
    )
    
    spare_parts = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'List spare parts (one per line):\nPart 1 - KSh 1500\nPart 2 - KSh 2000'
        })
    )
    
    def get_total_amount(self):
        """Calculate total amount including tax."""
        labor_cost = self.cleaned_data.get('labor_cost', 0)
        parts_cost = self.cleaned_data.get('parts_cost', 0)
        tax_rate = self.cleaned_data.get('tax_rate', 0)
        
        subtotal = labor_cost + parts_cost
        tax_amount = subtotal * (tax_rate / 100)
        total = subtotal + tax_amount
        
        return {
            'subtotal': subtotal,
            'tax_amount': tax_amount,
            'total': total
        }
    
    def get_spare_parts_list(self):
        """Parse spare parts into a list of dictionaries."""
        parts_text = self.cleaned_data.get('spare_parts', '')
        parts_list = []
        
        if parts_text:
            for line in parts_text.strip().split('\n'):
                if line.strip():
                    parts_list.append({'description': line.strip()})
        
        return parts_list