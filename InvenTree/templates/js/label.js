{% load i18n %}

function printStockItemLabels(items, options={}) {
    /**
     * Print stock item labels for the given stock items
     */

    if (items.length == 0) {
        showAlertDialog(
            '{% trans "Select Stock Items" %}',
            '{% trans "Stock item(s) must be selected before printing labels" %}'
        );

        return;
    }

    // Request available labels from the server
    inventreeGet(
        '{% url "api-stockitem-label-list" %}',
        {
            enabled: true,
            items: items,
        },
        {
            success: function(response) {

                if (response.length == 0) {
                    showAlertDialog(
                        '{% trans "No Labels Found" %}',
                        '{% trans "No labels found which match selected stock item(s)" %}',
                    );

                    return;
                }

                // Select label to print
                selectLabel(
                    response,
                    items,
                    {
                        success: function(pk) {
                            var href = `/api/label/stock/${pk}/print/?`;

                            items.forEach(function(item) {
                                href += `items[]=${item}&`;
                            });

                            window.location.href = href;
                        }
                    }
                );
            }
        }
    );
}

function printStockLocationLabels(locations, options={}) {

    if (locations.length == 0) {
        showAlertDialog(
            '{% trans "Select Stock Locations" %}',
            '{% trans "Stock location(s) must be selected before printing labels" %}'
        );

        return;
    }

    // Request available labels from the server
    inventreeGet(
        '{% url "api-stocklocation-label-list" %}',
        {
            enabled: true,
            locations: locations,
        },
        {
            success: function(response) {
                if (response.length == 0) {
                    showAlertDialog(
                        '{% trans "No Labels Found" %}',
                        '{% trans "No labels found which match selected stock location(s)" %}',
                    );

                    return;
                }

                // Select label to print
                selectLabel(
                    response,
                    locations,
                    {
                        success: function(pk) {
                            var href = `/api/label/location/${pk}/print/?`;

                            locations.forEach(function(location) {
                                href += `locations[]=${location}&`;
                            });

                            window.location.href = href;
                        }
                    }
                );
            }
        }
    )
}


function selectLabel(labels, items, options={}) {
    /**
     * Present the user with the available labels,
     * and allow them to select which label to print.
     * 
     * The intent is that the available labels have been requested
     * (via AJAX) from the server.
     */

    // If only a single label template is provided,
    // just run with that!

    if (labels.length == 1) {
        if (options.success) {
            options.success(labels[0].pk);
        }

        return;
    }


    var modal = options.modal || '#modal-form';

    var label_list = makeOptionsList(
        labels,
        function(item) {
            var text = item.name;

            if (item.description) {
                text += ` - ${item.description}`;
            }

            return text;
        },
        function(item) {
            return item.pk;
        }
    );

    // Construct form
    var html = '';

    if (items.length > 0) {

        html += `
        <div class='alert alert-block alert-info'>
        ${items.length} {% trans "stock items selected" %}
        </div>`;
    }

    html += `
    <form method='post' action='' class='js-modal-form' enctype='multipart/form-data'>
        <div class='form-group'>
            <label class='control-label requiredField' for='id_label'>
            {% trans "Select Label" %}
            </label>
            <div class='controls'>
                <select id='id_label' class='select form-control name='label'>
                    ${label_list}
                </select>
            </div>
        </div>
    </form>`;

    openModal({
        modal: modal,
    });

    modalEnable(modal, true);
    modalSetTitle(modal, '{% trans "Select Label Template" %}');
    modalSetContent(modal, html);

    attachSelect(modal);

    modalSubmit(modal, function() {

        var label = $(modal).find('#id_label');

        var pk = label.val();

        closeModal(modal);

        if (options.success) {
            options.success(pk);
        }
    });
}
