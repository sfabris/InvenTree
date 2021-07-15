{% load i18n %}
{% load inventree_extras %}

/**
 *
 * This file contains code for rendering (and managing) HTML forms
 * which are served via the django-drf API.
 *
 * The django DRF library provides an OPTIONS method for each API endpoint,
 * which allows us to introspect the available fields at any given endpoint.
 *
 * The OPTIONS method provides the following information for each available field:
 *
 * - Field name
 * - Field label (translated)
 * - Field help text (translated)
 * - Field type
 * - Read / write status
 * - Field required status
 * - min_value / max_value
 *
 */

/*
 * Return true if the OPTIONS specify that the user
 * can perform a GET method at the endpoint.
 */
function canView(OPTIONS) {
    
    if ('actions' in OPTIONS) {
        return ('GET' in OPTIONS.actions);
    } else {
        return false;
    }
}


/*
 * Return true if the OPTIONS specify that the user
 * can perform a POST method at the endpoint
 */
function canCreate(OPTIONS) {

    if ('actions' in OPTIONS) {
        return ('POST' in OPTIONS.actions);
    } else {
        return false;
    }
}


/*
 * Return true if the OPTIONS specify that the user
 * can perform a PUT or PATCH method at the endpoint
 */
function canChange(OPTIONS) {
    
    if ('actions' in OPTIONS) {
        return ('PUT' in OPTIONS.actions || 'PATCH' in OPTIONS.actions);
    } else {
        return false;
    }
}


/*
 * Return true if the OPTIONS specify that the user
 * can perform a DELETE method at the endpoint
 */
function canDelete(OPTIONS) {

    if ('actions' in OPTIONS) {
        return ('DELETE' in OPTIONS.actions);
    } else {
        return false;
    }
}


/*
 * Get the API endpoint options at the provided URL,
 * using a HTTP options request.
 */
function getApiEndpointOptions(url, callback, options) {

    // Return the ajax request object
    $.ajax({
        url: url,
        type: 'OPTIONS',
        contentType: 'application/json',
        dataType: 'json',
        accepts: {
            json: 'application/json',
        },
        success: callback,
        error: function(request, status, error) {
            // TODO: Handle error
            console.log(`ERROR in getApiEndpointOptions at '${url}'`);
        }
    });
}


/*
 * Construct a 'creation' (POST) form, to create a new model in the database.
 * 
 * arguments:
 * - fields: The 'actions' object provided by the OPTIONS endpoint
 * 
 * options:
 * - 
 */
function constructCreateForm(fields, options) {

    // Check if default values were provided for any fields
    for (const name in fields) {
    
        var field = fields[name];

        var field_options = options.fields[name] || {};

        // If a 'value' is not provided for the field,
        if (field.value == null) {
            
            if ('value' in field_options) {
                // Client has specified the default value for the field
                field.value = field_options.value;
            } else if (field.default != null) {
                // OPTIONS endpoint provided default value for this field
                field.value = field.default;
            }
        }
    }

    // We should have enough information to create the form!
    constructFormBody(fields, options);
}


/*
 * Construct a 'change' (PATCH) form, to create a new model in the database.
 * 
 * arguments:
 * - fields: The 'actions' object provided by the OPTIONS endpoint
 * 
 * options:
 * - 
 */
function constructChangeForm(fields, options) {

    // Request existing data from the API endpoint
    $.ajax({
        url: options.url,
        type: 'GET',
        contentType: 'application/json',
        dataType: 'json',
        accepts: {
            json: 'application/json',
        },
        success: function(data) {

            // Push existing 'value' to each field
            for (const field in data) {

                if (field in fields) {
                    fields[field].value = data[field];
                }
            }

            // Store the entire data object
            options.instance = data;

            constructFormBody(fields, options);
        },
        error: function(request, status, error) {
            // TODO: Handle error here
            console.log(`ERROR in constructChangeForm at '${options.url}'`);
        }
    });
}


/*
 * Construct a 'delete' form, to remove a model instance from the database.
 * 
 * arguments:
 * - fields: The 'actions' object provided by the OPTIONS request
 * - options: The 'options' object provided by the client
 */
function constructDeleteForm(fields, options) {

    // Force the "confirm" property if not set
    if (!('confirm' in options)) {
        options.confirm = true;
    }

    // Request existing data from the API endpoint
    // This data can be used to render some information on the form
    $.ajax({
        url: options.url,
        type: 'GET',
        contentType: 'application/json',
        dataType: 'json',
        accepts: {
            json: 'application/json',
        },
        success: function(data) {

            // Store the instance data
            options.instance = data;

            constructFormBody(fields, options);
        },
        error: function(request, status, error) {
            // TODO: Handle error here
            console.log(`ERROR in constructDeleteForm at '${options.url}`);
        }
    });
}


