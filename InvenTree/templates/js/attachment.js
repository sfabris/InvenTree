{% load i18n %}

function reloadAttachmentTable() {

    $('#attachment-table').bootstrapTable("refresh");
}


function loadAttachmentTable(url, options) {

    var table = options.table || '#attachment-table';

    $(table).inventreeTable({
        url: url,
        name: options.name || 'attachments',
        formatNoMatches: function() { return '{% trans "No attachments found" %}'},
        sortable: true,
        search: false,
        queryParams: options.filters || {},
        onPostBody: function() {
            // Add callback for 'edit' button
            $(table).find('.button-attachment-edit').click(function() {
                var pk = $(this).attr('pk');

                if (options.onEdit) {
                    options.onEdit(pk);
                }
            });
            
            // Add callback for 'delete' button
            $(table).find('.button-attachment-delete').click(function() {
                var pk = $(this).attr('pk');

                if (options.onDelete) {
                    options.onDelete(pk);
                }
            });
        },
        columns: [
            {
                field: 'attachment',
                title: '{% trans "File" %}',
                formatter: function(value, row) {

                    var split = value.split('/');

                    return renderLink(split[split.length - 1], value);
                }
            },
            {
                field: 'comment',
                title: '{% trans "Comment" %}',
            },
            {
                field: 'upload_date',
                title: '{% trans "Upload Date" %}',
            },
            {
                field: 'actions',
                formatter: function(value, row) {
                    var html = '';

                    html = `<div class='btn-group float-right' role='group'>`;

                    html += makeIconButton(
                        'fa-edit icon-blue',
                        'button-attachment-edit',
                        row.pk,
                        '{% trans "Edit attachment" %}',
                    );

                    html += makeIconButton(
                        'fa-trash-alt icon-red',
                        'button-attachment-delete',
                        row.pk,
                        '{% trans "Delete attachment" %}',
                    );

                    html += `</div>`;

                    return html;
                }
            }
        ]
    });
}