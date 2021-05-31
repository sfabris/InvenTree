# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.test import TestCase
from django.contrib.auth import get_user_model

from .models import InvenTreeSetting


class SettingsTest(TestCase):
    """
    Tests for the 'settings' model
    """

    fixtures = [
        'settings',
    ]

    def setUp(self):

        user = get_user_model()

        self.user = user.objects.create_user('username', 'user@email.com', 'password')
        self.user.is_staff = True
        self.user.save()

        self.client.login(username='username', password='password')

    def test_settings_objects(self):

        # There should be two settings objects in the database
        settings = InvenTreeSetting.objects.all()

        self.assertTrue(settings.count() >= 2)

        instance_name = InvenTreeSetting.objects.get(pk=1)
        self.assertEqual(instance_name.key, 'INVENTREE_INSTANCE')
        self.assertEqual(instance_name.value, 'My very first InvenTree Instance')

        # Check object lookup (case insensitive)
        self.assertEqual(InvenTreeSetting.get_setting_object('iNvEnTrEE_inSTanCE').pk, 1)

    def test_required_values(self):
        """
        - Ensure that every global setting has a name.
        - Ensure that every global setting has a description.
        """

        for key in InvenTreeSetting.GLOBAL_SETTINGS.keys():

            setting = InvenTreeSetting.GLOBAL_SETTINGS[key]

            name = setting.get('name', None)

            if name is None:
                raise ValueError(f'Missing GLOBAL_SETTING name for {key}')

            description = setting.get('description', None)

            if description is None:
                raise ValueError(f'Missing GLOBAL_SETTING description for {key}')

            if not key == key.upper():
                raise ValueError(f"GLOBAL_SETTINGS key '{key}' is not uppercase")

    def test_defaults(self):
        """
        Populate the settings with default values
        """

        for key in InvenTreeSetting.GLOBAL_SETTINGS.keys():

            value = InvenTreeSetting.get_setting_default(key)

            InvenTreeSetting.set_setting(key, value, self.user)

            self.assertEqual(value, InvenTreeSetting.get_setting(key))

            # Any fields marked as 'boolean' must have a default value specified
            setting = InvenTreeSetting.get_setting_object(key)

            if setting.is_bool():
                if setting.default_value in ['', None]:
                    raise ValueError(f'Default value for boolean setting {key} not provided')

                if setting.default_value not in [True, False]:
                    raise ValueError(f'Non-boolean default value specified for {key}')