/*
 * Request API OPTIONS data from the server,
 * and construct a modal form based on the response.
 * 
 * url: API URL which defines form data
 * options:
 * - method: The HTTP method e.g. 'PUT', 'POST', 'DELETE' (default='PATCH')
 * - title: The form title
 * - submitText: Text for the "submit" button
 * - closeText: Text for the "close" button
 * - fields: list of fields to display, with the following options
 *      - filters: API query filters
 *      - onEdit: callback when field is edited
 *      - secondary: Define a secondary modal form for this field
 *      - label: Specify custom label
 *      - help_text: Specify custom help_text
 *      - placeholder: Specify custom placeholder text
 *      - value: Specify initial value
 *      - hidden: Set to true to hide the field
 *      - icon: font-awesome icon to display before the field
 *      - prefix: Custom HTML prefix to display before the field
 * - focus: Name of field to focus on when modal is displayed
 * - preventClose: Set to true to prevent form from closing on success
 * - onSuccess: callback function when form action is successful
 * - follow: If a 'url' is provided by the API on success, redirect to it
 * - redirect: A URL to redirect to after form success
 * - reload: Set to true to reload the current page after form success
 * - confirm: Set to true to require a "confirm" button
 * - confirmText: Text for confirm button (default = "Confirm")
 * 
 */
function constructForm(url, options) {

    // Save the URL 
    options.url = url;

    // Default HTTP method
    options.method = options.method || 'PATCH';

    // Request OPTIONS endpoint from the API
    getApiEndpointOptions(url, function(OPTIONS) {

        /*
         * Determine what "type" of form we want to construct,
         * based on the requested action.
         * 
         * First we must determine if the user has the correct permissions!
         */

        switch (options.method) {
            case 'POST':
                if (canCreate(OPTIONS)) {
                    constructCreateForm(OPTIONS.actions.POST, options);
                } else {
                    // User does not have permission to POST to the endpoint
                    showAlertDialog(
                        '{% trans "Action Prohibited" %}',
                        '{% trans "Create operation not allowed" %}'
                    );
                    console.log(`'POST action unavailable at ${url}`);
                }
                break;
            case 'PUT':
            case 'PATCH':
                if (canChange(OPTIONS)) {
                    constructChangeForm(OPTIONS.actions.PUT, options);
                } else {
                    // User does not have permission to PUT/PATCH to the endpoint
                    showAlertDialog(
                        '{% trans "Action Prohibited" %}',
                        '{% trans "Update operation not allowed" %}'
                    );
                    console.log(`${options.method} action unavailable at ${url}`);
                }
                break;
            case 'DELETE':
                if (canDelete(OPTIONS)) {
                    constructDeleteForm(OPTIONS.actions.DELETE, options);
                } else {
                    // User does not have permission to DELETE to the endpoint
                    showAlertDialog(
                        '{% trans "Action Prohibited" %}',
                        '{% trans "Delete operation not allowed" %}'
                    );
                    console.log(`DELETE action unavailable at ${url}`);
                }
                break;
            case 'GET':
                if (canView(OPTIONS)) {
                    // TODO?
                } else {
                    // User does not have permission to GET to the endpoint
                    showAlertDialog(
                        '{% trans "Action Prohibited" %}',
                        '{% trans "View operation not allowed" %}'
                    );
                    console.log(`GET action unavailable at ${url}`);
                }
                break;
            default:
                console.log(`constructForm() called with invalid method '${options.method}'`);
                break;
        }
    });
}


/*
 * Construct a modal form based on the provided options
 * 
 * arguments:
 * - fields: The endpoint description returned from the OPTIONS request
 * - options: form options object provided by the client.
 */
