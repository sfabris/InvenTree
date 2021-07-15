{% load i18n %}
{% load inventree_extras %}

var jQuery = window.$;

// using jQuery
function getCookie(name) {
    var cookieValue = null;
    if (document.cookie && document.cookie != '') {
        var cookies = document.cookie.split(';');
        for (var i = 0; i < cookies.length; i++) {
            var cookie = jQuery.trim(cookies[i]);
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) == (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

function inventreeGet(url, filters={}, options={}) {

    // Middleware token required for data update
    //var csrftoken = jQuery("[name=csrfmiddlewaretoken]").val();
    var csrftoken = getCookie('csrftoken');

    return $.ajax({
        beforeSend: function(xhr, settings) {
            xhr.setRequestHeader('X-CSRFToken', csrftoken);
        },
        url: url,
        type: 'GET',
        data: filters,
        dataType: 'json',
        contentType: 'application/json',
        success: function(response) {
            if (options.success) {
                options.success(response);
            }
        },
        error: function(xhr, ajaxOptions, thrownError) {
            console.error('Error on GET at ' + url);
            console.error(thrownError);
            if (options.error) {
                options.error({
                    error: thrownError
                });
            }
        }
    });
}

function inventreeFormDataUpload(url, data, options={}) {
    /* Upload via AJAX using the FormData approach.
     * 
     * Note that the following AJAX parameters are required for FormData upload
     * 
     * processData: false
     * contentType: false
     */

    // CSRF cookie token
    var csrftoken = getCookie('csrftoken');

    return $.ajax({
        beforeSend: function(xhr, settings) {
            xhr.setRequestHeader('X-CSRFToken', csrftoken);
        },
        url: url,
        method: options.method || 'POST',
        data: data,
        processData: false,
        contentType: false,
        success: function(data, status, xhr) {
            if (options.success) {
                options.success(data, status, xhr);
            }
        },
        error: function(xhr, status, error) {
            console.log('Form data upload failure: ' + status);

            if (options.error) {
                options.error(xhr, status, error);
            }
        }
    });
}

function inventreePut(url, data={}, options={}) {

    var method = options.method || 'PUT';

    // Middleware token required for data update
    //var csrftoken = jQuery("[name=csrfmiddlewaretoken]").val();
    var csrftoken = getCookie('csrftoken');

    return $.ajax({
        beforeSend: function(xhr, settings) {
            xhr.setRequestHeader('X-CSRFToken', csrftoken);
        },
        url: url,
        type: method,
        data: JSON.stringify(data),
        dataType: 'json',
        contentType: 'application/json',
        success: function(response, status) {
            if (options.success) {
                options.success(response, status);
            }
            if (options.reloadOnSuccess) {
                location.reload();
            }
        },
        error: function(xhr, ajaxOptions, thrownError) {
            if (options.error) {
                options.error(xhr, ajaxOptions, thrownError);
            } else {
                console.error(`Error on ${method} to '${url}' - STATUS ${xhr.status}`);
                console.error(thrownError);
            }
        },
        complete: function(xhr, status) {
            if (options.complete) {
                options.complete(xhr, status);
            }
        }
    });
}


function inventreeDelete(url, options={}) {
    /*
     * Delete a record
     */

    options = options || {};

    options.method = 'DELETE';

    inventreePut(url, {}, options);

}


function showApiError(xhr) {

    var title = null;
    var message = null;

    switch (xhr.status) {
    case 0:     // No response
        title = '{% trans "No Response" %}';
        message = '{% trans "No response from the InvenTree server" %}';
        break;
    case 400:   // Bad request
        // Note: Normally error code 400 is handled separately,
        //       and should now be shown here!
        title = '{% trans "Error 400: Bad request" %}';
        message = '{% trans "API request returned error code 400" %}';
        break;
    case 401:   // Not authenticated
        title = '{% trans "Error 401: Not Authenticated" %}';
        message = '{% trans "Authentication credentials not supplied" %}';
        break;
    case 403:   // Permission denied
        title = '{% trans "Error 403: Permission Denied" %}';
        message = '{% trans "You do not have the required permissions to access this function" %}';
        break;
    case 404:   // Resource not found
        title = '{% trans "Error 404: Resource Not Found" %}';
        message = '{% trans "The requested resource could not be located on the server" %}';
        break;
    case 408:   // Timeout
        title = '{% trans "Error 408: Timeout" %}';
        message = '{% trans "Connection timeout while requesting data from server" %}';
        break;
    default:
        title = '{% trans "Unhandled Error Code" %}';
        message = `{% trans "Error code" %}: ${xhr.status}`;
        break;
    }

    message += "<hr>";
    message += renderErrorMessage(xhr);

    showAlertDialog(title, message);
}