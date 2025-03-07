{% load i18n %}
{% load inventree_extras %}
{% load status_codes %}

/* globals
    attachSelect,
    attachToggle,
    blankImage,
    enableField,
    clearField,
    clearFieldOptions,
    closeModal,
    constructFormBody,
    constructNumberInput,
    createNewModal,
    getFormFieldValue,
    global_settings,
    handleFormErrors,
    imageHoverIcon,
    inventreeDelete,
    inventreeGet,
    inventreePut,
    launchModalForm,
    linkButtonsToSelection,
    loadTableFilters,
    makeIconBadge,
    makeIconButton,
    makeOptionsList,
    makePartIcons,
    modalEnable,
    modalSetContent,
    modalSetTitle,
    modalSubmit,
    moment,
    openModal,
    printStockItemLabels,
    printTestReports,
    renderLink,
    reloadFieldOptions,
    scanItemsIntoLocation,
    showAlertDialog,
    setFieldValue,
    setupFilterList,
    showApiError,
    stockStatusDisplay,
*/

/* exported
    createNewStockItem,
    exportStock,
    loadInstalledInTable,
    loadStockLocationTable,
    loadStockTable,
    loadStockTestResultsTable,
    loadStockTrackingTable,
    loadTableFilters,
    locationFields,
    removeStockRow,
    stockStatusCodes,
*/


function locationFields() {
    return {
        parent: {
            help_text: '{% trans "Parent stock location" %}',
        },
        name: {},
        description: {},
    };
}


/* Stock API functions
 * Requires api.js to be loaded first
 */

function stockStatusCodes() {
    return [
        {% for code in StockStatus.list %}
        {
            key: {{ code.key }},
            text: '{{ code.value }}',
        },
        {% endfor %}
    ];
}


/*
 * Export stock table
 */
function exportStock(params={}) {

    constructFormBody({}, {
        title: '{% trans "Export Stock" %}',
        fields: {
            format: {
                label: '{% trans "Format" %}',
                help_text: '{% trans "Select file format" %}',
                required: true,
                type: 'choice',
                value: 'csv',
                choices: [
                    {
                        value: 'csv',
                        display_name: 'CSV',
                    },
                    {
                        value: 'tsv',
                        display_name: 'TSV',
                    },
                    {
                        value: 'xls',
                        display_name: 'XLS',
                    },
                    {
                        value: 'xlsx',
                        display_name: 'XLSX',
                    },
                ],
            },
            sublocations: {
                label: '{% trans "Include Sublocations" %}',
                help_text: '{% trans "Include stock items in sublocations" %}',
                type: 'boolean',
                value: 'true',
            }
        },
        onSubmit: function(fields, form_options) {

            var format = getFormFieldValue('format', fields['format'], form_options);
            var cascade = getFormFieldValue('sublocations', fields['sublocations'], form_options);

            // Hide the modal
            $(form_options.modal).modal('hide');

            var url = `{% url "stock-export" %}?format=${format}&cascade=${cascade}`;

            for (var key in params) {
                url += `&${key}=${params[key]}`;
            }

            console.log(url);
            location.href = url;
        }
    });
}


/**
 * Perform stock adjustments
 */