function constructFormBody(fields, options) {

    var html = '';

    // Client must provide set of fields to be displayed,
    // otherwise *all* fields will be displayed
    var displayed_fields = options.fields || fields;

    // Provide each field object with its own name
    for(field in fields) {
        fields[field].name = field;

        var field_options = displayed_fields[field];

        // Copy custom options across to the fields object
        if (field_options) {

            // Override existing query filters (if provided!)
            fields[field].filters = Object.assign(fields[field].filters || {}, field_options.filters);

            // TODO: Refactor the following code with Object.assign (see above)

            // Secondary modal options
            fields[field].secondary = field_options.secondary;

            // Edit callback
            fields[field].onEdit = field_options.onEdit;

            fields[field].multiline = field_options.multiline;

            // Custom help_text
            if (field_options.help_text) {
                fields[field].help_text = field_options.help_text;
            }

            // Custom label
            if (field_options.label) {
                fields[field].label = field_options.label;
            }

            // Custom placeholder
            if (field_options.placeholder) {
                fields[field].placeholder = field_options.placeholder;
            }

            // Field prefix
            if (field_options.prefix) {
                fields[field].prefix = field_options.prefix;
            } else if (field_options.icon) {
                // Specify icon like 'fa-user'
                fields[field].prefix = `<span class='fas ${field_options.icon}'></span>`;
            }

            fields[field].hidden = field_options.hidden;

            if (field_options.read_only != null) {
                fields[field].read_only = field_options.read_only;
            }
        }
    }

    // Construct an ordered list of field names
    var field_names = [];

    for (var name in displayed_fields) {

        field_names.push(name);

        // Field not specified in the API, but the client wishes to add it!
        if (!(name in fields)) {
            fields[name] = displayed_fields[name];
        }
    }

    // Push the ordered field names into the options,
    // allowing successive functions to access them.
    options.field_names = field_names;

    // Render selected fields

    for (var idx = 0; idx < field_names.length; idx++) {

        var name = field_names[idx];

        var field = fields[name];

        switch (field.type) {
            // Skip field types which are simply not supported
            case 'nested object':
                continue;
            default:
                break;
        }
        
        html += constructField(name, field, options);
    }

    // TODO: Dynamically create the modals,
    //       so that we can have an infinite number of stacks!

    // Create a new modal if one does not exists
    if (!options.modal) {
        options.modal = createNewModal(options);
    }

    var modal = options.modal;

    modalEnable(modal, true);
    
    // Insert generated form content
    $(modal).find('#form-content').html(html);

    if (options.preFormContent) {
        $(modal).find('#pre-form-content').html(options.preFormContent);
    }

    if (options.postFormContent) {
        $(modal).find('#post-form-content').html(options.postFormContent);
    }
    
    // Clear any existing buttons from the modal
    $(modal).find('#modal-footer-buttons').html('');

    // Insert "confirm" button (if required)
    if (options.confirm) {
        insertConfirmButton(options);
    }

    // Display the modal
    $(modal).modal('show');

    updateFieldValues(fields, options);

    // Setup related fields
    initializeRelatedFields(fields, options);

    // Attach edit callbacks (if required)
    addFieldCallbacks(fields, options);

    // Attach clear callbacks (if required)
    addClearCallbacks(fields, options);

    attachToggle(modal);

    $(modal + ' .select2-container').addClass('select-full-width');
    $(modal + ' .select2-container').css('width', '100%');

    modalShowSubmitButton(modal, true);

    $(modal).on('click', '#modal-form-submit', function() {

        // Immediately disable the "submit" button,
        // to prevent the form being submitted multiple times!
        $(options.modal).find('#modal-form-submit').prop('disabled', true);

        // Run custom code before normal form submission
        if (options.beforeSubmit) {
            options.beforeSubmit(fields, options);
        }

        // Run custom code instead of normal form submission
        if (options.onSubmit) {
            options.onSubmit(fields, options);
        } else {
            submitFormData(fields, options);
        }
    });
}


// Add a "confirm" checkbox to the modal
// The "submit" button will be disabled unless "confirm" is checked
function insertConfirmButton(options) {

    var message = options.confirmMessage || '{% trans "Confirm" %}';

    var confirm = `
    <span style='float: left;'>
        ${message}
        <input id='modal-confirm' name='confirm' type='checkbox'>
    </span>`;

    $(options.modal).find('#modal-footer-buttons').append(confirm);

    // Disable the 'submit' button
    $(options.modal).find('#modal-form-submit').prop('disabled', true);

    // Trigger event
    $(options.modal).find('#modal-confirm').change(function() {
        var enabled = this.checked;

        $(options.modal).find('#modal-form-submit').prop('disabled', !enabled);
    });
}


/*
 * Submit form data to the server.
 * 
 */
