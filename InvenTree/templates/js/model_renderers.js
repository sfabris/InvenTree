{% load i18n %}


function blankImage() {
    return `/static/img/blank_image.png`;
}

// Render a select2 thumbnail image
function select2Thumbnail(image) {
    if (!image) {
        image = blankImage();
    }

    return `<img src='${image}' class='select2-thumbnail'>`;
}


/*
 * This file contains functions for rendering various InvenTree database models,
 * in particular for displaying them in modal forms in a 'select2' context.
 * 
 * Each renderer is provided with three arguments:
 * 
 * - name: The 'name' of the model instance in the referring model
 * - data: JSON data which represents the model instance. Returned via a GET request.
 * - parameters: The field parameters provided via an OPTIONS request to the endpoint.
 * - options: User options provided by the client
 */


// Renderer for "Company" model
function renderCompany(name, data, parameters, options) {
    
    var html = select2Thumbnail(data.image);

    html += `<span><b>${data.name}</b></span> - <i>${data.description}</i>`;

    html += `<span class='float-right'>{% trans "Company ID" %}: ${data.pk}</span>`;

    return html;
}


// Renderer for "StockItem" model
function renderStockItem(name, data, parameters, options) {

    var image = data.part_detail.thumbnail || data.part_detail.image || blankImage();

    var html = `<img src='${image}' class='select2-thumbnail'>`;

    html += ` <span>${data.part_detail.full_name || data.part_detail.name}</span>`;

    if (data.serial && data.quantity == 1) {
        html += ` - <i>{% trans "Serial Number" %}: ${data.serial}`;
    } else {
        html += ` - <i>{% trans "Quantity" %}: ${data.quantity}`;
    }

    if (data.part_detail.description) {
        html += `<p><small>${data.part_detail.description}</small></p>`;
    }

    return html;
}


// Renderer for "StockLocation" model
function renderStockLocation(name, data, parameters, options) {

    var html = `<span>${data.name}</span>`;

    if (data.description) {
        html += ` - <i>${data.description}</i>`;
    }

    html += `<span class='float-right'>{% trans "Location ID" %}: ${data.pk}</span>`;

    if (data.pathstring) {
        html += `<p><small>${data.pathstring}</small></p>`;
    }

    return html;
}


function renderBuild(name, data, parameters, options) {
    
    var image = null;

    if (data.part_detail && data.part_detail.thumbnail) {
        image = data.part_detail.thumbnail;
    } 

    var html = select2Thumbnail(image);

    html += `<span><b>${data.reference}</b></span> - ${data.quantity} x ${data.part_detail.full_name}`;
    html += `<span class='float-right'>{% trans "Build ID" %}: ${data.pk}</span>`;

    html += `<p><i>${data.title}</i></p>`;

    return html;
}


// Renderer for "Part" model
function renderPart(name, data, parameters, options) {

    var html = select2Thumbnail(data.image);
    
    html += ` <span>${data.full_name || data.name}</span>`;

    if (data.description) {
        html += ` - <i>${data.description}</i>`;
    }

    html += `<span class='float-right'>{% trans "Part ID" %}: ${data.pk}</span>`;

    return html;
}

// Renderer for "User" model
function renderUser(name, data, parameters, options) {

    var html = `<span>${data.username}</span>`;

    if (data.first_name && data.last_name) {
        html += ` - <i>${data.first_name} ${data.last_name}</i>`;
    }

    return html;
}


// Renderer for "Owner" model
function renderOwner(name, data, parameters, options) {

    var html = `<span>${data.name}</span>`;

    switch (data.label) {
        case 'user':
            html += `<span class='float-right fas fa-user'></span>`;
            break;
        case 'group':
            html += `<span class='float-right fas fa-users'></span>`;
            break;
        default:
            break;
    }

    return html;
}


// Renderer for "PartCategory" model
function renderPartCategory(name, data, parameters, options) {

    var html = `<span><b>${data.name}</b></span>`;

    if (data.description) {
        html += ` - <i>${data.description}</i>`;
    }

    html += `<span class='float-right'>{% trans "Category ID" %}: ${data.pk}</span>`;

    if (data.pathstring) {
        html += `<p><small>${data.pathstring}</small></p>`;
    }

    return html;
}


function renderPartParameterTemplate(name, data, parameters, options) {

    var html = `<span>${data.name} - [${data.units}]</span>`;

    return html;
}


// Rendered for "SupplierPart" model
function renderSupplierPart(name, data, parameters, options) {

    var supplier_image = null;
    var part_image = null;
    
    if (data.supplier_detail) {
        supplier_image = data.supplier_detail.image;
    }

    if (data.part_detail) {
        part_image = data.part_detail.thumbnail || data.part_detail.image;
    }

    var html = '';
    
    html += select2Thumbnail(supplier_image);
    html += select2Thumbnail(part_image);
    
    html += ` <span><b>${data.supplier_detail.name}</b> - ${data.SKU}</span>`;
    html += ` - <i>${data.part_detail.full_name}</i>`;

    html += `<span class='float-right'>{% trans "Supplier Part ID" %}: ${data.pk}</span>`;


    return html;

}