function adjustStock(action, items, options={}) {

    var formTitle = 'Form Title Here';
    var actionTitle = null;

    // API url
    var url = null;

    var specifyLocation = false;
    var allowSerializedStock = false;

    switch (action) {
    case 'move':
        formTitle = '{% trans "Transfer Stock" %}';
        actionTitle = '{% trans "Move" %}';
        specifyLocation = true;
        allowSerializedStock = true;
        url = '{% url "api-stock-transfer" %}';
        break;
    case 'count':
        formTitle = '{% trans "Count Stock" %}';
        actionTitle = '{% trans "Count" %}';
        url = '{% url "api-stock-count" %}';
        break;
    case 'take':
        formTitle = '{% trans "Remove Stock" %}';
        actionTitle = '{% trans "Take" %}';
        url = '{% url "api-stock-remove" %}';
        break;
    case 'add':
        formTitle = '{% trans "Add Stock" %}';
        actionTitle = '{% trans "Add" %}';
        url = '{% url "api-stock-add" %}';
        break;
    case 'delete':
        formTitle = '{% trans "Delete Stock" %}';
        allowSerializedStock = true;
        break;
    default:
        break;
    }

    // Generate modal HTML content
    var html = `
    <table class='table table-striped table-condensed' id='stock-adjust-table'>
    <thead>
    <tr>
        <th>{% trans "Part" %}</th>
        <th>{% trans "Stock" %}</th>
        <th>{% trans "Location" %}</th>
        <th>${actionTitle || ''}</th>
        <th></th>
    </tr>
    </thead>
    <tbody>
    `;

    var itemCount = 0;

    for (var idx = 0; idx < items.length; idx++) {

        var item = items[idx];

        if ((item.serial != null) && !allowSerializedStock) {
            continue;
        }

        var pk = item.pk;

        var readonly = (item.serial != null);
        var minValue = null;
        var maxValue = null;
        var value = null;

        switch (action) {
        case 'move':
            minValue = 0;
            maxValue = item.quantity;
            value = item.quantity;
            break;
        case 'add':
            minValue = 0;
            value = 0;
            break;
        case 'take':
            minValue = 0;
            value = 0;
            break;
        case 'count':
            minValue = 0;
            value = item.quantity;
            break;
        default:
            break;
        }

        var image = item.part_detail.thumbnail || item.part_detail.image || blankImage();

        var status = stockStatusDisplay(item.status, {
            classes: 'float-right'
        });

        var quantity = item.quantity;

        var location = locationDetail(item, false);

        if (item.location_detail) {
            location = item.location_detail.pathstring;
        }

        if (item.serial != null) {
            quantity = `#${item.serial}`;
        }

        var actionInput = '';

        if (actionTitle != null) {
            actionInput = constructNumberInput(
                item.pk,
                {
                    value: value,
                    min_value: minValue,
                    max_value: maxValue,
                    read_only: readonly,
                    title: readonly ? '{% trans "Quantity cannot be adjusted for serialized stock" %}' : '{% trans "Specify stock quantity" %}',
                }
            );
        }

        var buttons = `<div class='btn-group float-right' role='group'>`;

        buttons += makeIconButton(
            'fa-times icon-red',
            'button-stock-item-remove',
            pk,
            '{% trans "Remove stock item" %}',
        );

        buttons += `</div>`;

        html += `
        <tr id='stock_item_${pk}' class='stock-item-row'>
            <td id='part_${pk}'><img src='${image}' class='hover-img-thumb'> ${item.part_detail.full_name}</td>
            <td id='stock_${pk}'>${quantity}${status}</td>
            <td id='location_${pk}'>${location}</td>
            <td id='action_${pk}'>
                <div id='div_id_${pk}'>
                    ${actionInput}
                    <div id='errors-${pk}'></div>
                </div>
            </td>
            <td id='buttons_${pk}'>${buttons}</td>
        </tr>`;

        itemCount += 1;
    }

    if (itemCount == 0) {
        showAlertDialog(
            '{% trans "Select Stock Items" %}',
            '{% trans "You must select at least one available stock item" %}',
        );

        return;
    }

    html += `</tbody></table>`;

    var modal = createNewModal({
        title: formTitle,
    });

    // Extra fields
    var extraFields = {
        location: {
            label: '{% trans "Location" %}',
            help_text: '{% trans "Select destination stock location" %}',
            type: 'related field',
            required: true,
            api_url: `/api/stock/location/`,
            model: 'stocklocation',
            name: 'location',
        },
        notes: {
            label: '{% trans "Notes" %}',
            help_text: '{% trans "Stock transaction notes" %}',
            type: 'string',
            name: 'notes',
        }
    };

    if (!specifyLocation) {
        delete extraFields.location;
    }

    constructFormBody({}, {
        preFormContent: html,
        fields: extraFields,
        confirm: true,
        confirmMessage: '{% trans "Confirm stock adjustment" %}',
        modal: modal,
        onSubmit: function(fields) {

            // "Delete" action gets handled differently
            if (action == 'delete') {

                var requests = [];

                items.forEach(function(item) {
                    requests.push(
                        inventreeDelete(
                            `/api/stock/${item.pk}/`,
                        )
                    );
                });

                // Wait for *all* the requests to complete
                $.when.apply($, requests).done(function() {
                    // Destroy the modal window
                    $(modal).modal('hide');

                    if (options.onSuccess) {
                        options.onSuccess();
                    }
                });

                return;
            }

            // Data to transmit
            var data = {
                items: [],
            };

            // Add values for each selected stock item
            items.forEach(function(item) {

                var q = getFormFieldValue(item.pk, {}, {modal: modal});

                if (q != null) {
                    data.items.push({pk: item.pk, quantity: q});
                }
            });

            // Add in extra field data
            for (var field_name in extraFields) {
                data[field_name] = getFormFieldValue(
                    field_name,
                    fields[field_name],
                    {
                        modal: modal,
                    }
                );
            }

            inventreePut(
                url,
                data,
                {
                    method: 'POST',
                    success: function() {

                        // Destroy the modal window
                        $(modal).modal('hide');

                        if (options.onSuccess) {
                            options.onSuccess();
                        }
                    },
                    error: function(xhr) {
                        switch (xhr.status) {
                        case 400:

                            // Handle errors for standard fields
                            handleFormErrors(
                                xhr.responseJSON,
                                extraFields,
                                {
                                    modal: modal,
                                }
                            );

                            break;
                        default:
                            $(modal).modal('hide');
                            showApiError(xhr);
                            break;
                        }
                    }
                }
            );
        }
    });

    // Attach callbacks for the action buttons
    $(modal).find('.button-stock-item-remove').click(function() {
        var pk = $(this).attr('pk');

        $(modal).find(`#stock_item_${pk}`).remove();
    });

    attachToggle(modal);

    $(modal + ' .select2-container').addClass('select-full-width');
    $(modal + ' .select2-container').css('width', '100%');
}


function removeStockRow(e) {
    // Remove a selected row from a stock modal form

    e = e || window.event;
    var src = e.target || e.srcElement;

    var row = $(src).attr('row');

    $('#' + row).remove();
}


function passFailBadge(result, align='float-right') {

    if (result) {
        return `<span class='label label-green ${align}'>{% trans "PASS" %}</span>`;
    } else {
        return `<span class='label label-red ${align}'>{% trans "FAIL" %}</span>`;
    }
}

function noResultBadge(align='float-right') {
    return `<span class='label label-blue ${align}'>{% trans "NO RESULT" %}</span>`;
}