function submitFormData(fields, options) {

    // Form data to be uploaded to the server
    // Only used if file / image upload is required
    var form_data = new FormData();

    var data = {};

    var has_files = false;

    // Extract values for each field
    options.field_names.forEach(function(name) {

        var field = fields[name] || null;

        if (field) {

            var value = getFormFieldValue(name, field, options);

            // Handle file inputs
            if (field.type == 'image upload' || field.type == 'file upload') {

                var field_el = $(options.modal).find(`#id_${name}`)[0];

                var field_files = field_el.files;

                if (field_files.length > 0) {
                    // One file per field, please!
                    var file = field_files[0];

                    form_data.append(name, file);
                    
                    has_files = true;
                }
            } else {

                // Normal field (not a file or image)
                form_data.append(name, value);

                data[name] = value;
            }
        } else {
            console.log(`WARNING: Could not find field matching '${name}'`);
        }
    });

    var upload_func = inventreePut;

    if (has_files) {
        upload_func = inventreeFormDataUpload;
        data = form_data;
    }

    // Submit data
    upload_func(
        options.url,
        data,
        {
            method: options.method,
            success: function(response, status) {
                handleFormSuccess(response, options);
            },
            error: function(xhr, status, thrownError) {
                
                switch (xhr.status) {
                    case 400:   // Bad request
                        handleFormErrors(xhr.responseJSON, fields, options);
                        break;
                    default:
                        $(options.modal).modal('hide');
                        showApiError(xhr);
                        break;
                }
            }
        }
    );
}


/*
 * Update (set) the field values based on the specified data.
 *
 * Iterate through each of the displayed fields,
 * and set the 'val' attribute of each one.
 *
 */
function updateFieldValues(fields, options) {
  
    for (var idx = 0; idx < options.field_names.length; idx++) {

        var name = options.field_names[idx];

        var field = fields[name] || null;

        if (field == null) { continue; }

        var value = field.value;

        if (value == null) {
            value = field.default;
        }

        if (value == null) { continue; }

        updateFieldValue(name, value, field, options);
    }
}


function updateFieldValue(name, value, field, options) {
    var el = $(options.modal).find(`#id_${name}`);

    switch (field.type) {
        case 'boolean':
            el.prop('checked', value);
            break;
        case 'related field':
            // Clear?
            if (value == null && !field.required) {
                el.val(null).trigger('change');
            }
            // TODO - Specify an actual value!
            break;
        case 'file upload':
        case 'image upload':
            break;
        default:
            el.val(value);
            break;
    }
}


/*
 * Extract and field value before sending back to the server
 *
 * arguments:
 * - name: The name of the field
 * - field: The field specification provided from the OPTIONS request
 * - options: The original options object provided by the client
 */
function getFormFieldValue(name, field, options) {

    // Find the HTML element
    var el = $(options.modal).find(`#id_${name}`);

    if (!el) {
        return null;
    }

    var value = null;

    switch (field.type) {
        case 'boolean':
            value = el.is(":checked");
            break;
        case 'date':
        case 'datetime':
            value = el.val();

            // Ensure empty values are sent as nulls
            if (!value || value.length == 0) {
                value = null;
            }
            break;
        default:
            value = el.val();
            break;
    }

    return value;
}


/*
 * Handle successful form posting
 * 
 * arguments:
 * - response: The JSON response object from the server
 * - options: The original options object provided by the client
 */
function handleFormSuccess(response, options) {

    // Close the modal
    if (!options.preventClose) {
        // Note: The modal will be deleted automatically after closing
        $(options.modal).modal('hide');
    }

    // Display any required messages
    // Should we show alerts immediately or cache them?
    var cache = (options.follow && response.url) || options.redirect || options.reload;

    // Display any messages
    if (response && response.success) {
        showAlertOrCache("alert-success", response.success, cache);
    }
    
    if (response && response.info) {
        showAlertOrCache("alert-info", response.info, cache);
    }

    if (response && response.warning) {
        showAlertOrCache("alert-warning", response.warning, cache);
    }

    if (response && response.danger) {
        showAlertOrCache("alert-danger", response.danger, cache);
    }

    if (options.onSuccess) {
        // Callback function
        options.onSuccess(response, options);
    }

    if (options.follow && response.url) {
        // Follow the returned URL
        window.location.href = response.url;
    } else if (options.reload) {
        // Reload the current page
        location.reload();
    } else if (options.redirect) {
        // Redirect to a specified URL
        window.location.href = options.redirect;
    }
}



/*
 * Remove all error text items from the form
 */
function clearFormErrors(options) {

    // Remove the individual error messages
    $(options.modal).find('.form-error-message').remove();

    // Remove the "has error" class
    $(options.modal).find('.has-error').removeClass('has-error');

    // Hide the 'non field errors'
    $(options.modal).find('#non-field-errors').html('');
}


/*
 * Display form error messages as returned from the server.
 * 
 * arguments:
 * - errors: The JSON error response from the server
 * - fields: The form data object
 * - options: Form options provided by the client
 */
