# -*- coding: utf-8 -*-

import PIL

from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

from InvenTree.api_tester import InvenTreeAPITestCase
from InvenTree.status_codes import StockStatus

from part.models import Part, PartCategory
from stock.models import StockItem
from company.models import Company
from common.models import InvenTreeSetting


class PartOptionsAPITest(InvenTreeAPITestCase):
    """
    Tests for the various OPTIONS endpoints in the /part/ API

    Ensure that the required field details are provided!
    """

    roles = [
        'part.add',
    ]

    def setUp(self):

        super().setUp()

    def test_part(self):
        """
        Test the Part API OPTIONS
        """

        actions = self.getActions(reverse('api-part-list'))['POST']

        # Check that a bunch o' fields are contained
        for f in ['assembly', 'component', 'description', 'image', 'IPN']:
            self.assertTrue(f in actions.keys())

        # Active is a 'boolean' field
        active = actions['active']

        self.assertTrue(active['default'])
        self.assertEqual(active['help_text'], 'Is this part active?')
        self.assertEqual(active['type'], 'boolean')
        self.assertEqual(active['read_only'], False)

        # String field
        ipn = actions['IPN']
        self.assertEqual(ipn['type'], 'string')
        self.assertFalse(ipn['required'])
        self.assertEqual(ipn['max_length'], 100)
        self.assertEqual(ipn['help_text'], 'Internal Part Number')

        # Related field
        category = actions['category']

        self.assertEqual(category['type'], 'related field')
        self.assertTrue(category['required'])
        self.assertFalse(category['read_only'])
        self.assertEqual(category['label'], 'Category')
        self.assertEqual(category['model'], 'partcategory')
        self.assertEqual(category['api_url'], reverse('api-part-category-list'))
        self.assertEqual(category['help_text'], 'Part category')

    def test_category(self):
        """
        Test the PartCategory API OPTIONS endpoint
        """

        actions = self.getActions(reverse('api-part-category-list'))

        # actions should *not* contain 'POST' as we do not have the correct role
        self.assertFalse('POST' in actions)

        self.assignRole('part_category.add')

        actions = self.getActions(reverse('api-part-category-list'))['POST']

        name = actions['name']

        self.assertTrue(name['required'])
        self.assertEqual(name['label'], 'Name')

        loc = actions['default_location']
        self.assertEqual(loc['api_url'], reverse('api-location-list'))

    def test_bom_item(self):
        """
        Test the BomItem API OPTIONS endpoint
        """

        actions = self.getActions(reverse('api-bom-list'))['POST']

        inherited = actions['inherited']

        self.assertEqual(inherited['type'], 'boolean')

        # 'part' reference
        part = actions['part']

        self.assertTrue(part['required'])
        self.assertFalse(part['read_only'])
        self.assertTrue(part['filters']['assembly'])

        # 'sub_part' reference
        sub_part = actions['sub_part']

        self.assertTrue(sub_part['required'])
        self.assertEqual(sub_part['type'], 'related field')
        self.assertTrue(sub_part['filters']['component'])