function formatDate(row) {
    // Function for formatting date field
    var html = row.date;

    if (row.user_detail) {
        html += `<span class='badge'>${row.user_detail.username}</span>`;
    }

    if (row.attachment) {
        html += `<a href='${row.attachment}'><span class='fas fa-file-alt label-right'></span></a>`;
    }

    return html;
}

function loadStockTestResultsTable(table, options) {
    /*
     * Load StockItemTestResult table
     */

    function makeButtons(row, grouped) {
        var html = `<div class='btn-group float-right' role='group'>`;

        html += makeIconButton('fa-plus icon-green', 'button-test-add', row.test_name, '{% trans "Add test result" %}');

        if (!grouped && row.result != null) {
            var pk = row.pk;
            html += makeIconButton('fa-edit icon-blue', 'button-test-edit', pk, '{% trans "Edit test result" %}');
            html += makeIconButton('fa-trash-alt icon-red', 'button-test-delete', pk, '{% trans "Delete test result" %}');
        }

        html += '</div>';

        return html;
    }

    var parent_node = 'parent node';

    table.inventreeTable({
        url: '{% url "api-part-test-template-list" %}',
        method: 'get',
        name: 'testresult',
        treeEnable: true,
        rootParentId: parent_node,
        parentIdField: 'parent',
        idField: 'pk',
        uniqueId: 'key',
        treeShowField: 'test_name',
        formatNoMatches: function() {
            return '{% trans "No test results found" %}';
        },
        queryParams: {
            part: options.part,
        },
        onPostBody: function() {
            table.treegrid({
                treeColumn: 0,
            });
            table.treegrid('collapseAll');
        },
        columns: [
            {
                field: 'pk',
                title: 'ID',
                visible: false,
                switchable: false,
            },
            {
                field: 'test_name',
                title: '{% trans "Test Name" %}',
                sortable: true,
                formatter: function(value, row) {
                    var html = value;

                    if (row.required) {
                        html = `<b>${value}</b>`;
                    }

                    if (row.result == null) {
                        html += noResultBadge();
                    } else {
                        html += passFailBadge(row.result);
                    }

                    return html;
                }
            },
            {
                field: 'value',
                title: '{% trans "Value" %}',
            },
            {
                field: 'notes',
                title: '{% trans "Notes" %}',
            },
            {
                field: 'date',
                title: '{% trans "Test Date" %}',
                sortable: true,
                formatter: function(value, row) {
                    return formatDate(row);
                },
            },
            {
                field: 'buttons',
                formatter: function(value, row) {
                    return makeButtons(row, false);
                }
            }
        ],
        onLoadSuccess: function(tableData) {

            // Set "parent" for each existing row
            tableData.forEach(function(item, idx) {
                tableData[idx].parent = parent_node;
            });

            // Once the test template data are loaded, query for test results
            inventreeGet(
                '{% url "api-stock-test-result-list" %}',
                {
                    stock_item: options.stock_item,
                    user_detail: true,
                    attachment_detail: true,
                    ordering: '-date',
                },
                {
                    success: function(data) {
                        // Iterate through the returned test data
                        data.forEach(function(item) {

                            var match = false;
                            var override = false;

                            // Extract the simplified test key
                            var key = item.key;

                            // Attempt to associate this result with an existing test
                            for (var idx = 0; idx < tableData.length; idx++) {

                                var row = tableData[idx];

                                if (key == row.key) {

                                    item.test_name = row.test_name;
                                    item.required = row.required;

                                    if (row.result == null) {
                                        item.parent = parent_node;
                                        tableData[idx] = item;
                                        override = true;
                                    } else {
                                        item.parent = row.pk;
                                    }

                                    match = true;

                                    break;
                                }
                            }

                            // No match could be found
                            if (!match) {
                                item.test_name = item.test;
                                item.parent = parent_node;
                            }

                            if (!override) {
                                tableData.push(item);
                            }

                        });

                        // Push data back into the table
                        table.bootstrapTable('load', tableData);
                    }
                }
            );
        }
    });
}


function locationDetail(row, showLink=true) {
    /* 
     * Function to display a "location" of a StockItem.
     * 
     * Complicating factors: A StockItem may not actually *be* in a location!
     * - Could be at a customer
     * - Could be installed in another stock item
     * - Could be assigned to a sales order
     * - Could be currently in production!
     *
     * So, instead of being naive, we'll check!
     */

    // Display text
    var text = '';

    // URL (optional)
    var url = '';

    if (row.is_building && row.build) {
        // StockItem is currently being built!
        text = '{% trans "In production" %}';
        url = `/build/${row.build}/`;
    } else if (row.belongs_to) {
        // StockItem is installed inside a different StockItem
        text = `{% trans "Installed in Stock Item" %} ${row.belongs_to}`;
        url = `/stock/item/${row.belongs_to}/installed/`;
    } else if (row.customer) {
        // StockItem has been assigned to a customer
        text = '{% trans "Shipped to customer" %}';
        url = `/company/${row.customer}/assigned-stock/`;
    } else if (row.sales_order) {
        // StockItem has been assigned to a sales order
        text = '{% trans "Assigned to Sales Order" %}';
        url = `/order/sales-order/${row.sales_order}/`;
    } else if (row.location) {
        text = row.location_detail.pathstring;
        url = `/stock/location/${row.location}/`;
    } else {
        text = '<i>{% trans "No stock location set" %}</i>';
        url = '';
    }

    if (showLink && url) {
        return renderLink(text, url);
    } else {
        return text;
    }
}