function handleFormErrors(errors, fields, options) {

    // Reset the status of the "submit" button
    $(options.modal).find('#modal-form-submit').prop('disabled', false);

    // Remove any existing error messages from the form
    clearFormErrors(options);

    var non_field_errors = $(options.modal).find('#non-field-errors');

    non_field_errors.append(
        `<div class='alert alert-block alert-danger'>
            <b>{% trans "Form errors exist" %}</b>
        </div>`
    );

    // Non-field errors?
    if ('non_field_errors' in errors) {

        var nfe = errors.non_field_errors;

        for (var idx = 0; idx < nfe.length; idx++) {
            var err = nfe[idx];

            var html = `
            <div class='alert alert-block alert-danger'>
                ${err}
            </div>`;

            non_field_errors.append(html);
        }
    }

    for (field_name in errors) {

        // Add the 'has-error' class
        $(options.modal).find(`#div_id_${field_name}`).addClass('has-error');

        var field_dom = $(options.modal).find(`#errors-${field_name}`); // $(options.modal).find(`#id_${field_name}`);

        var field_errors = errors[field_name];

        // Add an entry for each returned error message
        for (var idx = field_errors.length-1; idx >= 0; idx--) {

            var error_text = field_errors[idx];

            var html = `
            <span id='error_${idx+1}_id_${field_name}' class='help-block form-error-message'>
                <strong>${error_text}</strong>
            </span>`;

            field_dom.append(html);
        }
    }
}


/*
 * Attach callbacks to specified fields,
 * triggered after the field value is edited.
 * 
 * Callback function is called with arguments (name, field, options)
 */
function addFieldCallbacks(fields, options) {

    for (var idx = 0; idx < options.field_names.length; idx++) {
        
        var name = options.field_names[idx];

        var field = fields[name];

        if (!field || !field.onEdit) continue;

        addFieldCallback(name, field, options);
    }
}


function addFieldCallback(name, field, options) {

    $(options.modal).find(`#id_${name}`).change(function() {
        field.onEdit(name, field, options);
    });
}


function addClearCallbacks(fields, options) {

    for (var idx = 0; idx < options.field_names.length; idx++) {

        var name = options.field_names[idx];

        var field = fields[name];

        if (!field || field.required) continue;

        addClearCallback(name, field, options);
    }
}


function addClearCallback(name, field, options) {

    $(options.modal).find(`#clear_${name}`).click(function() {
        updateFieldValue(name, null, field, options);
    });
}


function initializeRelatedFields(fields, options) {

    var field_names = options.field_names;

    for (var idx = 0; idx < field_names.length; idx++) {

        var name = field_names[idx];

        var field = fields[name] || null;

        if (!field || field.hidden) continue;

        switch (field.type) {
            case 'related field':
                initializeRelatedField(name, field, options);
                break;
            case 'choice':
                initializeChoiceField(name, field, options);
                break;
        }
    }
}


/*
 * Add a button to launch a secondary modal, to create a new modal instance.
 *
 * arguments:
 * - name: The name of the field
 * - field: The field data object
 * - options: The options object provided by the client
 */
function addSecondaryModal(name, field, options) {

    var secondary = field.secondary;

    var html = `
    <span style='float: right;'>
        <div type='button' class='btn btn-primary btn-secondary' title='${secondary.title || secondary.label}' id='btn-new-${name}'>
            ${secondary.label || secondary.title}
        </div>
    </span>`;

    $(options.modal).find(`label[for="id_${name}"]`).append(html);

    // TODO: Launch a callback
    $(options.modal).find(`#btn-new-${name}`).click(function() {

        if (secondary.callback) {
            // A "custom" callback can be specified for the button
            secondary.callback(field, options);
        } else if (secondary.api_url) {
            // By default, a new modal form is created, with the parameters specified
            // The parameters match the "normal" form creation parameters

            secondary.onSuccess = function(data, opts) {
                setRelatedFieldData(name, data, options);
            };

            constructForm(secondary.api_url, secondary);
        }
    });
}


/*
 * Initializea single related-field
 * 
 * argument:
 * - modal: DOM identifier for the modal window
 * - name: name of the field e.g. 'location'
 * - field: Field definition from the OPTIONS request
 * - options: Original options object provided by the client
 */
