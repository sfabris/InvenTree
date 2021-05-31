""" Unit tests for Stock views (see views.py) """

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from common.models import InvenTreeSetting

import json
from datetime import datetime, timedelta

from InvenTree.status_codes import StockStatus


class StockViewTestCase(TestCase):

    fixtures = [
        'category',
        'part',
        'company',
        'location',
        'supplier_part',
        'stock',
    ]

    def setUp(self):
        super().setUp()

        # Create a user
        user = get_user_model()

        self.user = user.objects.create_user(
            username='username',
            email='user@email.com',
            password='password'
        )

        self.user.is_staff = True
        self.user.save()

        # Put the user into a group with the correct permissions
        group = Group.objects.create(name='mygroup')
        self.user.groups.add(group)

        # Give the group *all* the permissions!
        for rule in group.rule_sets.all():
            rule.can_view = True
            rule.can_change = True
            rule.can_add = True
            rule.can_delete = True

            rule.save()

        self.client.login(username='username', password='password')


class StockListTest(StockViewTestCase):
    """ Tests for Stock list views """

    def test_stock_index(self):
        response = self.client.get(reverse('stock-index'))
        self.assertEqual(response.status_code, 200)


class StockLocationTest(StockViewTestCase):
    """ Tests for StockLocation views """

    def test_location_edit(self):
        response = self.client.get(reverse('stock-location-edit', args=(1,)), HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)

    def test_qr_code(self):
        # Request the StockLocation QR view
        response = self.client.get(reverse('stock-location-qr', args=(1,)), HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)

        # Test for an invalid StockLocation
        response = self.client.get(reverse('stock-location-qr', args=(999,)), HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)

    def test_create(self):
        # Test StockLocation creation view
        response = self.client.get(reverse('stock-location-create'), HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)

        # Create with a parent
        response = self.client.get(reverse('stock-location-create'), {'location': 1}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)

        # Create with an invalid parent
        response = self.client.get(reverse('stock-location-create'), {'location': 999}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)