function loadStockTable(table, options) {
    /* Load data into a stock table with adjustable options.
     * Fetches data (via AJAX) and loads into a bootstrap table.
     * Also links in default button callbacks.
     * 
     * Options:
     *  url - URL for the stock query
     *  params - query params for augmenting stock data request
     *  groupByField - Column for grouping stock items
     *  buttons - Which buttons to link to stock selection callbacks
     *  filterList - <ul> element where filters are displayed
     *  disableFilters: If true, disable custom filters
     */

    // List of user-params which override the default filters

    options.params['location_detail'] = true;
    options.params['part_detail'] = true;

    var params = options.params || {};

    var filterListElement = options.filterList || '#filter-list-stock';

    var filters = {};

    var filterKey = options.filterKey || options.name || 'stock';

    if (!options.disableFilters) {
        filters = loadTableFilters(filterKey);
    }

    var original = {};

    for (var k in params) {
        original[k] = params[k];
    }

    setupFilterList(filterKey, table, filterListElement);

    // Override the default values, or add new ones
    for (var key in params) {
        filters[key] = params[key];
    }

    var grouping = true;

    if ('grouping' in options) {
        grouping = options.grouping;
    }

    var col = null;

    // Explicitly disable part grouping functionality
    // Might be able to add this in later on,
    // but there is a bug which makes this crash if paginating on the server side.
    // Ref: https://github.com/wenzhixin/bootstrap-table/issues/3250
    // eslint-disable-next-line no-unused-vars
    grouping = false;

    var columns = [
        {
            checkbox: true,
            title: '{% trans "Select" %}',
            searchable: false,
            switchable: false,
        },
        {
            field: 'pk',
            title: 'ID',
            visible: false,
            switchable: false,
        }
    ];

    col = {
        field: 'part_detail.full_name',
        title: '{% trans "Part" %}',
        sortName: 'part__name',
        visible: params['part_detail'],
        switchable: params['part_detail'],
        formatter: function(value, row) {

            var url = `/stock/item/${row.pk}/`;
            var thumb = row.part_detail.thumbnail;
            var name = row.part_detail.full_name;

            var html = imageHoverIcon(thumb) + renderLink(name, url);

            html += makePartIcons(row.part_detail);

            return html;
        }
    };
    
    if (!options.params.ordering) {
        col['sortable'] = true;
    }

    columns.push(col);

    col = {
        field: 'part_detail.IPN',
        title: 'IPN',
        sortName: 'part__IPN',
        visible: params['part_detail'],
        switchable: params['part_detail'],
        formatter: function(value, row) {
            return row.part_detail.IPN;
        },
    };

    if (!options.params.ordering) {
        col['sortable'] = true;
    }

    columns.push(col);

    columns.push({
        field: 'part_detail.description',
        title: '{% trans "Description" %}',
        visible: params['part_detail'],
        switchable: params['part_detail'],
        formatter: function(value, row) {
            return row.part_detail.description;
        }
    });

    col = {
        field: 'quantity',
        title: '{% trans "Stock" %}',
        formatter: function(value, row) {

            var val = parseFloat(value);

            // If there is a single unit with a serial number, use the serial number
            if (row.serial && row.quantity == 1) {
                val = '# ' + row.serial;
            } else {
                val = +val.toFixed(5);
            }

            var html = renderLink(val, `/stock/item/${row.pk}/`);

            if (row.is_building) {
                html += makeIconBadge('fa-tools', '{% trans "Stock item is in production" %}');
            } 

            if (row.sales_order) {
                // Stock item has been assigned to a sales order
                html += makeIconBadge('fa-truck', '{% trans "Stock item assigned to sales order" %}');
            } else if (row.customer) {
                // StockItem has been assigned to a customer
                html += makeIconBadge('fa-user', '{% trans "Stock item assigned to customer" %}');
            }

            if (row.expired) {
                html += makeIconBadge('fa-calendar-times icon-red', '{% trans "Stock item has expired" %}');
            } else if (row.stale) {
                html += makeIconBadge('fa-stopwatch', '{% trans "Stock item will expire soon" %}');
            }

            if (row.allocated) {
                html += makeIconBadge('fa-bookmark', '{% trans "Stock item has been allocated" %}');
            }

            if (row.belongs_to) {
                html += makeIconBadge('fa-box', '{% trans "Stock item has been installed in another item" %}');
            }

            // Special stock status codes

            // REJECTED
            if (row.status == {{ StockStatus.REJECTED }}) {
                html += makeIconBadge('fa-times-circle icon-red', '{% trans "Stock item has been rejected" %}');
            } else if (row.status == {{ StockStatus.LOST }}) {
                html += makeIconBadge('fa-question-circle', '{% trans "Stock item is lost" %}');
            } else if (row.status == {{ StockStatus.DESTROYED }}) {
                html += makeIconBadge('fa-skull-crossbones', '{% trans "Stock item is destroyed" %}');
            }

            if (row.quantity <= 0) {
                html += `<span class='label label-right label-danger'>{% trans "Depleted" %}</span>`;
            }

            return html;
        }
    };

    if (!options.params.ordering) {
        col['sortable'] = true;
    }
    
    columns.push(col);

    col = {
        field: 'status',
        title: '{% trans "Status" %}',
        formatter: function(value) {
            return stockStatusDisplay(value);
        },
    };

    if (!options.params.ordering) {
        col['sortable'] = true;
    }

    columns.push(col);

    col = {
        field: 'batch',
        title: '{% trans "Batch" %}',
    };

    if (!options.params.ordering) {
        col['sortable'] = true;
    }

    columns.push(col);

    col = {
        field: 'location_detail.pathstring',
        title: '{% trans "Location" %}',
        formatter: function(value, row) {
            return locationDetail(row);
        }
    };

    if (!options.params.ordering) {
        col['sortable'] = true;
    }

    columns.push(col);

    col = {
        field: 'stocktake_date',
        title: '{% trans "Stocktake" %}',
    };

    if (!options.params.ordering) {
        col['sortable'] = true;
    }

    columns.push(col);

    col = {
        field: 'expiry_date',
        title: '{% trans "Expiry Date" %}',
        visible: global_settings.STOCK_ENABLE_EXPIRY,
        switchable: global_settings.STOCK_ENABLE_EXPIRY,
    };

    if (!options.params.ordering) {
        col['sortable'] = true;
    }

    columns.push(col);

    col = {
        field: 'updated',
        title: '{% trans "Last Updated" %}',
    };

    if (!options.params.ordering) {
        col['sortable'] = true;
    }

    columns.push(col);

    columns.push({
        field: 'purchase_order',
        title: '{% trans "Purchase Order" %}',
        formatter: function(value, row) {
            if (!value) {
                return '-';
            }

            var link = `/order/purchase-order/${row.purchase_order}/`;
            var text = `${row.purchase_order}`;

            if (row.purchase_order_reference) {

                var prefix = global_settings.PURCHASEORDER_REFERENCE_PREFIX;

                text = prefix + row.purchase_order_reference;
            }

            return renderLink(text, link);
        }
    });

    col = {
        
        field: 'supplier_part',
        title: '{% trans "Supplier Part" %}',
        visible: params['supplier_part_detail'] || false,
        switchable: params['supplier_part_detail'] || false,
        formatter: function(value, row) {
            if (!value) {
                return '-';
            }

            var link = `/supplier-part/${row.supplier_part}/?display=stock`;

            var text = '';

            if (row.supplier_part_detail) {
                text = `${row.supplier_part_detail.SKU}`;
            } else {
                text = `<i>{% trans "Supplier part not specified" %}</i>`;
            }

            return renderLink(text, link);
        }
    };

    if (!options.params.ordering) {
        col.sortable = true;
        col.sortName = 'SKU';
    }

    columns.push(col);

    col = {
        field: 'purchase_price_string',
        title: '{% trans "Purchase Price" %}',
    };

    if (!options.params.ordering) {
        col.sortable = true;
        col.sortName = 'purchase_price';
    }

    columns.push(col);

    columns.push({
        field: 'packaging',
        title: '{% trans "Packaging" %}',
    },
    {
        field: 'notes',
        title: '{% trans "Notes" %}',
    });

    table.inventreeTable({
        method: 'get',
        formatNoMatches: function() {
            return '{% trans "No stock items matching query" %}';
        },
        url: options.url || '{% url "api-stock-list" %}',
        queryParams: filters,
        sidePagination: 'server',
        name: 'stock',
        original: original,
        showColumns: true,
        columns: columns,
        {% if False %}
        groupByField: options.groupByField || 'part',
        groupBy: grouping,
        groupByFormatter: function(field, id, data) {

            var row = data[0];

            if (field == 'part_detail.full_name') {

                var html = imageHoverIcon(row.part_detail.thumbnail);

                html += row.part_detail.full_name;
                html += ` <i>(${data.length} {% trans "items" %})</i>`;

                html += makePartIcons(row.part_detail);

                return html;
            } else if (field == 'part_detail.IPN') {
                var ipn = row.part_detail.IPN;

                if (ipn) {
                    return ipn;
                } else {
                    return '-';
                }
            } else if (field == 'part_detail.description') {
                return row.part_detail.description;
            } else if (field == 'packaging') {
                var packaging = [];

                data.forEach(function(item) {
                    var pkg = item.packaging;

                    if (!pkg) {
                        pkg = '-';
                    }

                    if (!packaging.includes(pkg)) {
                        packaging.push(pkg);
                    }
                });

                if (packaging.length > 1) {
                    return "...";
                } else if (packaging.length == 1) {
                    return packaging[0];
                } else {
                    return "-";
                }
            } else if (field == 'quantity') {
                var stock = 0;
                var items = 0;

                data.forEach(function(item) {
                    stock += parseFloat(item.quantity); 
                    items += 1;
                });

                stock = +stock.toFixed(5);

                return `${stock} (${items} {% trans "items" %})`;
            } else if (field == 'status') {
                var statii = [];

                data.forEach(function(item) {
                    var status = String(item.status);

                    if (!status || status == '') {
                        status = '-';
                    }

                    if (!statii.includes(status)) {
                        statii.push(status);
                    }
                });

                // Multiple status codes
                if (statii.length > 1) {
                    return "...";
                } else if (statii.length == 1) {
                    return stockStatusDisplay(statii[0]);
                } else {
                    return "-";
                }
            } else if (field == 'batch') {
                var batches = [];

                data.forEach(function(item) {
                    var batch = item.batch;

                    if (!batch || batch == '') {
                        batch = '-';
                    }

                    if (!batches.includes(batch)) {
                        batches.push(batch); 
                    }
                });

                if (batches.length > 1) {
                    return "" + batches.length + " {% trans 'batches' %}";
                } else if (batches.length == 1) {
                    if (batches[0]) {
                        return batches[0];
                    } else {
                        return '-';
                    }
                } else {
                    return '-';
                }
            } else if (field == 'location_detail.pathstring') {
                /* Determine how many locations */
                var locations = [];

                data.forEach(function(item) {

                    var detail = locationDetail(item);

                    if (!locations.includes(detail)) {
                        locations.push(detail);
                    }
                });

                if (locations.length == 1) {
                    // Single location, easy!
                    return locations[0];
                } else if (locations.length > 1) {
                    return "In " + locations.length + " {% trans 'locations' %}";
                } else {
                    return "<i>{% trans 'Undefined location' %}</i>";
                }
            } else if (field == 'notes') {
                var notes = [];

                data.forEach(function(item) {
                    var note = item.notes;

                    if (!note || note == '') {
                        note = '-';
                    }

                    if (!notes.includes(note)) {
                        notes.push(note);
                    }
                });

                if (notes.length > 1) {
                    return '...';
                } else if (notes.length == 1) {
                    return notes[0] || '-';
                } else {
                    return '-';
                }
            } else {
                return '';
            }
        },
        {% endif %}
    });

    /*
    if (options.buttons) {
        linkButtonsToSelection(table, options.buttons);
    }
    */

    var buttons = [
        '#stock-print-options',
        '#stock-options',
    ];

    if (global_settings.BARCODE_ENABLE) {
        buttons.push('#stock-barcode-options');
    }

    linkButtonsToSelection(
        table,
        buttons,
    );


    function stockAdjustment(action) {
        var items = $(table).bootstrapTable('getSelections');

        adjustStock(action, items, {
            onSuccess: function() {
                $(table).bootstrapTable('refresh');
            }
        });
    }

    // Automatically link button callbacks

    $('#multi-item-print-label').click(function() {
        var selections = $(table).bootstrapTable('getSelections');

        var items = [];

        selections.forEach(function(item) {
            items.push(item.pk);
        });

        printStockItemLabels(items);
    });

    $('#multi-item-print-test-report').click(function() {
        var selections = $(table).bootstrapTable('getSelections');

        var items = [];

        selections.forEach(function(item) {
            items.push(item.pk);
        });

        printTestReports(items);
    });

    if (global_settings.BARCODE_ENABLE) {
        $('#multi-item-barcode-scan-into-location').click(function() {        
            var selections = $(table).bootstrapTable('getSelections');

            var items = [];

            selections.forEach(function(item) {
                items.push(item.pk);
            });

            scanItemsIntoLocation(items);
        });
    }

    $('#multi-item-stocktake').click(function() {
        stockAdjustment('count');
    });

    $('#multi-item-remove').click(function() {
        stockAdjustment('take');
    });

    $('#multi-item-add').click(function() {
        stockAdjustment('add');
    });

    $('#multi-item-move').click(function() {
        stockAdjustment('move');
    });

    $('#multi-item-order').click(function() {
        var selections = $(table).bootstrapTable('getSelections');

        var stock = [];

        selections.forEach(function(item) {
            stock.push(item.pk);
        });

        launchModalForm('/order/purchase-order/order-parts/', {
            data: {
                stock: stock,
            },
        });
    });

    $('#multi-item-set-status').click(function() {
        // Select and set the STATUS field for selected stock items
        var selections = $(table).bootstrapTable('getSelections');

        // Select stock status
        var modal = '#modal-form';

        var status_list = makeOptionsList(
            stockStatusCodes(),
            function(item) {
                return item.text;
            },
            function(item) {
                return item.key;
            }
        );

        // Add an empty option at the start of the list
        status_list.unshift('<option value="">---------</option>');

        // Construct form
        var html = `
        <form method='post' action='' class='js-modal-form' enctype='multipart/form-data'>
            <div class='form-group'>
                <label class='control-label requiredField' for='id_status'>
                {% trans "Stock Status" %}
                </label>
                <div class='controls'>
                    <select id='id_status' class='select form-control' name='label'>
                        ${status_list}
                    </select>
                </div>
            </div>
        </form>`;

        openModal({
            modal: modal,
        });

        modalEnable(modal, true);
        modalSetTitle(modal, '{% trans "Set Stock Status" %}');
        modalSetContent(modal, html);

        attachSelect(modal);

        modalSubmit(modal, function() {
            var label = $(modal).find('#id_status');

            var status_code = label.val();

            closeModal(modal);

            if (!status_code) {
                showAlertDialog(
                    '{% trans "Select Status Code" %}',
                    '{% trans "Status code must be selected" %}'
                );

                return;
            }

            var requests = [];

            selections.forEach(function(item) {
                var url = `/api/stock/${item.pk}/`;

                requests.push(
                    inventreePut(
                        url,
                        {
                            status: status_code,
                        },
                        {
                            method: 'PATCH',
                            success: function() {
                            }
                        }
                    )
                );
            });

            $.when.apply($, requests).done(function() {
                $(table).bootstrapTable('refresh');
            });
        });
    });

    $('#multi-item-delete').click(function() {
        var selections = $(table).bootstrapTable('getSelections');

        var stock = [];

        selections.forEach(function(item) {
            stock.push(item.pk);
        });

        stockAdjustment('delete');
    });
}