function initializeRelatedField(name, field, options) {

    if (!field.api_url) {
        // TODO: Provide manual api_url option?
        console.log(`Related field '${name}' missing 'api_url' parameter.`);
        return;
    }

    // Find the select element and attach a select2 to it
    var select = $(options.modal).find(`#id_${name}`);

    // Add a button to launch a 'secondary' modal
    if (field.secondary != null) {
        addSecondaryModal(name, field, options);
    }

    // TODO: Add 'placeholder' support for entry select2 fields

    // limit size for AJAX requests
    var pageSize = options.pageSize || 25;

    select.select2({
        placeholder: '',
        dropdownParent: $(options.modal),
        dropdownAutoWidth: false,
        ajax: {
            url: field.api_url,
            dataType: 'json',
            delay: 250,
            cache: true,
            data: function(params) {

                if (!params.page) {
                    offset = 0;
                } else {
                    offset = (params.page - 1) * pageSize;
                }

                // Custom query filters can be specified against each field
                var query = field.filters || {};

                // Add search and pagination options
                query.search = params.term;
                query.offset = offset;
                query.limit = pageSize;

                return query;
            },
            processResults: function(response) {
                // Convert the returned InvenTree data into select2-friendly format

                var data = [];

                var more = false;

                if ('count' in response && 'results' in response) {
                    // Response is paginated
                    data = response.results;

                    // Any more data available?
                    if (response.next) {
                        more = true;
                    }

                } else {
                    // Non-paginated response
                    data = response;
                }

                // Each 'row' must have the 'id' attribute
                for (var idx = 0; idx < data.length; idx++) {
                    data[idx].id = data[idx].pk;
                }

                // Ref: https://select2.org/data-sources/formats
                var results = {
                    results: data,
                    pagination: {
                        more: more,
                    }
                };

                return results;
            },
        },
        templateResult: function(item, container) {

            // Extract 'instance' data passed through from an initial value
            // Or, use the raw 'item' data as a backup
            var data = item;
            
            if (item.element && item.element.instance) {
                data = item.element.instance;
            }

            if (!data.pk) {
                return $(searching());
            }

            // Custom formatting for the search results
            if (field.model) {
                // If the 'model' is specified, hand it off to the custom model render
                var html = renderModelData(name, field.model, data, field, options);
                return $(html);
            } else {
                // Return a simple renderering
                console.log(`WARNING: templateResult() missing 'field.model' for '${name}'`);
                return `${name} - ${item.id}`;
            }
        },
        templateSelection: function(item, container) {

            // Extract 'instance' data passed through from an initial value
            // Or, use the raw 'item' data as a backup
            var data = item;
            
            if (item.element && item.element.instance) {
                data = item.element.instance;
            }

            if (!data.pk) {
                return field.placeholder || '';
                return $(searching());
            }

            // Custom formatting for selected item
            if (field.model) {
                // If the 'model' is specified, hand it off to the custom model render
                var html = renderModelData(name, field.model, data, field, options);
                return $(html);
            } else {
                // Return a simple renderering
                console.log(`WARNING: templateSelection() missing 'field.model' for '${name}'`);
                return `${name} - ${item.id}`;
            }
        }
    });

    // If a 'value' is already defined, grab the model info from the server
    if (field.value) {
        var pk = field.value;
        var url = `${field.api_url}/${pk}/`.replace('//', '/');

        inventreeGet(url, {}, {
            success: function(data) {
                setRelatedFieldData(name, data, options);
            }
        });
    }
}


/*
 * Set the value of a select2 instace for a "related field",
 * e.g. with data returned from a secondary modal
 * 
 * arguments:
 * - name: The name of the field
 * - data: JSON data representing the model instance
 * - options: The modal form specifications
 */
function setRelatedFieldData(name, data, options) {

    var select = $(options.modal).find(`#id_${name}`);

    var option = new Option(name, data.pk, true, true);

    // Assign the JSON data to the 'instance' attribute,
    // so we can access and render it later
    option.instance = data;

    select.append(option).trigger('change');

    select.trigger({
        type: 'select2:select',
        params: {
            data: data
        }
    });
}


function initializeChoiceField(name, field, options) {

    var select = $(options.modal).find(`#id_${name}`);

    select.select2({
        dropdownAutoWidth: false,
        dropdownParent: $(options.modal),
    });
}


// Render a 'no results' element
function searching() {
    return `<span>{% trans "Searching" %}...</span>`;
}

/*
 * Render a "foreign key" model reference in a select2 instance.
 * Allows custom rendering with access to the entire serialized object.
 * 
 * arguments:
 * - name: The name of the field e.g. 'location'
 * - model: The name of the InvenTree model e.g. 'stockitem'
 * - data: The JSON data representation of the modal instance (GET request)
 * - parameters: The field definition (OPTIONS) request
 * - options: Other options provided at time of modal creation by the client
 */
