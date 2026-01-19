from django.test import TestCase, Client
from django.urls import reverse
from .models import MarketplaceItem

class ItemListViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse('marketplace:item_list') # Assuming app_name='marketplace' and path name='item_list'

    def test_marketplace_heading_default(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['heading'], 'Marketplace')

    def test_marketplace_heading_mock_test(self):
        # 'MOCK_TEST' is the value, 'Mock Test' is the label -> heading plural 'Mock Tests'
        response = self.client.get(self.url, {'type': 'MOCK_TEST'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['heading'], 'Mock Tests')

    def test_marketplace_heading_multiple_types(self):
        # If multiple types selected, fallback to default
        response = self.client.get(self.url, {'type': ['MOCK_TEST', 'VIDEO_COURSE']})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['heading'], 'Marketplace')

    def test_marketplace_heading_invalid_type(self):
        # If invalid type, fallback to default
        response = self.client.get(self.url, {'type': 'INVALID_TYPE'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['heading'], 'Marketplace')