function loadStockLocationTable(table, options) {
    /* Display a table of stock locations */

    var params = options.params || {};

    var filterListElement = options.filterList || '#filter-list-location';

    var filters = {};

    var filterKey = options.filterKey || options.name || 'location';

    if (!options.disableFilters) {
        filters = loadTableFilters(filterKey);
    }

    var original = {};

    for (var k in params) {
        original[k] = params[k];
    }

    setupFilterList(filterKey, table, filterListElement);

    for (var key in params) {
        filters[key] = params[key];
    }

    table.inventreeTable({
        method: 'get',
        url: options.url || '{% url "api-location-list" %}',
        queryParams: filters,
        sidePagination: 'server',
        name: 'location',
        original: original,
        showColumns: true,
        columns: [
            {
                checkbox: true,
                title: '{% trans "Select" %}',
                searchable: false,
                switchable: false,
            },
            {
                field: 'name',
                title: '{% trans "Name" %}',
                switchable: true,
                sortable: true,
                formatter: function(value, row) {
                    return renderLink(
                        value,
                        `/stock/location/${row.pk}/`
                    );
                },
            },
            {
                field: 'description',
                title: '{% trans "Description" %}',
                switchable: true,
                sortable: false,
            },
            {
                field: 'pathstring',
                title: '{% trans "Path" %}',
                switchable: true,
                sortable: false,
            },
            {
                field: 'items',
                title: '{% trans "Stock Items" %}',
                switchable: true,
                sortable: false,
                sortName: 'item_count',
            }
        ]
    });
}

