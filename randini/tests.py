from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from .models import Customer, Booking, Order, SparePart, ContactMessage
import json


class CustomerViewsTestCase(TestCase):
    """Test customer-facing views and functionality"""
    
    def setUp(self):
        self.client = Client()
        # Create test user
        self.user = User.objects.create_user(
            username='testuser@example.com',
            email='testuser@example.com',
            first_name='Test',
            last_name='User',
            password='testpass123'
        )
        # Create customer profile
        self.customer = Customer.objects.create(
            user=self.user,
            phone_number='+254712345678'
        )
        # Create test spare part
        self.spare_part = SparePart.objects.create(
            name='Test Brake Pad',
            description='High quality brake pads',
            price=1500.00,
            stock=10
        )
    
    def test_home_page_loads(self):
        """Test that home page loads successfully"""
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Expert Auto Care')
    
    def test_services_page_loads(self):
        """Test that services page loads successfully"""
        response = self.client.get(reverse('services'))
        self.assertEqual(response.status_code, 200)
    
    def test_spareparts_page_loads(self):
        """Test that spare parts page loads successfully"""
        self.client.login(username='testuser@example.com', password='testpass123')
        response = self.client.get(reverse('spareparts'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Brake Pad')
    
    def test_contact_form_submission(self):
        """Test contact form submission"""
        self.client.login(username='testuser@example.com', password='testpass123')
        response = self.client.post(reverse('contact'), {
            'name': 'Test User',
            'email': 'test@example.com',
            'phone': '+254712345678',
            'subject': 'Test Subject',
            'message': 'This is a test message with sufficient length.'
        })
        self.assertEqual(response.status_code, 302)  # Redirect after success
        self.assertTrue(ContactMessage.objects.filter(subject='Test Subject').exists())
    
    def test_booking_form_submission(self):
        """Test booking form submission"""
        self.client.login(username='testuser@example.com', password='testpass123')
        from django.utils import timezone
        from datetime import timedelta
        future_time = timezone.now() + timedelta(days=7)
        
        response = self.client.post(reverse('booking'), {
            'full_name': 'Test User',
            'email': 'test@example.com',
            'phone': '254712345678',
            'location': 'Nairobi',
            'preferred_time': future_time.strftime('%Y-%m-%d %H:%M:%S'),
            'vehicle_type': 'sedan',
            'service_type': 'diagnostic'
        })
        self.assertEqual(response.status_code, 302)  # Redirect after success
        self.assertTrue(Booking.objects.filter(user=self.user).exists())
    
    def test_cart_functionality(self):
        """Test cart add/remove functionality"""
        self.client.login(username='testuser@example.com', password='testpass123')
        
        # Add to cart
        response = self.client.get(reverse('add_to_cart', args=[self.spare_part.id]))
        self.assertEqual(response.status_code, 302)
        
        # Check cart page
        response = self.client.get(reverse('cart'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Brake Pad')
        
        # Remove from cart
        response = self.client.get(reverse('remove_from_cart', args=[self.spare_part.id]))
        self.assertEqual(response.status_code, 302)


class ModelTestCase(TestCase):
    """Test model functionality and validation"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser@example.com',
            email='testuser@example.com',
            first_name='Test',
            last_name='User',
            password='testpass123'
        )
    
    def test_customer_creation(self):
        """Test customer model creation"""
        customer = Customer.objects.create(
            user=self.user,
            phone_number='+254712345678'
        )
        self.assertEqual(str(customer), f'{self.user.first_name} {self.user.last_name}'.strip() or self.user.username)
    
    def test_spare_part_creation(self):
        """Test spare part model creation"""
        part = SparePart.objects.create(
            name='Test Part',
            description='Test description',
            price=1000.00,
            stock=5
        )
        self.assertEqual(str(part), 'Test Part (Ksh 1000.0)')
        self.assertEqual(part.stock, 5)
    
    def test_order_creation(self):
        """Test order model creation"""
        customer = Customer.objects.create(
            user=self.user,
            phone_number='+254712345678'
        )
        order = Order.objects.create(
            user=self.user,
            full_name='Test User',
            email='test@example.com',
            phone_number='+254712345678',
            address='Test Address',
            city='Nairobi',
            total_amount=1000.00,
            payment_method='cash',
            status='Pending'
        )
        self.assertEqual(str(order), f'Order #{order.id} by Test User')
        self.assertEqual(order.status, 'Pending')


class MpesaIntegrationTestCase(TestCase):
    """Test M-Pesa integration functionality"""
    
    def test_mpesa_callback_view(self):
        """Test M-Pesa callback view handles requests"""
        # Test successful callback
        callback_data = {
            'Body': {
                'stkCallback': {
                    'ResultCode': 0,
                    'CheckoutRequestID': 'test_checkout_id',
                    'CallbackMetadata': {
                        'Item': [
                            {'Name': 'MpesaReceiptNumber', 'Value': 'TEST123'},
                            {'Name': 'PhoneNumber', 'Value': '+254712345678'},
                            {'Name': 'Amount', 'Value': 1000}
                        ]
                    }
                }
            }
        }
        
        response = self.client.post(
            reverse('mpesa_callback'),
            data=json.dumps(callback_data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        
        # Test failed callback
        callback_data['Body']['stkCallback']['ResultCode'] = 1
        response = self.client.post(
            reverse('mpesa_callback'),
            data=json.dumps(callback_data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)


class FormValidationTestCase(TestCase):
    """Test form validation"""
    
    def test_contact_form_validation(self):
        """Test contact form validation"""
        from .forms import ContactForm
        
        # Test valid data
        form_data = {
            'name': 'Test User',
            'email': 'test@example.com',
            'phone': '+254712345678',
            'subject': 'Test Subject',
            'message': 'This is a test message with sufficient length.'
        }
        form = ContactForm(data=form_data)
        self.assertTrue(form.is_valid())
        
        # Test invalid email
        form_data['email'] = 'invalid-email'
        form = ContactForm(data=form_data)
        self.assertFalse(form.is_valid())
        
        # Test short message
        form_data['email'] = 'test@example.com'
        form_data['message'] = 'Short'
        form = ContactForm(data=form_data)
        self.assertFalse(form.is_valid())
