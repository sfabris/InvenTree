"""
Unit testing for the Stock API
"""

# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import datetime, timedelta

from rest_framework import status
from django.urls import reverse

from InvenTree.status_codes import StockStatus
from InvenTree.api_tester import InvenTreeAPITestCase

from common.models import InvenTreeSetting

from .models import StockItem, StockLocation


class StockAPITestCase(InvenTreeAPITestCase):

    fixtures = [
        'category',
        'part',
        'company',
        'location',
        'supplier_part',
        'stock',
        'stock_tests',
    ]

    roles = [
        'stock.change',
        'stock.add',
        'stock_location.change',
        'stock_location.add',
    ]

    def setUp(self):

        super().setUp()


class StockLocationTest(StockAPITestCase):
    """
    Series of API tests for the StockLocation API
    """
    list_url = reverse('api-location-list')

    def setUp(self):
        super().setUp()

        # Add some stock locations
        StockLocation.objects.create(name='top', description='top category')

    def test_list(self):
        # Check that we can request the StockLocation list
        response = self.client.get(self.list_url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)

    def test_add(self):
        # Check that we can add a new StockLocation
        data = {
            'parent': 1,
            'name': 'Location',
            'description': 'Another location for stock'
        }
        response = self.client.post(self.list_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


class StockItemListTest(StockAPITestCase):
    """
    Tests for the StockItem API LIST endpoint
    """

    list_url = reverse('api-stock-list')

    def get_stock(self, **kwargs):
        """
        Filter stock and return JSON object
        """

        response = self.client.get(self.list_url, format='json', data=kwargs)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Return JSON-ified data
        return response.data

    def test_get_stock_list(self):
        """
        List *all* StockItem objects.
        """

        response = self.get_stock()

        self.assertEqual(len(response), 20)

    def test_filter_by_part(self):
        """
        Filter StockItem by Part reference
        """

        response = self.get_stock(part=25)

        self.assertEqual(len(response), 8)

        response = self.get_stock(part=10004)

        self.assertEqual(len(response), 12)

    def test_filter_by_IPN(self):
        """
        Filter StockItem by IPN reference
        """

        response = self.get_stock(IPN="R.CH")
        self.assertEqual(len(response), 3)

    def test_filter_by_location(self):
        """
        Filter StockItem by StockLocation reference
        """

        response = self.get_stock(location=5)
        self.assertEqual(len(response), 1)

        response = self.get_stock(location=1, cascade=0)
        self.assertEqual(len(response), 0)

        response = self.get_stock(location=1, cascade=1)
        self.assertEqual(len(response), 2)

        response = self.get_stock(location=7)
        self.assertEqual(len(response), 16)

    def test_filter_by_depleted(self):
        """
        Filter StockItem by depleted status
        """

        response = self.get_stock(depleted=1)
        self.assertEqual(len(response), 1)

        response = self.get_stock(depleted=0)
        self.assertEqual(len(response), 19)

    def test_filter_by_in_stock(self):
        """
        Filter StockItem by 'in stock' status
        """

        response = self.get_stock(in_stock=1)
        self.assertEqual(len(response), 17)

        response = self.get_stock(in_stock=0)
        self.assertEqual(len(response), 3)

    def test_filter_by_status(self):
        """
        Filter StockItem by 'status' field
        """

        codes = {
            StockStatus.OK: 18,
            StockStatus.DESTROYED: 1,
            StockStatus.LOST: 1,
            StockStatus.DAMAGED: 0,
            StockStatus.REJECTED: 0,
        }

        for code in codes.keys():
            num = codes[code]

            response = self.get_stock(status=code)
            self.assertEqual(len(response), num)

    def test_filter_by_batch(self):
        """
        Filter StockItem by batch code
        """

        response = self.get_stock(batch='B123')
        self.assertEqual(len(response), 1)

    def test_filter_by_serialized(self):
        """
        Filter StockItem by serialized status
        """

        response = self.get_stock(serialized=1)
        self.assertEqual(len(response), 12)

        for item in response:
            self.assertIsNotNone(item['serial'])

        response = self.get_stock(serialized=0)
        self.assertEqual(len(response), 8)

        for item in response:
            self.assertIsNone(item['serial'])

    def test_filter_by_expired(self):
        """
        Filter StockItem by expiry status
        """

        # First, we can assume that the 'stock expiry' feature is disabled
        response = self.get_stock(expired=1)
        self.assertEqual(len(response), 20)

        self.user.is_staff = True
        self.user.save()

        # Now, ensure that the expiry date feature is enabled!
        InvenTreeSetting.set_setting('STOCK_ENABLE_EXPIRY', True, self.user)

        response = self.get_stock(expired=1)
        self.assertEqual(len(response), 1)

        for item in response:
            self.assertTrue(item['expired'])

        response = self.get_stock(expired=0)
        self.assertEqual(len(response), 19)

        for item in response:
            self.assertFalse(item['expired'])

        # Mark some other stock items as expired
        today = datetime.now().date()

        for pk in [510, 511, 512]:
            item = StockItem.objects.get(pk=pk)
            item.expiry_date = today - timedelta(days=pk)
            item.save()

        response = self.get_stock(expired=1)
        self.assertEqual(len(response), 4)

        response = self.get_stock(expired=0)
        self.assertEqual(len(response), 16)

    def test_paginate(self):
        """
        Test that we can paginate results correctly
        """

        for n in [1, 5, 10]:
            response = self.get_stock(limit=n)

            self.assertIn('count', response)
            self.assertIn('results', response)

            self.assertEqual(len(response['results']), n)


class StockItemTest(StockAPITestCase):
    """
    Series of API tests for the StockItem API
    """

    list_url = reverse('api-stock-list')

    def detail_url(self, pk):
        return reverse('api-stock-detail', kwargs={'pk': pk})

    def setUp(self):
        super().setUp()
        # Create some stock locations
        top = StockLocation.objects.create(name='A', description='top')

        StockLocation.objects.create(name='B', description='location b', parent=top)
        StockLocation.objects.create(name='C', description='location c', parent=top)

    def test_create_default_location(self):
        """
        Test the default location functionality,
        if a 'location' is not specified in the creation request.
        """

        # The part 'R_4K7_0603' (pk=4) has a default location specified

        response = self.client.post(
            self.list_url,
            data={
                'part': 4,
                'quantity': 10
            }
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['location'], 2)

        # What if we explicitly set the location to a different value?

        response = self.client.post(
            self.list_url,
            data={
                'part': 4,
                'quantity': 20,
                'location': 1,
            }
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['location'], 1)

        # And finally, what if we set the location explicitly to None?

        response = self.client.post(
            self.list_url,
            data={
                'part': 4,
                'quantity': 20,
                'location': '',
            }
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['location'], None)

    def test_stock_item_create(self):
        """
        Test creation of a StockItem via the API
        """

        # POST with an empty part reference

        response = self.client.post(
            self.list_url,
            data={
                'quantity': 10,
                'location': 1
            }
        )

        self.assertContains(response, 'This field is required', status_code=status.HTTP_400_BAD_REQUEST)

        # POST with an invalid part reference

        response = self.client.post(
            self.list_url,
            data={
                'quantity': 10,
                'location': 1,
                'part': 10000000,
            }
        )

        self.assertContains(response, 'does not exist', status_code=status.HTTP_400_BAD_REQUEST)

        # POST without quantity
        response = self.client.post(
            self.list_url,
            data={
                'part': 1,
                'location': 1,
            }
        )

        self.assertContains(response, 'This field is required', status_code=status.HTTP_400_BAD_REQUEST)

        # POST with quantity and part and location
        response = self.client.post(
            self.list_url,
            data={
                'part': 1,
                'location': 1,
                'quantity': 10,
            }
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_default_expiry(self):
        """
        Test that the "default_expiry" functionality works via the API.

        - If an expiry_date is specified, use that
        - Otherwise, check if the referenced part has a default_expiry defined
            - If so, use that!
            - Otherwise, no expiry

        Notes:
            - Part <25> has a default_expiry of 10 days

        """

        # First test - create a new StockItem without an expiry date
        data = {
            'part': 4,
            'quantity': 10,
        }

        response = self.client.post(self.list_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertIsNone(response.data['expiry_date'])

        # Second test - create a new StockItem with an explicit expiry date
        data['expiry_date'] = '2022-12-12'

        response = self.client.post(self.list_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertIsNotNone(response.data['expiry_date'])
        self.assertEqual(response.data['expiry_date'], '2022-12-12')

        # Third test - create a new StockItem for a Part which has a default expiry time
        data = {
            'part': 25,
            'quantity': 10
        }

        response = self.client.post(self.list_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Expected expiry date is 10 days in the future
        expiry = datetime.now().date() + timedelta(10)

        self.assertEqual(response.data['expiry_date'], expiry.isoformat())


class StocktakeTest(StockAPITestCase):
    """
    Series of tests for the Stocktake API
    """

    def test_action(self):
        """
        Test each stocktake action endpoint,
        for validation
        """

        for endpoint in ['api-stock-count', 'api-stock-add', 'api-stock-remove']:

            url = reverse(endpoint)

            data = {}

            # POST with a valid action
            response = self.post(url, data)
            self.assertContains(response, "must contain list", status_code=status.HTTP_400_BAD_REQUEST)

            data['items'] = [{
                'no': 'aa'
            }]

            # POST without a PK
            response = self.post(url, data)
            self.assertContains(response, 'must contain a valid pk', status_code=status.HTTP_400_BAD_REQUEST)

            # POST with a PK but no quantity
            data['items'] = [{
                'pk': 10
            }]

            response = self.post(url, data)
            self.assertContains(response, 'must contain a valid pk', status_code=status.HTTP_400_BAD_REQUEST)

            data['items'] = [{
                'pk': 1234
            }]

            response = self.post(url, data)
            self.assertContains(response, 'must contain a valid quantity', status_code=status.HTTP_400_BAD_REQUEST)

            data['items'] = [{
                'pk': 1234,
                'quantity': '10x0d'
            }]

            response = self.post(url, data)
            self.assertContains(response, 'must contain a valid quantity', status_code=status.HTTP_400_BAD_REQUEST)

            data['items'] = [{
                'pk': 1234,
                'quantity': "-1.234"
            }]

            response = self.post(url, data)
            self.assertContains(response, 'must not be less than zero', status_code=status.HTTP_400_BAD_REQUEST)

            # Test with a single item
            data = {
                'item': {
                    'pk': 1234,
                    'quantity': '10',
                }
            }

            response = self.post(url, data)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_transfer(self):
        """
        Test stock transfers
        """

        data = {
            'item': {
                'pk': 1234,
                'quantity': 10,
            },
            'location': 1,
            'notes': "Moving to a new location"
        }

        url = reverse('api-stock-transfer')

        response = self.post(url, data)
        self.assertContains(response, "Moved 1 parts to", status_code=status.HTTP_200_OK)

        # Now try one which will fail due to a bad location
        data['location'] = 'not a location'

        response = self.post(url, data)
        self.assertContains(response, 'Valid location must be specified', status_code=status.HTTP_400_BAD_REQUEST)


class StockTestResultTest(StockAPITestCase):

    def get_url(self):
        return reverse('api-stock-test-result-list')

    def test_list(self):

        url = self.get_url()
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 4)

        response = self.client.get(url, data={'stock_item': 105})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 4)

    def test_post_fail(self):
        # Attempt to post a new test result without specifying required data

        url = self.get_url()

        response = self.client.post(
            url,
            data={
                'test': 'A test',
                'result': True,
            },
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # This one should pass!
        response = self.client.post(
            url,
            data={
                'test': 'A test',
                'stock_item': 105,
                'result': True,
            },
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_post(self):
        # Test creation of a new test result

        url = self.get_url()

        response = self.client.get(url)
        n = len(response.data)

        data = {
            'stock_item': 105,
            'test': 'Checked Steam Valve',
            'result': False,
            'value': '150kPa',
            'notes': 'I guess there was just too much pressure?',
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        response = self.client.get(url)
        self.assertEqual(len(response.data), n + 1)

        # And read out again
        response = self.client.get(url, data={'test': 'Checked Steam Valve'})

        self.assertEqual(len(response.data), 1)

        test = response.data[0]
        self.assertEqual(test['value'], '150kPa')
        self.assertEqual(test['user'], self.user.pk)