function loadStockTrackingTable(table, options) {

    var cols = [];

    // Date
    cols.push({
        field: 'date',
        title: '{% trans "Date" %}',
        sortable: true,
        formatter: function(value) {
            var m = moment(value);

            if (m.isValid()) {
                var html = m.format('dddd MMMM Do YYYY'); // + '<br>' + m.format('h:mm a');
                return html;
            }

            return '<i>{% trans "Invalid date" %}</i>';
        }
    });

    // Stock transaction description
    cols.push({
        field: 'label',
        title: '{% trans "Description" %}',
        formatter: function(value, row) {
            var html = '<b>' + value + '</b>';

            if (row.notes) {
                html += '<br><i>' + row.notes + '</i>';
            }

            return html;
        }
    });

    // Stock transaction details
    cols.push({
        field: 'deltas',
        title: '{% trans "Details" %}',
        formatter: function(details, row) {
            var html = `<table class='table table-condensed' id='tracking-table-${row.pk}'>`;

            if (!details) {
                html += '</table>';
                return html;
            }

            // Location information
            if (details.location) {

                html += `<tr><th>{% trans "Location" %}</th>`;

                html += '<td>';

                if (details.location_detail) {
                    // A valid location is provided

                    html += renderLink(
                        details.location_detail.pathstring,
                        details.location_detail.url,
                    );
                } else {
                    // An invalid location (may have been deleted?)
                    html += `<i>{% trans "Location no longer exists" %}</i>`;
                }

                html += '</td></tr>';
            }

            // Purchase Order Information
            if (details.purchaseorder) {

                html += `<tr><th>{% trans "Purchase Order" %}</td>`;

                html += '<td>';

                if (details.purchaseorder_detail) {
                    html += renderLink(
                        details.purchaseorder_detail.reference,
                        `/order/purchase-order/${details.purchaseorder}/`
                    );
                } else {
                    html += `<i>{% trans "Purchase order no longer exists" %}</i>`;
                }

                html += '</td></tr>';
            }

            // Customer information
            if (details.customer) {

                html += `<tr><th>{% trans "Customer" %}</td>`;

                html += '<td>';

                if (details.customer_detail) {
                    html += renderLink(
                        details.customer_detail.name,
                        details.customer_detail.url
                    );
                } else {
                    html += `<i>{% trans "Customer no longer exists" %}</i>`;
                }

                html += '</td></tr>';
            }

            // Stockitem information
            if (details.stockitem) {
                html += '<tr><th>{% trans "Stock Item" %}</td>';

                html += '<td>';

                if (details.stockitem_detail) {
                    html += renderLink(
                        details.stockitem,
                        `/stock/item/${details.stockitem}/`
                    );
                } else {
                    html += `<i>{% trans "Stock item no longer exists" %}</i>`;
                }

                html += '</td></tr>';
            }

            // Status information
            if (details.status) {
                html += `<tr><th>{% trans "Status" %}</td>`;

                html += '<td>';
                html += stockStatusDisplay(
                    details.status,
                    {
                        classes: 'float-right',
                    }
                );
                html += '</td></tr>';

            }

            // Quantity information
            if (details.added) {
                html += '<tr><th>{% trans "Added" %}</th>';

                html += `<td>${details.added}</td>`;

                html += '</tr>';
            }

            if (details.removed) {
                html += '<tr><th>{% trans "Removed" %}</th>';

                html += `<td>${details.removed}</td>`;

                html += '</tr>';
            }

            if (details.quantity) {
                html += '<tr><th>{% trans "Quantity" %}</th>';

                html += `<td>${details.quantity}</td>`;

                html += '</tr>';
            }

            html += '</table>';

            return html;
        }
    });

    cols.push({
        field: 'user',
        title: '{% trans "User" %}',
        formatter: function(value, row) {
            if (value) {
                // TODO - Format the user's first and last names
                return row.user_detail.username;
            } else {
                return `<i>{% trans "No user information" %}</i>`;
            }
        }
    });

    /*
    // 2021-05-11 - Ability to edit or delete StockItemTracking entries is now removed
    cols.push({
        sortable: false,
        formatter: function(value, row, index, field) {
            // Manually created entries can be edited or deleted
            if (false && !row.system) {
                var bEdit = "<button title='{% trans 'Edit tracking entry' %}' class='btn btn-entry-edit btn-default btn-glyph' type='button' url='/stock/track/" + row.pk + "/edit/'><span class='fas fa-edit'/></button>";
                var bDel = "<button title='{% trans 'Delete tracking entry' %}' class='btn btn-entry-delete btn-default btn-glyph' type='button' url='/stock/track/" + row.pk + "/delete/'><span class='fas fa-trash-alt icon-red'/></button>";

                return "<div class='btn-group' role='group'>" + bEdit + bDel + "</div>";
            } else {
                return "";
            }
        }
    });
    */

    table.inventreeTable({
        method: 'get',
        queryParams: options.params,
        columns: cols,
        url: options.url,
    });

    if (options.buttons) {
        linkButtonsToSelection(table, options.buttons);
    }

    table.on('click', '.btn-entry-edit', function() {
        var button = $(this);

        launchModalForm(button.attr('url'), {
            reload: true,
        });
    });

    table.on('click', '.btn-entry-delete', function() {
        var button = $(this);

        launchModalForm(button.attr('url'), {
            reload: true,
        });
    });
}