function renderModelData(name, model, data, parameters, options) {

    if (!data) {
        return parameters.placeholder || '';
    }

    // TODO: Implement this function for various models

    var html = null;

    var renderer = null;

    // Find a custom renderer 
    switch (model) {
        case 'company':
            renderer = renderCompany;
            break;
        case 'stockitem':
            renderer = renderStockItem;
            break;
        case 'stocklocation':
            renderer = renderStockLocation;
            break;
        case 'part':
            renderer = renderPart;
            break;
        case 'partcategory':
            renderer = renderPartCategory;
            break;
        case 'partparametertemplate':
            renderer = renderPartParameterTemplate;
            break;
        case 'supplierpart':
            renderer = renderSupplierPart;
            break;
        case 'build':
            renderer = renderBuild;
            break;
        case 'owner':
            renderer = renderOwner;
            break;
        case 'user':
            renderer = renderUser;
            break;
        default:
            break;
    }
    
    if (renderer != null) {
        html = renderer(name, data, parameters, options);
    }

    if (html != null) {
        return html;
    } else {
        console.log(`ERROR: Rendering not implemented for model '${model}'`);
        // Simple text rendering
        return `${model} - ID ${data.id}`;
    }
}


/*
 * Construct a single form 'field' for rendering in a form.
 * 
 * arguments:
 * - name: The 'name' of the field
 * - parameters: The field parameters supplied by the DRF OPTIONS method
 * 
 * options:
 * - 
 * 
 * The function constructs a fieldset which mostly replicates django "crispy" forms:
 * 
 * - Field name
 * - Field <input> (depends on specified field type)
 * - Field description (help text)
 * - Field errors
 */
function constructField(name, parameters, options) {

    var field_name = `id_${name}`;

    // Hidden inputs are rendered without label / help text / etc
    if (parameters.hidden) {
        return constructHiddenInput(name, parameters, options);
    }

    var form_classes = 'form-group';

    if (parameters.errors) {
        form_classes += ' has-error';
    }

    var html = `<div id='div_${field_name}' class='${form_classes}'>`;

    // Add a label
    html += constructLabel(name, parameters);

    html += `<div class='controls'>`;

    // Does this input deserve "extra" decorators?
    var extra = parameters.prefix != null;
    
    // Some fields can have 'clear' inputs associated with them
    if (!parameters.required && !parameters.read_only) {
        switch (parameters.type) {
            case 'string':
            case 'url':
            case 'email':
            case 'integer':
            case 'float':
            case 'decimal':
            case 'related field':
            case 'date':
                extra = true;
                break;
            default:
                break;
        }
    }
    
    if (extra) {
        html += `<div class='input-group'>`;
    
        if (parameters.prefix) {
            html += `<span class='input-group-addon'>${parameters.prefix}</span>`;
        }
    }

    html += constructInput(name, parameters, options);

    if (extra) {

        if (!parameters.required) {
            html += `
            <span class='input-group-addon form-clear' id='clear_${name}' title='{% trans "Clear input" %}'>
                <span class='icon-red fas fa-backspace'></span>
            </span>`;
        }

        html += `</div>`;   // input-group
    }

    // Div for error messages
    html += `<div id='errors-${name}'></div>`;

    if (parameters.help_text) {
        html += constructHelpText(name, parameters, options);
    }

    html += `</div>`;   // controls
    html += `</div>`;   // form-group
    
    return html;
}


/*
 * Construct a 'label' div
 *
 * arguments:
 * - name: The name of the field
 * - required: Is this a required field?
 */
function constructLabel(name, parameters) {

    var label_classes = 'control-label';

    if (parameters.required) {
        label_classes += ' requiredField';
    }

    var html = `<label class='${label_classes}' for='id_${name}'>`;
    
    if (parameters.label) {
        html += `${parameters.label}`;
    } else {
        html += `${name}`;
    }
    
    if (parameters.required) {
        html += `<span class='asteriskField'>*</span>`;
    }
    
    html += `</label>`;

    return html;
}


/*
 * Construct a form input based on the field parameters
 * 
 * arguments:
 * - name: The name of the field
 * - parameters: Field parameters returned by the OPTIONS method
 * 
 */
function constructInput(name, parameters, options) {

    var html = '';

    var func = null;

    switch (parameters.type) {
        case 'boolean':
            func = constructCheckboxInput;
            break;
        case 'string':
        case 'url':
        case 'email':
            func = constructTextInput;
            break;
        case 'integer':
        case 'float':
        case 'decimal':
            func = constructNumberInput;
            break;
        case 'choice':
            func = constructChoiceInput;
            break;
        case 'related field':
            func = constructRelatedFieldInput;
            break;
        case 'image upload':
        case 'file upload':
            func = constructFileUploadInput;
            break;
        case 'date':
            func = constructDateInput;
            break;
        default:
            // Unsupported field type!
            break;
        }
        
    if (func != null) {
        html = func(name, parameters, options);
    } else {
        console.log(`WARNING: Unhandled form field type: '${parameters.type}'`);
    }

    return html;
}


