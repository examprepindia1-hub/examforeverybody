import requests
import json
from django.conf import settings
from requests.auth import HTTPBasicAuth

class PayPalClient:
    def __init__(self):
        self.client_id = settings.PAYPAL_CLIENT_ID
        self.client_secret = settings.PAYPAL_SECRET
        self.environment = settings.PAYPAL_MODE # 'sandbox' or 'live'
        
        if self.environment == 'live':
            self.base_url = "https://api-m.paypal.com"
        else:
            self.base_url = "https://api-m.sandbox.paypal.com"

    def get_access_token(self):
        """Generates a new access token from PayPal"""
        url = f"{self.base_url}/v1/oauth2/token"
        headers = {
            "Accept": "application/json",
            "Accept-Language": "en_US",
        }
        data = {"grant_type": "client_credentials"}
        
        response = requests.post(
            url, 
            auth=HTTPBasicAuth(self.client_id, self.client_secret), 
            headers=headers, 
            data=data
        )
        
        if response.status_code == 200:
            return response.json()['access_token']
        raise Exception(f"Failed to get access token: {response.text}")

    def create_order(self, amount, currency="USD"):
        """Creates an order in PayPal system"""
        access_token = self.get_access_token()
        url = f"{self.base_url}/v2/checkout/orders"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}",
        }
        
        payload = {
            "intent": "CAPTURE",
            "purchase_units": [{
                "amount": {
                    "currency_code": currency,
                    "value": str(amount)
                }
            }]
        }
        
        response = requests.post(url, headers=headers, json=payload)
        return response.json()

    def capture_order(self, order_id):
        """Captures payment for an order"""
        access_token = self.get_access_token()
        url = f"{self.base_url}/v2/checkout/orders/{order_id}/capture"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}",
        }
        
        response = requests.post(url, headers=headers)
        return response.json()