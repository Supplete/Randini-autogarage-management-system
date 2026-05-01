"""
utils.py — Randini Auto Garage M-Pesa Integration
=================================================
Utility functions for handling M-Pesa STK Push payments.

Functions:
    - get_access_token()    : Retrieves OAuth token from M-Pesa API
    - trigger_stk_push()   : Initiates STK Push payment request

Security Notes:
    - Uses sandbox environment for development
    - Production requires production credentials
    - Callback URL must be HTTPS and publicly accessible
"""

import requests
from requests.auth import HTTPBasicAuth
from datetime import datetime
import base64
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags

# M-Pesa Sandbox Credentials (Development Only)
# TODO: Replace with production credentials in production environment
MPESA_CONSUMER_KEY = "OLAhog5GAFrJV82zeGZGYKKYbhhx1jSnOHOt7k18j9WZeXzD"
MPESA_CONSUMER_SECRET = "5SQCUnY3LDsyO87V7PFGeCtGrKhqr2NBkUAFk2B8a4xBdZR4VQYNGzJFkF4X7qRC"
MPESA_API_URL = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
MPESA_STK_URL = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"

# M-Pesa Business Details (Sandbox)
MPESA_SHORTCODE = "174379"  # Test paybill number
MPESA_PASSKEY = "bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919"