class PartAPITest(InvenTreeAPITestCase):
    """
    Series of tests for the Part DRF API
    - Tests for Part API
    - Tests for PartCategory API
    """

    fixtures = [
        'category',
        'part',
        'location',
        'bom',
        'test_templates',
    ]

    roles = [
        'part.change',
        'part.add',
        'part.delete',
        'part_category.change',
        'part_category.add',
    ]

    def setUp(self):
        super().setUp()

    def test_get_categories(self):
        """
        Test that we can retrieve list of part categories,
        with various filtering options.
        """

        url = reverse('api-part-category-list')

        # Request *all* part categories
        response = self.client.get(url, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 8)

        # Request top-level part categories only
        response = self.client.get(
            url,
            {
                'parent': 'null',
            },
            format='json'
        )

        self.assertEqual(len(response.data), 2)

        # Children of PartCategory<1>, cascade
        response = self.client.get(
            url,
            {
                'parent': 1,
                'cascade': 'true',
            },
            format='json',
        )

        self.assertEqual(len(response.data), 5)

        # Children of PartCategory<1>, do not cascade
        response = self.client.get(
            url,
            {
                'parent': 1,
                'cascade': 'false',
            },
            format='json',
        )

        self.assertEqual(len(response.data), 3)

    def test_add_categories(self):
        """ Check that we can add categories """
        data = {
            'name': 'Animals',
            'description': 'All animals go here'
        }

        url = reverse('api-part-category-list')
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        parent = response.data['pk']

        # Add some sub-categories to the top-level 'Animals' category
        for animal in ['cat', 'dog', 'zebra']:
            data = {
                'name': animal,
                'description': 'A sort of animal',
                'parent': parent,
            }
            response = self.client.post(url, data, format='json')
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            self.assertEqual(response.data['parent'], parent)
            self.assertEqual(response.data['name'], animal)
            self.assertEqual(response.data['pathstring'], 'Animals/' + animal)

        # There should be now 8 categories
        response = self.client.get(url, format='json')
        self.assertEqual(len(response.data), 12)

    def test_cat_detail(self):
        url = reverse('api-part-category-detail', kwargs={'pk': 4})
        response = self.client.get(url, format='json')

        # Test that we have retrieved the category
        self.assertEqual(response.data['description'], 'Integrated Circuits')
        self.assertEqual(response.data['parent'], 1)

        # Change some data and post it back
        data = response.data
        data['name'] = 'Changing category'
        data['parent'] = None
        data['description'] = 'Changing the description'
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['description'], 'Changing the description')
        self.assertIsNone(response.data['parent'])

    def test_get_all_parts(self):
        url = reverse('api-part-list')
        data = {'cascade': True}
        response = self.client.get(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 13)

    def test_get_parts_by_cat(self):
        url = reverse('api-part-list')
        data = {'category': 2}
        response = self.client.get(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # There should only be 2 objects in category C
        self.assertEqual(len(response.data), 2)

        for part in response.data:
            self.assertEqual(part['category'], 2)

    def test_include_children(self):
        """ Test the special 'include_child_categories' flag
        If provided, parts are provided for ANY child category (recursive)
        """
        url = reverse('api-part-list')
        data = {'category': 1, 'cascade': True}

        # Now request to include child categories
        response = self.client.get(url, data, format='json')

        # Now there should be 5 total parts
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)

    def test_get_bom_list(self):
        """ There should be 4 BomItem objects in the database """
        url = reverse('api-bom-list')
        response = self.client.get(url, format='json')
        self.assertEqual(len(response.data), 4)

    def test_get_bom_detail(self):
        # Get the detail for a single BomItem
        url = reverse('api-bom-item-detail', kwargs={'pk': 3})
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(int(float(response.data['quantity'])), 25)

        # Increase the quantity
        data = response.data
        data['quantity'] = 57
        data['note'] = 'Added a note'

        response = self.client.patch(url, data, format='json')

        # Check that the quantity was increased and a note added
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(int(float(response.data['quantity'])), 57)
        self.assertEqual(response.data['note'], 'Added a note')

    def test_add_bom_item(self):
        url = reverse('api-bom-list')

        data = {
            'part': 100,
            'sub_part': 4,
            'quantity': 777,
        }

        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Now try to create a BomItem which points to a non-assembly part (should fail)
        data['part'] = 3
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # TODO - Now try to create a BomItem which references itself
        data['part'] = 2
        data['sub_part'] = 2
        response = self.client.post(url, data, format='json')

    def test_test_templates(self):

        url = reverse('api-part-test-template-list')

        # List ALL items
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 7)

        # Request for a particular part
        response = self.client.get(url, data={'part': 10000})
        self.assertEqual(len(response.data), 5)

        response = self.client.get(url, data={'part': 10004})
        self.assertEqual(len(response.data), 7)

        # Try to post a new object (missing description)
        response = self.client.post(
            url,
            data={
                'part': 10000,
                'test_name': 'My very first test',
                'required': False,
            }
        )

        self.assertEqual(response.status_code, 400)

        # Try to post a new object (should succeed)
        response = self.client.post(
            url,
            data={
                'part': 10000,
                'test_name': 'New Test',
                'required': True,
                'description': 'a test description'
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Try to post a new test with the same name (should fail)
        response = self.client.post(
            url,
            data={
                'part': 10004,
                'test_name': "   newtest",
                'description': 'dafsdf',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Try to post a new test against a non-trackable part (should fail)
        response = self.client.post(
            url,
            data={
                'part': 1,
                'test_name': 'A simple test',
            }
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_thumbs(self):
        """
        Return list of part thumbnails
        """

        url = reverse('api-part-thumbs')

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_paginate(self):
        """
        Test pagination of the Part list API
        """

        for n in [1, 5, 10]:
            response = self.get(reverse('api-part-list'), {'limit': n})

            data = response.data

            self.assertIn('count', data)
            self.assertIn('results', data)

            self.assertEqual(len(data['results']), n)

    def test_default_values(self):
        """
        Tests for 'default' values:

        Ensure that unspecified fields revert to "default" values
        (as specified in the model field definition)
        """

        url = reverse('api-part-list')

        response = self.client.post(url, {
            'name': 'all defaults',
            'description': 'my test part',
            'category': 1,
        })

        data = response.data

        # Check that the un-specified fields have used correct default values
        self.assertTrue(data['active'])
        self.assertFalse(data['virtual'])

        # By default, parts are not purchaseable
        self.assertFalse(data['purchaseable'])

        # Set the default 'purchaseable' status to True
        InvenTreeSetting.set_setting(
            'PART_PURCHASEABLE',
            True,
            self.user
        )

        response = self.client.post(url, {
            'name': 'all defaults',
            'description': 'my test part 2',
            'category': 1,
        })

        # Part should now be purchaseable by default
        self.assertTrue(response.data['purchaseable'])

        # "default" values should not be used if the value is specified
        response = self.client.post(url, {
            'name': 'all defaults',
            'description': 'my test part 2',
            'category': 1,
            'active': False,
            'purchaseable': False,
        })

        self.assertFalse(response.data['active'])
        self.assertFalse(response.data['purchaseable'])


class PartDetailTests(InvenTreeAPITestCase):
    """
    Test that we can create / edit / delete Part objects via the API
    """

    fixtures = [
        'category',
        'part',
        'location',
        'bom',
        'test_templates',
    ]

    roles = [
        'part.change',
        'part.add',
        'part.delete',
        'part_category.change',
        'part_category.add',
    ]

    def setUp(self):
        super().setUp()

    def test_part_operations(self):
        n = Part.objects.count()

        # Create a part
        response = self.client.post(
            reverse('api-part-list'),
            {
                'name': 'my test api part',
                'description': 'a part created with the API',
                'category': 1,
            }
        )

        self.assertEqual(response.status_code, 201)

        pk = response.data['pk']

        # Check that a new part has been added
        self.assertEqual(Part.objects.count(), n + 1)

        part = Part.objects.get(pk=pk)

        self.assertEqual(part.name, 'my test api part')

        # Edit the part
        url = reverse('api-part-detail', kwargs={'pk': pk})

        # Let's change the name of the part

        response = self.client.patch(url, {
            'name': 'a new better name',
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['pk'], pk)
        self.assertEqual(response.data['name'], 'a new better name')

        part = Part.objects.get(pk=pk)

        # Name has been altered
        self.assertEqual(part.name, 'a new better name')

        # Part count should not have changed
        self.assertEqual(Part.objects.count(), n + 1)

        # Now, try to set the name to the *same* value
        # 2021-06-22 this test is to check that the "duplicate part" checks don't do strange things
        response = self.client.patch(url, {
            'name': 'a new better name',
        })

        self.assertEqual(response.status_code, 200)

        # Try to remove the part
        response = self.client.delete(url)

        # As the part is 'active' we cannot delete it
        self.assertEqual(response.status_code, 405)

        # So, let's make it not active
        response = self.patch(url, {'active': False}, expected_code=200)

        response = self.client.delete(url)
        self.assertEqual(response.status_code, 204)

        # Part count should have reduced
        self.assertEqual(Part.objects.count(), n)

    def test_duplicates(self):
        """
        Check that trying to create 'duplicate' parts results in errors
        """

        # Create a part
        response = self.client.post(reverse('api-part-list'), {
            'name': 'part',
            'description': 'description',
            'IPN': 'IPN-123',
            'category': 1,
            'revision': 'A',
        })

        self.assertEqual(response.status_code, 201)

        n = Part.objects.count()

        # Check that we cannot create a duplicate in a different category
        response = self.client.post(reverse('api-part-list'), {
            'name': 'part',
            'description': 'description',
            'IPN': 'IPN-123',
            'category': 2,
            'revision': 'A',
        })

        self.assertEqual(response.status_code, 400)

        # Check that only 1 matching part exists
        parts = Part.objects.filter(
            name='part',
            description='description',
            IPN='IPN-123'
        )

        self.assertEqual(parts.count(), 1)

        # A new part should *not* have been created
        self.assertEqual(Part.objects.count(), n)

        # But a different 'revision' *can* be created
        response = self.client.post(reverse('api-part-list'), {
            'name': 'part',
            'description': 'description',
            'IPN': 'IPN-123',
            'category': 2,
            'revision': 'B',
        })

        self.assertEqual(response.status_code, 201)
        self.assertEqual(Part.objects.count(), n + 1)

        # Now, check that we cannot *change* an existing part to conflict
        pk = response.data['pk']

        url = reverse('api-part-detail', kwargs={'pk': pk})

        # Attempt to alter the revision code
        response = self.client.patch(
            url,
            {
                'revision': 'A',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 400)

        # But we *can* change it to a unique revision code
        response = self.client.patch(
            url,
            {
                'revision': 'C',
            }
        )

        self.assertEqual(response.status_code, 200)

    def test_image_upload(self):
        """
        Test that we can upload an image to the part API
        """

        self.assignRole('part.add')

        # Create a new part
        response = self.client.post(
            reverse('api-part-list'),
            {
                'name': 'imagine',
                'description': 'All the people',
                'category': 1,
            },
            expected_code=201
        )

        pk = response.data['pk']

        url = reverse('api-part-detail', kwargs={'pk': pk})

        p = Part.objects.get(pk=pk)

        # Part should not have an image!
        with self.assertRaises(ValueError):
            print(p.image.file)

        # Create a custom APIClient for file uploads
        # Ref: https://stackoverflow.com/questions/40453947/how-to-generate-a-file-upload-test-request-with-django-rest-frameworks-apireq
        upload_client = APIClient()
        upload_client.force_authenticate(user=self.user)

        # Try to upload a non-image file
        with open('dummy_image.txt', 'w') as dummy_image:
            dummy_image.write('hello world')

        with open('dummy_image.txt', 'rb') as dummy_image:
            response = upload_client.patch(
                url,
                {
                    'image': dummy_image,
                },
                format='multipart',
            )

            self.assertEqual(response.status_code, 400)

        # Now try to upload a valid image file
        img = PIL.Image.new('RGB', (128, 128), color='red')
        img.save('dummy_image.jpg')

        with open('dummy_image.jpg', 'rb') as dummy_image:
            response = upload_client.patch(
                url,
                {
                    'image': dummy_image,
                },
                format='multipart',
            )

            self.assertEqual(response.status_code, 200)

        # And now check that the image has been set
        p = Part.objects.get(pk=pk)


class PartAPIAggregationTest(InvenTreeAPITestCase):
    """
    Tests to ensure that the various aggregation annotations are working correctly...
    """

    fixtures = [
        'category',
        'company',
        'part',
        'location',
        'bom',
        'test_templates',
    ]

    roles = [
        'part.view',
        'part.change',
    ]

    def setUp(self):

        super().setUp()

        # Add a new part
        self.part = Part.objects.create(
            name='Banana',
            description='This is a banana',
            category=PartCategory.objects.get(pk=1),
        )

        # Create some stock items associated with the part

        # First create 600 units which are OK
        StockItem.objects.create(part=self.part, quantity=100)
        StockItem.objects.create(part=self.part, quantity=200)
        StockItem.objects.create(part=self.part, quantity=300)

        # Now create another 400 units which are LOST
        StockItem.objects.create(part=self.part, quantity=400, status=StockStatus.LOST)

    def get_part_data(self):
        url = reverse('api-part-list')

        response = self.client.get(url, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        for part in response.data:
            if part['pk'] == self.part.pk:
                return part

        # We should never get here!
        self.assertTrue(False)

    def test_stock_quantity(self):
        """
        Simple test for the stock quantity
        """

        data = self.get_part_data()

        self.assertEqual(data['in_stock'], 600)
        self.assertEqual(data['stock_item_count'], 4)

        # Add some more stock items!!
        for i in range(100):
            StockItem.objects.create(part=self.part, quantity=5)

        # Add another stock item which is assigned to a customer (and shouldn't count)
        customer = Company.objects.get(pk=4)
        StockItem.objects.create(part=self.part, quantity=9999, customer=customer)

        data = self.get_part_data()

        self.assertEqual(data['in_stock'], 1100)
        self.assertEqual(data['stock_item_count'], 105)


class PartParameterTest(InvenTreeAPITestCase):
    """
    Tests for the ParParameter API
    """

    superuser = True

    fixtures = [
        'category',
        'part',
        'location',
        'params',
    ]

    def setUp(self):

        super().setUp()

    def test_list_params(self):
        """
        Test for listing part parameters
        """

        url = reverse('api-part-parameter-list')

        response = self.client.get(url, format='json')

        self.assertEqual(len(response.data), 5)

        # Filter by part
        response = self.client.get(
            url,
            {
                'part': 3,
            },
            format='json'
        )

        self.assertEqual(len(response.data), 3)

        # Filter by template
        response = self.client.get(
            url,
            {
                'template': 1,
            },
            format='json',
        )

        self.assertEqual(len(response.data), 3)

    def test_create_param(self):
        """
        Test that we can create a param via the API
        """

        url = reverse('api-part-parameter-list')

        response = self.client.post(
            url,
            {
                'part': '2',
                'template': '3',
                'data': 70
            }
        )

        self.assertEqual(response.status_code, 201)

        response = self.client.get(url, format='json')

        self.assertEqual(len(response.data), 6)

    def test_param_detail(self):
        """
        Tests for the PartParameter detail endpoint
        """

        url = reverse('api-part-parameter-detail', kwargs={'pk': 5})

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)

        data = response.data

        self.assertEqual(data['pk'], 5)
        self.assertEqual(data['part'], 3)
        self.assertEqual(data['data'], '12')

        # PATCH data back in
        response = self.client.patch(url, {'data': '15'}, format='json')

        self.assertEqual(response.status_code, 200)

        # Check that the data changed!
        response = self.client.get(url, format='json')

        data = response.data

        self.assertEqual(data['data'], '15')
