""" Unit tests for Part Views (see views.py) """

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from .models import Part, PartRelated


class PartViewTestCase(TestCase):

    fixtures = [
        'category',
        'part',
        'bom',
        'location',
        'company',
        'supplier_part',
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


class PartListTest(PartViewTestCase):

    def test_part_index(self):
        response = self.client.get(reverse('part-index'))
        self.assertEqual(response.status_code, 200)

        keys = response.context.keys()
        self.assertIn('csrf_token', keys)
        self.assertIn('parts', keys)
        self.assertIn('user', keys)

    def test_export(self):
        """ Export part data to CSV """

        response = self.client.get(reverse('part-export'), {'parts': '1,2,3,4,5,6,7,8,9,10'}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        self.assertEqual(response.status_code, 200)
        self.assertIn('streaming_content', dir(response))


class PartDetailTest(PartViewTestCase):

    def test_part_detail(self):
        """ Test that we can retrieve a part detail page """

        pk = 1

        response = self.client.get(reverse('part-detail', args=(pk,)))
        self.assertEqual(response.status_code, 200)

        part = Part.objects.get(pk=pk)

        keys = response.context.keys()

        self.assertIn('part', keys)
        self.assertIn('category', keys)

        self.assertEqual(response.context['part'].pk, pk)
        self.assertEqual(response.context['category'], part.category)

        self.assertFalse(response.context['editing_enabled'])

    def test_editable(self):

        pk = 1
        response = self.client.get(reverse('part-detail', args=(pk,)), {'edit': True})

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['editing_enabled'])

    def test_part_detail_from_ipn(self):
        """
        Test that we can retrieve a part detail page from part IPN:
        - if no part with matching IPN -> return part index
        - if unique IPN match -> return part detail page
        - if multiple IPN matches -> return part index
        """
        ipn_test = 'PART-000000-AA'
        pk = 1

        def test_ipn_match(index_result=False, detail_result=False):
            index_redirect = False
            detail_redirect = False

            response = self.client.get(reverse('part-detail-from-ipn', args=(ipn_test,)))

            # Check for PartIndex redirect
            try:
                if response.url == '/part/':
                    index_redirect = True
            except AttributeError:
                pass

            # Check for PartDetail redirect
            try:
                if response.context['part'].pk == pk:
                    detail_redirect = True
            except TypeError:
                pass

            self.assertEqual(index_result, index_redirect)
            self.assertEqual(detail_result, detail_redirect)

        # Test no match
        test_ipn_match(index_result=True, detail_result=False)

        # Test unique match
        part = Part.objects.get(pk=pk)
        part.IPN = ipn_test
        part.save()

        test_ipn_match(index_result=False, detail_result=True)

        # Test multiple matches
        part = Part.objects.get(pk=pk + 1)
        part.IPN = ipn_test
        part.save()

        test_ipn_match(index_result=True, detail_result=False)

    def test_bom_download(self):
        """ Test downloading a BOM for a valid part """

        response = self.client.get(reverse('bom-download', args=(1,)), HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        self.assertIn('streaming_content', dir(response))


class PartTests(PartViewTestCase):
    """ Tests for Part forms """

    def test_part_edit(self):

        response = self.client.get(reverse('part-edit', args=(1,)), HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        keys = response.context.keys()
        data = str(response.content)

        self.assertEqual(response.status_code, 200)

        self.assertIn('part', keys)
        self.assertIn('csrf_token', keys)

        self.assertIn('html_form', data)
        self.assertIn('"title":', data)

    def test_part_create(self):
        """ Launch form to create a new part """
        response = self.client.get(reverse('part-create'), {'category': 1}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)

        # And again, with an invalid category
        response = self.client.get(reverse('part-create'), {'category': 9999}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)

        # And again, with no category
        response = self.client.get(reverse('part-create'), {'name': 'Test part'}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)

    def test_part_duplicate(self):
        """ Launch form to duplicate part """

        # First try with an invalid part
        response = self.client.get(reverse('part-duplicate', args=(9999,)), HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)

        response = self.client.get(reverse('part-duplicate', args=(1,)), HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)

    def test_make_variant(self):

        response = self.client.get(reverse('make-part-variant', args=(1,)), HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)


class PartRelatedTests(PartViewTestCase):

    def test_valid_create(self):
        """ test creation of a related part """

        # Test GET view
        response = self.client.get(reverse('part-related-create'), {'part': 1},
                                   HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)

        # Test POST view with valid form data
        response = self.client.post(reverse('part-related-create'), {'part_1': 1, 'part_2': 2},
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertContains(response, '"form_valid": true', status_code=200)

        # Try to create the same relationship with part_1 and part_2 pks reversed
        response = self.client.post(reverse('part-related-create'), {'part_1': 2, 'part_2': 1},
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertContains(response, '"form_valid": false', status_code=200)

        # Try to create part related to itself
        response = self.client.post(reverse('part-related-create'), {'part_1': 1, 'part_2': 1},
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertContains(response, '"form_valid": false', status_code=200)

        # Check final count
        n = PartRelated.objects.all().count()
        self.assertEqual(n, 1)


class PartAttachmentTests(PartViewTestCase):

    def test_valid_create(self):
        """ test creation of an attachment for a valid part """

        response = self.client.get(reverse('part-attachment-create'), {'part': 1}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)

        # TODO - Create a new attachment using this view

    def test_invalid_create(self):
        """ test creation of an attachment for an invalid part """

        # TODO
        pass

    def test_edit(self):
        """ test editing an attachment """

        # TODO
        pass


class PartQRTest(PartViewTestCase):
    """ Tests for the Part QR Code AJAX view """

    def test_html_redirect(self):
        # A HTML request for a QR code should be redirected (use an AJAX request instead)
        response = self.client.get(reverse('part-qr', args=(1,)))
        self.assertEqual(response.status_code, 302)

    def test_valid_part(self):
        response = self.client.get(reverse('part-qr', args=(1,)), HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)

        data = str(response.content)

        self.assertIn('Part QR Code', data)
        self.assertIn('<img src=', data)

    def test_invalid_part(self):
        response = self.client.get(reverse('part-qr', args=(9999,)), HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        self.assertEqual(response.status_code, 200)


class CategoryTest(PartViewTestCase):
    """ Tests for PartCategory related views """

    def test_create(self):
        """ Test view for creating a new category """
        response = self.client.get(reverse('category-create'), {'category': 1}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        self.assertEqual(response.status_code, 200)

    def test_create_invalid_parent(self):
        """ test creation of a new category with an invalid parent """
        response = self.client.get(reverse('category-create'), {'category': 9999}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        # Form should still return OK
        self.assertEqual(response.status_code, 200)

    def test_edit(self):
        """ Retrieve the part category editing form """
        response = self.client.get(reverse('category-edit', args=(1,)), HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)

    def test_set_category(self):
        """ Test that the "SetCategory" view works """

        url = reverse('part-set-category')

        response = self.client.get(url, {'parts[]': 1}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)

        data = {
            'part_id_10': True,
            'part_id_1': True,
            'part_category': 5
        }

        response = self.client.post(url, data, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)


class BomItemTests(PartViewTestCase):
    """ Tests for BomItem related views """

    def test_create_valid_parent(self):
        """ Create a BomItem for a valid part """
        response = self.client.get(reverse('bom-item-create'), {'parent': 1}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)

    def test_create_no_parent(self):
        """ Create a BomItem without a parent """
        response = self.client.get(reverse('bom-item-create'), HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)

    def test_create_invalid_parent(self):
        """ Create a BomItem with an invalid parent """
        response = self.client.get(reverse('bom-item-create'), {'parent': 99999}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