// Construct a set of default input options which apply to all input types
function constructInputOptions(name, classes, type, parameters) {

    var opts = [];

    opts.push(`id='id_${name}'`);

    opts.push(`class='${classes}'`);

    opts.push(`name='${name}'`);

    opts.push(`type='${type}'`);

    // Read only?
    if (parameters.read_only) {
        opts.push(`readonly=''`);
    }

    if (parameters.value != null) {
        // Existing value?
        opts.push(`value='${parameters.value}'`);
    } else if (parameters.default != null) {
        // Otherwise, a defualt value?
        opts.push(`value='${parameters.default}'`);
    }

    // Maximum input length
    if (parameters.max_length != null) {
        opts.push(`maxlength='${parameters.max_length}'`);
    }

    // Minimum input length
    if (parameters.min_length != null) {
        opts.push(`minlength='${parameters.min_length}'`);
    }

    // Maximum value
    if (parameters.max_value != null) {
        opts.push(`max='${parameters.max_value}'`);
    }

    // Minimum value
    if (parameters.min_value != null) {
        opts.push(`min='${parameters.min_value}'`);
    }

    // Field is required?
    if (parameters.required) {
        opts.push(`required=''`);
    }

    // Custom mouseover title?
    if (parameters.title != null) {
        opts.push(`title='${parameters.title}'`);
    }

    // Placeholder?
    if (parameters.placeholder != null) {
        opts.push(`placeholder='${parameters.placeholder}'`);
    }

    if (parameters.multiline) {
        return `<textarea ${opts.join(' ')}></textarea>`;
    } else {
        return `<input ${opts.join(' ')}>`;
    }
}


// Construct a "hidden" input
function constructHiddenInput(name, parameters, options) {

    return constructInputOptions(
        name,
        'hiddeninput',
        'hidden',
        parameters
    );
}


// Construct a "checkbox" input
function constructCheckboxInput(name, parameters, options) {

    return constructInputOptions(
        name,
        'checkboxinput',
        'checkbox',
        parameters
    );
}


// Construct a "text" input
function constructTextInput(name, parameters, options) {

    var classes = '';
    var type = '';

    switch (parameters.type) {
        default:
            classes = 'textinput textInput form-control';
            type = 'text';
            break;
        case 'url':
            classes = 'urlinput form-control';
            type = 'url';
            break;
        case 'email':
            classes = 'emailinput form-control';
            type = 'email';
            break;
    }

    return constructInputOptions(
        name,
        classes,
        type,
        parameters
    );
}


// Construct a "number" field
function constructNumberInput(name, parameters, options) {

    return constructInputOptions(
        name,
        'numberinput form-control',
        'number',
        parameters
    );
}


// Construct a "choice" input
function constructChoiceInput(name, parameters, options) {

    var html = `<select id='id_${name}' class='select form-control' name='${name}'>`;

    var choices = parameters.choices || [];

    for (var idx = 0; idx < choices.length; idx++) {

        var choice = choices[idx];

        var selected = '';

        if (parameters.value && parameters.value == choice.value) {
            selected = ` selected=''`;
        }

        html += `<option value='${choice.value}'${selected}>`;
        html += `${choice.display_name}`;
        html += `</option>`;
    }

    html += `</select>`;

    return html;
}


/*
 * Construct a "related field" input.
 * This will create a "select" input which will then, (after form is loaded),
 * be converted into a select2 input.
 * This will then be served custom data from the API (as required)...
 */
function constructRelatedFieldInput(name, parameters, options) {

    var html = `<select id='id_${name}' class='select form-control' name='${name}'></select>`;

    // Don't load any options - they will be filled via an AJAX request

    return html;
}


/*
 * Construct a field for file upload
 */
function constructFileUploadInput(name, parameters, options) {

    var cls = 'clearablefileinput';

    if (parameters.required) {
        cls = 'fileinput';
    }

    return constructInputOptions(
        name,
        cls,
        'file',
        parameters
    );
}


/*
 * Construct a field for a date input
 */
function constructDateInput(name, parameters, options) {

    return constructInputOptions(
        name,
        'dateinput form-control',
        'date',
        parameters
    );
}


/*
 * Construct a 'help text' div based on the field parameters
 * 
 * arguments:
 * - name: The name of the field
 * - parameters: Field parameters returned by the OPTIONS method
 *  
 */
function constructHelpText(name, parameters, options) {
    
    var html = `<div id='hint_id_${name}' class='help-block'><i>${parameters.help_text}</i></div>`;

    return html;
}