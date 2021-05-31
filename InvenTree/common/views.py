"""
Django views for interacting with common models
"""

# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os

from django.utils.translation import ugettext_lazy as _
from django.forms import CheckboxInput, Select
from django.conf import settings
from django.core.files.storage import FileSystemStorage

from formtools.wizard.views import SessionWizardView

from InvenTree.views import AjaxUpdateView
from InvenTree.helpers import str2bool

from . import models
from . import forms
from .files import FileManager


class SettingEdit(AjaxUpdateView):
    """
    View for editing an InvenTree key:value settings object,
    (or creating it if the key does not already exist)
    """

    model = models.InvenTreeSetting
    ajax_form_title = _('Change Setting')
    form_class = forms.SettingEditForm
    ajax_template_name = "common/edit_setting.html"

    def get_context_data(self, **kwargs):
        """
        Add extra context information about the particular setting object.
        """

        ctx = super().get_context_data(**kwargs)

        setting = self.get_object()

        ctx['key'] = setting.key
        ctx['value'] = setting.value
        ctx['name'] = models.InvenTreeSetting.get_setting_name(setting.key)
        ctx['description'] = models.InvenTreeSetting.get_setting_description(setting.key)

        return ctx

    def get_form(self):
        """
        Override default get_form behaviour
        """

        form = super().get_form()

        setting = self.get_object()

        choices = setting.choices()

        if choices is not None:
            form.fields['value'].widget = Select(choices=choices)
        elif setting.is_bool():
            form.fields['value'].widget = CheckboxInput()

            self.object.value = str2bool(setting.value)
            form.fields['value'].value = str2bool(setting.value)

        name = models.InvenTreeSetting.get_setting_name(setting.key)

        if name:
            form.fields['value'].label = name

        description = models.InvenTreeSetting.get_setting_description(setting.key)

        if description:
            form.fields['value'].help_text = description

        return form

    def validate(self, setting, form):
        """
        Perform custom validation checks on the form data.
        """

        data = form.cleaned_data

        value = data.get('value', None)

        if setting.choices():
            """
            If a set of choices are provided for a given setting,
            the provided value must be one of those choices.
            """

            choices = [choice[0] for choice in setting.choices()]

            if value not in choices:
                form.add_error('value', _('Supplied value is not allowed'))

        if setting.is_bool():
            """
            If a setting is defined as a boolean setting,
            the provided value must look somewhat like a boolean value!
            """

            if not str2bool(value, test=True) and not str2bool(value, test=False):
                form.add_error('value', _('Supplied value must be a boolean'))


class MultiStepFormView(SessionWizardView):
    """ Setup basic methods of multi-step form

        form_list: list of forms
        form_steps_description: description for each form
    """

    form_list = []
    form_steps_template = []
    form_steps_description = []
    file_manager = None
    media_folder = ''
    file_storage = FileSystemStorage(settings.MEDIA_ROOT)

    def __init__(self, *args, **kwargs):
        """ Override init method to set media folder """
        super().__init__(*args, **kwargs)

        self.process_media_folder()
        
    def process_media_folder(self):
        """ Process media folder """

        if self.media_folder:
            media_folder_abs = os.path.join(settings.MEDIA_ROOT, self.media_folder)
            if not os.path.exists(media_folder_abs):
                os.mkdir(media_folder_abs)
            self.file_storage = FileSystemStorage(location=media_folder_abs)

    def get_template_names(self):
        """ Select template """
        
        try:
            # Get template
            template = self.form_steps_template[self.steps.index]
        except IndexError:
            return self.template_name

        return template

    def get_context_data(self, **kwargs):
        """ Update context data """
        
        # Retrieve current context
        context = super().get_context_data(**kwargs)

        # Get form description
        try:
            description = self.form_steps_description[self.steps.index]
        except IndexError:
            description = ''
        # Add description to form steps
        context.update({'description': description})

        return context