def get_access_token():
    """
    Retrieves OAuth access token from M-Pesa API.
    
    This token is required for all subsequent M-Pesa API calls.
    The token has a 1-hour expiry and should be cached in production.
    
    Returns:
        str: OAuth access token or None if request fails
        
    Note:
        - Uses HTTP Basic Authentication with consumer key and secret
        - Token expires after 1 hour
        - In production, implement token caching to avoid repeated requests
    """
    try:
        # Make OAuth request to M-Pesa
        response = requests.get(
            MPESA_API_URL, 
            auth=HTTPBasicAuth(MPESA_CONSUMER_KEY, MPESA_CONSUMER_SECRET)
        )
        
        # Extract access token from response
        token_data = response.json()
        access_token = token_data.get('access_token')
        
        if access_token:
            print(f"✅ M-Pesa access token obtained successfully")
            return access_token
        else:
            print(f"❌ Failed to obtain M-Pesa access token: {token_data}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"❌ M-Pesa API request failed: {e}")
        return None
    except Exception as e:
        print(f"❌ Unexpected error getting M-Pesa token: {e}")
        return None


def trigger_stk_push(phone, amount):
    """
    Initiates M-Pesa STK Push payment request.
    
    This function sends a payment request to the customer's phone,
    prompting them to enter their M-Pesa PIN to complete the transaction.
    
    Args:
        phone (str): Customer phone number (format: +254XXXXXXXXX)
        amount (int/float): Payment amount in KES
        
    Returns:
        dict: M-Pesa API response containing:
            - ResponseCode: '0' for success, '1' for failure
            - CheckoutRequestID: Unique transaction identifier
            - CustomerMessage: Message to display to customer
            - errorMessage: Error details (if failed)
            
    Example:
        >>> result = trigger_stk_push("+254712345678", 1500)
        >>> if result['ResponseCode'] == '0':
        ...     print("Payment request sent successfully")
        
    Note:
        - Customer will receive STK push on their phone
        - They must enter M-Pesa PIN to complete payment
        - Callback URL receives payment confirmation
        - Use ngrok for development callback testing
    """
    try:
        # Step 1: Get OAuth access token
        access_token = get_access_token()
        if not access_token:
            return {'ResponseCode': '1', 'errorMessage': 'Failed to get access token'}
        
        # Step 2: Generate timestamp and password
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        password_string = MPESA_SHORTCODE + MPESA_PASSKEY + timestamp
        password = base64.b64encode(password_string.encode()).decode('utf-8')
        
        # Step 3: Get callback URL from settings
        # Uses ngrok URL in development, production domain in production
        callback_url = getattr(settings, 'MPESA_CALLBACK_URL', 'https://yourdomain.com/mpesa-callback/')
        
        # Step 4: Construct STK push payload
        payload = {
            "BusinessShortCode": MPESA_SHORTCODE,           # Paybill number
            "Password": password,                           # Generated password
            "Timestamp": timestamp,                         # Current timestamp
            "TransactionType": "CustomerPayBillOnline",    # Transaction type
            "Amount": amount,                               # Payment amount
            "PartyA": phone,                                # Customer phone (payer)
            "PartyB": MPESA_SHORTCODE,                     # Paybill number (receiver)
            "PhoneNumber": phone,                           # Phone to receive STK push
            "CallBackURL": callback_url,                    # URL for payment confirmation
            "AccountReference": "Randini Garage",           # Reference shown in M-Pesa
            "TransactionDesc": "Parts Payment"             # Transaction description
        }
        
        # Step 5: Send STK push request
        response = requests.post(
            MPESA_STK_URL,
            json=payload,
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        # Step 6: Process response
        response_data = response.json()
        
        # Log response for debugging
        print(f"📱 M-Pesa STK Push Response: {response_data}")
        
        # Step 7: Return response
        return response_data
        
    except requests.exceptions.RequestException as e:
        error_msg = f"M-Pesa API request failed: {e}"
        print(f"❌ {error_msg}")
        return {'ResponseCode': '1', 'errorMessage': error_msg}
        
    except Exception as e:
        error_msg = f"Unexpected error in STK push: {e}"
        print(f"❌ {error_msg}")
        return {'ResponseCode': '1', 'errorMessage': error_msg}


# ─────────────────────────────────────────────────────────────
# HELPER FUNCTIONS (For Future Enhancement)
# ─────────────────────────────────────────────────────────────

def validate_phone_number(phone):
    """
    Validates and formats Kenyan phone numbers.
    
    Args:
        phone (str): Phone number in any format
        
    Returns:
        str: Formatted phone number (+254XXXXXXXXX) or None if invalid
        
    Note:
        - Accepts formats: 07XXXXXXXX, +254XXXXXXXXX, 254XXXXXXXXX
        - Returns standardized format: +254XXXXXXXXX
    """
    # Remove all non-digit characters
    digits_only = ''.join(filter(str.isdigit, phone))
    
    # Validate length
    if len(digits_only) == 12 and digits_only.startswith('254'):
        return f"+{digits_only}"
    elif len(digits_only) == 10 and digits_only.startswith('07'):
        return f"+254{digits_only[1:]}"
    else:
        return None


def format_amount(amount):
    """
    Formats payment amount for M-Pesa API.
    
    Args:
        amount (int/float/str): Payment amount
        
    Returns:
        int: Formatted amount in KES
        
    Note:
        - M-Pesa requires amounts in whole numbers (KES)
        - Rounds down for decimal amounts
    """
    try:
        return int(float(amount))
    except (ValueError, TypeError):
        return 0


# ─────────────────────────────────────────────────────────────
# EMAIL UTILITY FUNCTIONS
# ─────────────────────────────────────────────────────────────

def send_service_invoice_email(booking, customer, spare_parts=None):
    """
    Sends service invoice email to customer after vehicle service completion.
    
    Args:
        booking: Booking object with service details
        customer: Customer object
        spare_parts: QuerySet of spare parts used (optional)
        
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        from django.utils import timezone
        from decimal import Decimal
        
        # Calculate invoice amounts
        subtotal = booking.price
        if spare_parts:
            for part in spare_parts:
                subtotal += part.product.price * part.quantity
        
        service_fee = Decimal('500.00')  # Service fee
        total_amount = subtotal + service_fee
        
        # Prepare context for template
        context = {
            'booking': booking,
            'customer': customer,
            'spare_parts': spare_parts,
            'invoice_date': timezone.now(),
            'subtotal': subtotal,
            'service_fee': service_fee,
            'total_amount': total_amount,
        }
        
        # Render HTML email
        html_content = render_to_string('email/service_invoice.html', context)
        text_content = strip_tags(html_content)
        
        # Send email
        send_mail(
            subject=f'Invoice for Vehicle Service - Randini Garage (INV-{booking.id:06d})',
            message=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[customer.email],
            html_message=html_content,
            fail_silently=False,
        )
        
        print(f"✅ Service invoice email sent to {customer.email}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to send service invoice email: {e}")
        return False


def send_spare_parts_confirmation_email(order, customer, order_items):
    """
    Sends order confirmation email to customer after spare parts purchase.
    
    Args:
        order: Order object
        customer: Customer object
        order_items: QuerySet of order items
        
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        from django.utils import timezone
        from decimal import Decimal
        
        # Calculate order amounts
        subtotal = sum(item.product.price * item.quantity for item in order_items)
        vat = subtotal * Decimal('0.16')  # 16% VAT
        total_amount = subtotal + vat
        
        # Set collection ready date (next business day)
        collection_date = timezone.now()
        if collection_date.weekday() >= 5:  # Weekend
            collection_date += timezone.timedelta(days=2)
        else:
            collection_date += timezone.timedelta(days=1)
        
        # Prepare context for template
        context = {
            'order': order,
            'customer': customer,
            'order_items': order_items,
            'order_date': timezone.now(),
            'collection_ready_date': collection_date,
            'subtotal': subtotal,
            'vat': vat,
            'total_amount': total_amount,
            'discount': Decimal('0.00'),  # Can be modified for promotions
        }
        
        # Render HTML email
        html_content = render_to_string('email/spare_parts_confirmation.html', context)
        text_content = strip_tags(html_content)
        
        # Send email
        send_mail(
            subject=f'Order Confirmation - Randini Garage (ORD-{order.id:06d})',
            message=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[customer.email],
            html_message=html_content,
            fail_silently=False,
        )
        
        print(f"✅ Spare parts confirmation email sent to {customer.email}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to send spare parts confirmation email: {e}")
        return False


def send_payment_reminder_email(booking, customer, days_overdue=0):
    """
    Sends payment reminder email to customer for unpaid service invoices.
    
    Args:
        booking: Booking object with service details
        customer: Customer object
        days_overdue: Number of days overdue (0 for first reminder)
        
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        from django.utils import timezone
        from decimal import Decimal
        
        # Calculate amounts
        subtotal = booking.service_cost
        service_fee = Decimal('500.00')
        total_amount = subtotal + service_fee
        
        # Determine reminder urgency
        if days_overdue == 0:
            subject = f'Payment Reminder - Randini Garage (INV-{booking.id:06d})'
            urgency_text = "This is a friendly reminder that your payment is due."
        elif days_overdue <= 3:
            subject = f'URGENT: Payment Overdue - Randini Garage (INV-{booking.id:06d})'
            urgency_text = f"Your payment is {days_overdue} days overdue. Please settle immediately."
        else:
            subject = f'FINAL NOTICE: Payment Overdue - Randini Garage (INV-{booking.id:06d})'
            urgency_text = f"Your payment is {days_overdue} days overdue. This is a final notice."
        
        # Create simple text email for reminders
        message = f"""
Dear {customer.user.get_full_name()},

{urgency_text}

Invoice Details:
- Invoice Number: INV-{booking.id:06d}
- Service: {booking.service_type}
- Vehicle: {booking.vehicle_make} {booking.vehicle_model} ({booking.vehicle_year})
- Total Amount Due: KSh {total_amount:.2f}
- Due Date: {booking.created_at + timezone.timedelta(days=7):date:'F d, Y'}

Payment Methods:
- M-Pesa: +254 711962088 (Business Number: 123456)
- Bank Transfer: Randini Auto Garage, Account: 0123456789, Equity Bank
- Cash: Visit our garage in Bungoma

Please complete your payment as soon as possible to avoid any service interruptions.

Thank you for your business!

Randini Auto Garage
Bungoma, Kenya
+254 711962088
randinigarage@gmail.com
        """
        
        # Send email
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[customer.email],
            fail_silently=False,
        )
        
        print(f"✅ Payment reminder email sent to {customer.email}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to send payment reminder email: {e}")
        return False


def send_otp_email(email, otp_code, first_name=None):
    """
    Send OTP verification email to user
    
    Args:
        email (str): User's email address
        otp_code (str): OTP code to send
        first_name (str, optional): User's first name for personalization
    
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        # Prepare email context
        context = {
            'otp_code': otp_code,
            'first_name': first_name or 'User',
            'company_name': 'Randini Garage',
            'support_email': 'randinigarage@gmail.com',
        }
        
        # Create simple text email for OTP
        message = f"""
Dear {first_name or 'User'},

Your OTP verification code for {context['company_name']} is: {otp_code}

This code will expire in 10 minutes.

If you didn't request this code, please ignore this email.

Best regards,
{context['company_name']} Team
{context['support_email']}
        """
        
        # Send email
        send_mail(
            subject=f'OTP Verification - {context["company_name"]}',
            message=message.strip(),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )
        
        print(f"✅ OTP email sent successfully to {email}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to send OTP email to {email}: {str(e)}")
        return False


def send_welcome_email(customer):
    """
    Sends welcome email to new customer after registration.
    
    Args:
        customer: Customer object with user details
        
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        from django.utils import timezone
        
        # Prepare context for template
        context = {
            'customer': customer,
            'registration_date': timezone.now(),
        }
        
        # Render HTML email
        html_content = render_to_string('email/welcome_customer.html', context)
        text_content = strip_tags(html_content)
        
        # Send email
        send_mail(
            subject=f'Welcome to Randini Auto Garage! - {customer.user.get_full_name()}',
            message=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[customer.user.email],
            html_message=html_content,
            fail_silently=False,
        )
        
        print(f"✅ Welcome email sent to {customer.email}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to send welcome email: {e}")
        return False


def trigger_mpesa_payment(phone, amount, reference="Service Payment"):
    """
    Triggers M-Pesa STK push for payment.
    
    Args:
        phone (str): Customer phone number
        amount (float): Payment amount
        reference (str): Payment reference description
        
    Returns:
        dict: M-Pesa API response
    """
    try:
        # Validate and format phone number
        formatted_phone = validate_phone_number(phone)
        if not formatted_phone:
            return {'ResponseCode': '1', 'errorMessage': 'Invalid phone number'}
        
        # Format amount
        formatted_amount = format_amount(amount)
        if formatted_amount <= 0:
            return {'ResponseCode': '1', 'errorMessage': 'Invalid amount'}
        
        # Update transaction description
        original_desc = "Parts Payment"
        # This would require modifying the trigger_stk_push function to accept custom description
        # For now, we'll use the existing function
        
        # Trigger STK push
        result = trigger_stk_push(formatted_phone, formatted_amount)
        
        if result.get('ResponseCode') == '0':
            print(f"✅ M-Pesa payment request sent to {formatted_phone} for KSh {formatted_amount}")
        else:
            print(f"❌ M-Pesa payment request failed: {result}")
        
        return result
        
    except Exception as e:
        error_msg = f"Error triggering M-Pesa payment: {e}"
        print(f"❌ {error_msg}")
        return {'ResponseCode': '1', 'errorMessage': error_msg}