function createNewStockItem(options) {
    /* Launch a modal form to create a new stock item.
     * 
     * This is really just a helper function which calls launchModalForm,
     * but it does get called a lot, so here we are ...
     */

    // Add in some funky options

    options.callback = [
        {   
            field: 'part',
            action: function(value) {

                if (!value) {
                    // No part chosen
                    
                    clearFieldOptions('supplier_part');
                    enableField('serial_numbers', false);
                    enableField('purchase_price_0', false);
                    enableField('purchase_price_1', false);

                    return;
                }

                // Reload options for supplier part
                reloadFieldOptions(
                    'supplier_part',
                    {
                        url: '{% url "api-supplier-part-list" %}',
                        params: {
                            part: value,
                            pretty: true,
                        },
                        text: function(item) {
                            return item.pretty_name;
                        }
                    }
                );

                // Request part information from the server
                inventreeGet(
                    `/api/part/${value}/`, {},
                    {
                        success: function(response) {

                            // Disable serial number field if the part is not trackable
                            enableField('serial_numbers', response.trackable);
                            clearField('serial_numbers');

                            enableField('purchase_price_0', response.purchaseable);
                            enableField('purchase_price_1', response.purchaseable);

                            // Populate the expiry date
                            if (response.default_expiry <= 0) {
                                // No expiry date
                                clearField('expiry_date');
                            } else {
                                var expiry = moment().add(response.default_expiry, 'days');

                                setFieldValue('expiry_date', expiry.format('YYYY-MM-DD'));
                            }
                        }
                    }
                );
            }
        },
    ];

    launchModalForm('{% url "stock-item-create" %}', options);
}