class FileManagementFormView(MultiStepFormView):
    """ Setup form wizard to perform the following steps:
        1. Upload tabular data file
        2. Match headers to InvenTree fields
        3. Edit row data and match InvenTree items
    """

    name = None
    form_list = [
        ('upload', forms.UploadFile),
        ('fields', forms.MatchField),
        ('items', forms.MatchItem),
    ]
    form_steps_description = [
        _("Upload File"),
        _("Match Fields"),
        _("Match Items"),
    ]
    media_folder = 'file_upload/'
    extra_context_data = {}

    def get_context_data(self, form, **kwargs):
        context = super().get_context_data(form=form, **kwargs)

        if self.steps.current in ('fields', 'items'):
            
            # Get columns and row data
            self.columns = self.file_manager.columns()
            self.rows = self.file_manager.rows()
            # Check for stored data
            stored_data = self.storage.get_step_data(self.steps.current)
            if stored_data:
                self.get_form_table_data(stored_data)
            elif self.steps.current == 'items':
                # Set form table data
                self.set_form_table_data(form=form)
            
            # Update context
            context.update({'rows': self.rows})
            context.update({'columns': self.columns})

        # Load extra context data
        for key, items in self.extra_context_data.items():
            context.update({key: items})

        return context

    def get_file_manager(self, step=None, form=None):
        """ Get FileManager instance from uploaded file """

        if self.file_manager:
            return

        if step is not None:
            # Retrieve stored files from upload step
            upload_files = self.storage.get_step_files('upload')
            if upload_files:
                # Get file
                file = upload_files.get('upload-file', None)
                if file:
                    self.file_manager = FileManager(file=file, name=self.name)

    def get_form_kwargs(self, step=None):
        """ Update kwargs to dynamically build forms """

        # Always retrieve FileManager instance from uploaded file
        self.get_file_manager(step)

        if step == 'upload':
            # Dynamically build upload form
            if self.name:
                kwargs = {
                    'name': self.name
                }
                return kwargs
        elif step == 'fields':
            # Dynamically build match field form
            kwargs = {
                'file_manager': self.file_manager
            }
            return kwargs
        elif step == 'items':
            # Dynamically build match item form
            kwargs = {}
            kwargs['file_manager'] = self.file_manager

            # Get data from fields step
            data = self.storage.get_step_data('fields')

            # Process to update columns and rows
            self.rows = self.file_manager.rows()
            self.columns = self.file_manager.columns()
            self.get_form_table_data(data)
            self.set_form_table_data()
            self.get_field_selection()
            
            kwargs['row_data'] = self.rows

            return kwargs
        
        return super().get_form_kwargs()

    def get_form_table_data(self, form_data):
        """ Extract table cell data from form data and fields.
        These data are used to maintain state between sessions.

        Table data keys are as follows:

            col_name_<idx> - Column name at idx as provided in the uploaded file
            col_guess_<idx> - Column guess at idx as selected
            row_<x>_col<y> - Cell data as provided in the uploaded file

        """

        # Map the columns
        self.column_names = {}
        self.column_selections = {}

        self.row_data = {}

        for item, value in form_data.items():

            # Column names as passed as col_name_<idx> where idx is an integer

            # Extract the column names
            if item.startswith('col_name_'):
                try:
                    col_id = int(item.replace('col_name_', ''))
                except ValueError:
                    continue

                self.column_names[col_id] = value

            # Extract the column selections (in the 'select fields' view)
            if item.startswith('fields-'):

                try:
                    col_name = item.replace('fields-', '')
                except ValueError:
                    continue

                for idx, name in self.column_names.items():
                    if name == col_name:
                        self.column_selections[idx] = value
                        break

            # Extract the row data
            if item.startswith('row_'):
                # Item should be of the format row_<r>_col_<c>
                s = item.split('_')

                if len(s) < 4:
                    continue

                # Ignore row/col IDs which are not correct numeric values
                try:
                    row_id = int(s[1])
                    col_id = int(s[3])
                except ValueError:
                    continue
                
                if row_id not in self.row_data:
                    self.row_data[row_id] = {}

                self.row_data[row_id][col_id] = value

    def set_form_table_data(self, form=None):
        """ Set the form table data """

        if self.column_names:
            # Re-construct the column data
            self.columns = []

            for idx, value in self.column_names.items():
                header = ({
                    'name': value,
                    'guess': self.column_selections.get(idx, ''),
                })
                self.columns.append(header)

        if self.row_data:
            # Re-construct the row data
            self.rows = []

            # Update the row data
            for row_idx, row_key in enumerate(sorted(self.row_data.keys())):
                row_data = self.row_data[row_key]

                data = []

                for idx, item in row_data.items():
                    column_data = {
                        'name': self.column_names[idx],
                        'guess': self.column_selections[idx],
                    }
                    
                    cell_data = {
                        'cell': item,
                        'idx': idx,
                        'column': column_data,
                    }
                    data.append(cell_data)
                
                row = {
                    'index': row_idx,
                    'data': data,
                    'errors': {},
                }
                self.rows.append(row)

        # In the item selection step: update row data with mapping to form fields
        if form and self.steps.current == 'items':
            # Find field keys
            field_keys = []
            for field in form.fields:
                field_key = field.split('-')[0]
                if field_key not in field_keys:
                    field_keys.append(field_key)

            # Populate rows
            for row in self.rows:
                for field_key in field_keys:
                    # Map row data to field
                    row[field_key] = field_key + '-' + str(row['index'])

    def get_column_index(self, name):
        """ Return the index of the column with the given name.
        It named column is not found, return -1
        """

        try:
            idx = list(self.column_selections.values()).index(name)
        except ValueError:
            idx = -1

        return idx

    def get_field_selection(self):
        """ Once data columns have been selected, attempt to pre-select the proper data from the database.
        This function is called once the field selection has been validated.
        The pre-fill data are then passed through to the part selection form.

        This method is very specific to the type of data found in the file,
        therefore overwrite it in the subclass.
        """
        pass

    def check_field_selection(self, form):
        """ Check field matching """

        # Are there any missing columns?
        missing_columns = []

        # Check that all required fields are present
        for col in self.file_manager.REQUIRED_HEADERS:
            if col not in self.column_selections.values():
                missing_columns.append(col)

        # Check that at least one of the part match field is present
        part_match_found = False
        for col in self.file_manager.ITEM_MATCH_HEADERS:
            if col in self.column_selections.values():
                part_match_found = True
                break
        
        # If not, notify user
        if not part_match_found:
            for col in self.file_manager.ITEM_MATCH_HEADERS:
                missing_columns.append(col)

        # Track any duplicate column selections
        duplicates = []

        for col in self.column_names:

            if col in self.column_selections:
                guess = self.column_selections[col]
            else:
                guess = None

            if guess:
                n = list(self.column_selections.values()).count(self.column_selections[col])
                if n > 1 and self.column_selections[col] not in duplicates:
                    duplicates.append(self.column_selections[col])
        
        # Store extra context data
        self.extra_context_data = {
            'missing_columns': missing_columns,
            'duplicates': duplicates,
        }

        # Data validation
        valid = not missing_columns and not duplicates

        return valid

    def validate(self, step, form):
        """ Validate forms """

        valid = True

        # Get form table data
        self.get_form_table_data(form.data)

        if step == 'fields':
            # Validate user form data
            valid = self.check_field_selection(form)

            if not valid:
                form.add_error(None, _('Fields matching failed'))

        elif step == 'items':
            pass

        return valid

    def post(self, request, *args, **kwargs):
        """ Perform validations before posting data """

        wizard_goto_step = self.request.POST.get('wizard_goto_step', None)

        form = self.get_form(data=self.request.POST, files=self.request.FILES)

        form_valid = self.validate(self.steps.current, form)

        if not form_valid and not wizard_goto_step:
            # Re-render same step
            return self.render(form)

        return super().post(*args, **kwargs)