class StockItemTest(StockViewTestCase):
    """" Tests for StockItem views """

    def test_qr_code(self):
        # QR code for a valid item
        response = self.client.get(reverse('stock-item-qr', args=(1,)), HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)

        # QR code for an invalid item
        response = self.client.get(reverse('stock-item-qr', args=(9999,)), HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)

    def test_adjust_items(self):
        url = reverse('stock-adjust')

        # Move items
        response = self.client.get(url, {'stock[]': [1, 2, 3, 4, 5], 'action': 'move'}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)

        # Count part
        response = self.client.get(url, {'part': 1}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)

        # Remove items
        response = self.client.get(url, {'location': 1, 'action': 'take'}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)

        # Add items
        response = self.client.get(url, {'item': 1, 'action': 'add'}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)

        # Blank response
        response = self.client.get(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)

        # TODO - Tests for POST data

    def test_edit_item(self):
        # Test edit view for StockItem
        response = self.client.get(reverse('stock-item-edit', args=(1,)), HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)

        # Test with a non-purchaseable part
        response = self.client.get(reverse('stock-item-edit', args=(100,)), HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)

    def test_create_item(self):
        """
        Test creation of StockItem
        """

        url = reverse('stock-item-create')

        response = self.client.get(url, {'part': 1}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)

        response = self.client.get(url, {'part': 999}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)

        # Copy from a valid item, valid location
        response = self.client.get(url, {'location': 1, 'copy': 1}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)

        # Copy from an invalid item, invalid location
        response = self.client.get(url, {'location': 999, 'copy': 9999}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)

    def test_create_stock_with_expiry(self):
        """
        Test creation of stock item of a part with an expiry date.
        The initial value for the "expiry_date" field should be pre-filled,
        and should be in the future!
        """

        # First, ensure that the expiry date feature is enabled!
        InvenTreeSetting.set_setting('STOCK_ENABLE_EXPIRY', True, self.user)

        url = reverse('stock-item-create')

        response = self.client.get(url, {'part': 25}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        self.assertEqual(response.status_code, 200)

        # We are expecting 10 days in the future
        expiry = datetime.now().date() + timedelta(10)

        expected = f'name=\\\\"expiry_date\\\\" value=\\\\"{expiry.isoformat()}\\\\"'

        self.assertIn(expected, str(response.content))

        # Now check with a part which does *not* have a default expiry period
        response = self.client.get(url, {'part': 1}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        expected = 'name=\\\\"expiry_date\\\\" placeholder=\\\\"\\\\"'

        self.assertIn(expected, str(response.content))

    def test_serialize_item(self):
        # Test the serialization view

        url = reverse('stock-item-serialize', args=(100,))

        # GET the form
        response = self.client.get(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)

        data_valid = {
            'quantity': 5,
            'serial_numbers': '1-5',
            'destination': 4,
            'notes': 'Serializing stock test'
        }

        data_invalid = {
            'quantity': 4,
            'serial_numbers': 'dd-23-adf',
            'destination': 'blorg'
        }

        # POST
        response = self.client.post(url, data_valid, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['form_valid'])

        # Try again to serialize with the same numbers
        response = self.client.post(url, data_valid, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertFalse(data['form_valid'])

        # POST with invalid data
        response = self.client.post(url, data_invalid, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertFalse(data['form_valid'])


class StockOwnershipTest(StockViewTestCase):
    """ Tests for stock ownership views """

    def setUp(self):
        """ Add another user for ownership tests """

        super().setUp()

        # Promote existing user with staff, admin and superuser statuses
        self.user.is_staff = True
        self.user.is_admin = True
        self.user.is_superuser = True
        self.user.save()

        # Create a new user
        user = get_user_model()

        self.new_user = user.objects.create_user(
            username='john',
            email='john@email.com',
            password='custom123',
        )

        # Put the user into a new group with the correct permissions
        group = Group.objects.create(name='new_group')
        self.new_user.groups.add(group)

        # Give the group *all* the permissions!
        for rule in group.rule_sets.all():
            rule.can_view = True
            rule.can_change = True
            rule.can_add = True
            rule.can_delete = True

            rule.save()

    def enable_ownership(self):
        # Enable stock location ownership

        InvenTreeSetting.set_setting('STOCK_OWNERSHIP_CONTROL', True, self.user)
        self.assertEqual(True, InvenTreeSetting.get_setting('STOCK_OWNERSHIP_CONTROL'))

    def test_owner_control(self):
        # Test stock location and item ownership
        from .models import StockLocation, StockItem
        from users.models import Owner

        user_group = self.user.groups.all()[0]
        user_group_owner = Owner.get_owner(user_group)
        new_user_group = self.new_user.groups.all()[0]
        new_user_group_owner = Owner.get_owner(new_user_group)

        user_as_owner = Owner.get_owner(self.user)
        new_user_as_owner = Owner.get_owner(self.new_user)

        test_location_id = 4
        test_item_id = 11

        # Enable ownership control
        self.enable_ownership()

        # Set ownership on existing location
        response = self.client.post(reverse('stock-location-edit', args=(test_location_id,)),
                                    {'name': 'Office', 'owner': user_group_owner.pk},
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertContains(response, '"form_valid": true', status_code=200)

        # Set ownership on existing item (and change location)
        response = self.client.post(reverse('stock-item-edit', args=(test_item_id,)),
                                    {'part': 1, 'status': StockStatus.OK, 'owner': user_as_owner.pk},
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertContains(response, '"form_valid": true', status_code=200)

        # Logout
        self.client.logout()

        # Login with new user
        self.client.login(username='john', password='custom123')

        # Test location edit
        response = self.client.post(reverse('stock-location-edit', args=(test_location_id,)),
                                    {'name': 'Office', 'owner': new_user_group_owner.pk},
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        # Make sure the location's owner is unchanged
        location = StockLocation.objects.get(pk=test_location_id)
        self.assertEqual(location.owner, user_group_owner)

        # Test item edit
        response = self.client.post(reverse('stock-item-edit', args=(test_item_id,)),
                                    {'part': 1, 'status': StockStatus.OK, 'owner': new_user_as_owner.pk},
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        # Make sure the item's owner is unchanged
        item = StockItem.objects.get(pk=test_item_id)
        self.assertEqual(item.owner, user_as_owner)

        # Create new parent location
        parent_location = {
            'name': 'John Desk',
            'description': 'John\'s desk',
            'owner': new_user_group_owner.pk,
        }

        # Create new parent location
        response = self.client.post(reverse('stock-location-create'),
                                    parent_location, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertContains(response, '"form_valid": true', status_code=200)

        # Retrieve created location
        parent_location = StockLocation.objects.get(name=parent_location['name'])

        # Create new child location
        new_location = {
            'name': 'Upper Left Drawer',
            'description': 'John\'s desk - Upper left drawer',
        }

        # Try to create new location with neither parent or owner
        response = self.client.post(reverse('stock-location-create'),
                                    new_location, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertContains(response, '"form_valid": false', status_code=200)

        # Try to create new location with invalid owner
        new_location['parent'] = parent_location.id
        new_location['owner'] = user_group_owner.pk
        response = self.client.post(reverse('stock-location-create'),
                                    new_location, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertContains(response, '"form_valid": false', status_code=200)

        # Try to create new location with valid owner
        new_location['owner'] = new_user_group_owner.pk
        response = self.client.post(reverse('stock-location-create'),
                                    new_location, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertContains(response, '"form_valid": true', status_code=200)

        # Retrieve created location
        location_created = StockLocation.objects.get(name=new_location['name'])

        # Create new item
        new_item = {
            'part': 25,
            'location': location_created.pk,
            'quantity': 123,
            'status': StockStatus.OK,
        }

        # Try to create new item with no owner
        response = self.client.post(reverse('stock-item-create'),
                                    new_item, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertContains(response, '"form_valid": false', status_code=200)

        # Try to create new item with invalid owner
        new_item['owner'] = user_as_owner.pk
        response = self.client.post(reverse('stock-item-create'),
                                    new_item, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertContains(response, '"form_valid": false', status_code=200)

        # Try to create new item with valid owner
        new_item['owner'] = new_user_as_owner.pk
        response = self.client.post(reverse('stock-item-create'),
                                    new_item, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertContains(response, '"form_valid": true', status_code=200)

        # Logout
        self.client.logout()

        # Login with admin
        self.client.login(username='username', password='password')

        # Switch owner of location
        response = self.client.post(reverse('stock-location-edit', args=(location_created.pk,)),
                                    {'name': new_location['name'], 'owner': user_group_owner.pk},
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertContains(response, '"form_valid": true', status_code=200)

        # Check that owner was updated for item in this location
        stock_item = StockItem.objects.all().last()
        self.assertEqual(stock_item.owner, user_group_owner)