function loadInstalledInTable(table, options) {
    /*
    * Display a table showing the stock items which are installed in this stock item.
    */

    table.inventreeTable({
        url: '{% url "api-stock-list" %}',
        queryParams: {
            installed_in: options.stock_item,
            part_detail: true,
        },
        formatNoMatches: function() {
            return '{% trans "No installed items" %}';
        },
        columns: [
            {
                field: 'part',
                title: '{% trans "Part" %}',
                formatter: function(value, row) {
                    var html = '';

                    html += imageHoverIcon(row.part_detail.thumbnail);
                    html += renderLink(row.part_detail.full_name, `/stock/item/${row.pk}/`);

                    return html;
                }
            },
            {
                field: 'quantity',
                title: '{% trans "Quantity" %}',
                formatter: function(value, row) {

                    var html = '';

                    if (row.serial && row.quantity == 1) {
                        html += `{% trans "Serial" %}: ${row.serial}`;
                    } else {
                        html += `${row.quantity}`;
                    }

                    return renderLink(html, `/stock/item/${row.pk}/`);
                }
            },
            {
                field: 'status',
                title: '{% trans "Status" %}',
                formatter: function(value) {
                    return stockStatusDisplay(value);
                }
            },
            {
                field: 'batch',
                title: '{% trans "Batch" %}',
            },
            {
                field: 'buttons',
                title: '',
                switchable: false,
                formatter: function(value, row) {
                    var pk = row.pk;
                    var html = '';

                    html += `<div class='btn-group float-right' role='group'>`;
                    html += makeIconButton('fa-unlink', 'button-uninstall', pk, '{% trans "Uninstall Stock Item" %}');
                    html += `</div>`;

                    return html;
                }
            }
        ],
        onPostBody: function() {
            // Assign callbacks to the buttons
            table.find('.button-uninstall').click(function() {
                var pk = $(this).attr('pk');

                launchModalForm(
                    '{% url "stock-item-uninstall" %}',
                    {
                        data: {
                            'items[]': pk,
                        },
                        success: function() {
                            table.bootstrapTable('refresh');
                        }
                    }
                );
            });
        }
    });
}
