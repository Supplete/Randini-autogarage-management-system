import requests
from requests.auth import HTTPBasicAuth
from datetime import datetime
import base64

def get_access_token():
    # Standard Sandbox Credentials
    consumer_key = "OLAhog5GAFrJV82zeGZGYKKYbhhx1jSnOHOt7k18j9WZeXzD"
    consumer_secret = "5SQCUnY3LDsyO87V7PFGeCtGrKhqr2NBkUAFk2B8a4xBdZR4VQYNGzJFkF4X7qRC"
    api_URL = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
    
    r = requests.get(api_URL, auth=HTTPBasicAuth(consumer_key, consumer_secret))
    return r.json().get('access_token')

def trigger_stk_push(phone, amount):
    access_token = get_access_token()
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    
    shortcode = "174379"
    passkey = "bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919"
    
    password = base64.b64encode((shortcode + passkey + timestamp).encode()).decode('utf-8')

    payload = {
        "BusinessShortCode": shortcode,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": amount,
        "PartyA": phone,
        "PartyB": shortcode,
        "PhoneNumber": phone,
        "CallBackURL": "https://mydomain.com/callback", # Replace with your live URL later
        "AccountReference": "Randini Garage",
        "TransactionDesc": "Parts Payment"
    }
    
    response = requests.post(
        "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest",
        json=payload,
        headers={"Authorization": f"Bearer {access_token}"}
    )
    return response.json()