"""
JSON serializers for the Order API
"""

# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.utils.translation import ugettext_lazy as _

from django.db import models
from django.db.models import Case, When, Value
from django.db.models import BooleanField, ExpressionWrapper, F

from rest_framework import serializers
from rest_framework.serializers import ValidationError

from sql_util.utils import SubqueryCount

from InvenTree.serializers import InvenTreeModelSerializer
from InvenTree.serializers import InvenTreeAttachmentSerializer
from InvenTree.serializers import InvenTreeMoneySerializer
from InvenTree.serializers import InvenTreeAttachmentSerializerField

from InvenTree.status_codes import StockStatus

from company.serializers import CompanyBriefSerializer, SupplierPartSerializer

from part.serializers import PartBriefSerializer

import stock.models
from stock.serializers import LocationBriefSerializer, StockItemSerializer, LocationSerializer

from .models import PurchaseOrder, PurchaseOrderLineItem
from .models import PurchaseOrderAttachment, SalesOrderAttachment
from .models import SalesOrder, SalesOrderLineItem
from .models import SalesOrderAllocation

from common.settings import currency_code_mappings


class POSerializer(InvenTreeModelSerializer):
    """ Serializer for a PurchaseOrder object """

    def __init__(self, *args, **kwargs):

        supplier_detail = kwargs.pop('supplier_detail', False)

        super().__init__(*args, **kwargs)

        if supplier_detail is not True:
            self.fields.pop('supplier_detail')

    @staticmethod
    def annotate_queryset(queryset):
        """
        Add extra information to the queryset

        - Number of lines in the PurchaseOrder
        - Overdue status of the PurchaseOrder
        """

        queryset = queryset.annotate(
            line_items=SubqueryCount('lines')
        )

        queryset = queryset.annotate(
            overdue=Case(
                When(
                    PurchaseOrder.OVERDUE_FILTER, then=Value(True, output_field=BooleanField()),
                ),
                default=Value(False, output_field=BooleanField())
            )
        )

        return queryset

    supplier_detail = CompanyBriefSerializer(source='supplier', many=False, read_only=True)

    line_items = serializers.IntegerField(read_only=True)

    status_text = serializers.CharField(source='get_status_display', read_only=True)

    overdue = serializers.BooleanField(required=False, read_only=True)

    reference = serializers.CharField(required=True)

    class Meta:
        model = PurchaseOrder

        fields = [
            'pk',
            'issue_date',
            'complete_date',
            'creation_date',
            'description',
            'line_items',
            'link',
            'overdue',
            'reference',
            'responsible',
            'supplier',
            'supplier_detail',
            'supplier_reference',
            'status',
            'status_text',
            'target_date',
            'notes',
        ]

        read_only_fields = [
            'status'
            'issue_date',
            'complete_date',
            'creation_date',
        ]


class POLineItemSerializer(InvenTreeModelSerializer):

    @staticmethod
    def annotate_queryset(queryset):
        """
        Add some extra annotations to this queryset:

        - Total price = purchase_price * quantity
        """

        queryset = queryset.annotate(
            total_price=ExpressionWrapper(
                F('purchase_price') * F('quantity'),
                output_field=models.DecimalField()
            )
        )

        return queryset

    def __init__(self, *args, **kwargs):

        part_detail = kwargs.pop('part_detail', False)

        super().__init__(*args, **kwargs)

        if part_detail is not True:
            self.fields.pop('part_detail')
            self.fields.pop('supplier_part_detail')

    quantity = serializers.FloatField(default=1)
    received = serializers.FloatField(default=0)

    total_price = serializers.FloatField(read_only=True)

    part_detail = PartBriefSerializer(source='get_base_part', many=False, read_only=True)
    supplier_part_detail = SupplierPartSerializer(source='part', many=False, read_only=True)

    purchase_price = InvenTreeMoneySerializer(
        max_digits=19, decimal_places=4,
        allow_null=True
    )

    purchase_price_string = serializers.CharField(source='purchase_price', read_only=True)

    destination_detail = LocationBriefSerializer(source='get_destination', read_only=True)

    purchase_price_currency = serializers.ChoiceField(
        choices=currency_code_mappings(),
        help_text=_('Purchase price currency'),
    )

    class Meta:
        model = PurchaseOrderLineItem

        fields = [
            'pk',
            'quantity',
            'reference',
            'notes',
            'order',
            'part',
            'part_detail',
            'supplier_part_detail',
            'received',
            'purchase_price',
            'purchase_price_currency',
            'purchase_price_string',
            'destination',
            'destination_detail',
            'total_price',
        ]


class POLineItemReceiveSerializer(serializers.Serializer):
    """
    A serializer for receiving a single purchase order line item against a purchase order
    """

    line_item = serializers.PrimaryKeyRelatedField(
        queryset=PurchaseOrderLineItem.objects.all(),
        many=False,
        allow_null=False,
        required=True,
        label=_('Line Item'),
    )

    def validate_line_item(self, item):

        if item.order != self.context['order']:
            raise ValidationError(_('Line item does not match purchase order'))

        return item

    location = serializers.PrimaryKeyRelatedField(
        queryset=stock.models.StockLocation.objects.all(),
        many=False,
        allow_null=True,
        required=False,
        label=_('Location'),
        help_text=_('Select destination location for received items'),
    )

    quantity = serializers.DecimalField(
        max_digits=15,
        decimal_places=5,
        min_value=0,
        required=True,
    )

    status = serializers.ChoiceField(
        choices=list(StockStatus.items()),
        default=StockStatus.OK,
        label=_('Status'),
    )

    barcode = serializers.CharField(
        label=_('Barcode Hash'),
        help_text=_('Unique identifier field'),
        default='',
        required=False,
    )

    def validate_barcode(self, barcode):
        """
        Cannot check in a LineItem with a barcode that is already assigned
        """

        # Ignore empty barcode values
        if not barcode or barcode.strip() == '':
            return

        if stock.models.StockItem.objects.filter(uid=barcode).exists():
            raise ValidationError(_('Barcode is already in use'))

        return barcode

    class Meta:
        fields = [
            'barcode',
            'line_item',
            'location',
            'quantity',
            'status',
        ]


class POReceiveSerializer(serializers.Serializer):
    """
    Serializer for receiving items against a purchase order
    """

    items = POLineItemReceiveSerializer(many=True)

    location = serializers.PrimaryKeyRelatedField(
        queryset=stock.models.StockLocation.objects.all(),
        many=False,
        allow_null=True,
        label=_('Location'),
        help_text=_('Select destination location for received items'),
    )

    def is_valid(self, raise_exception=False):

        super().is_valid(raise_exception)

        # Custom validation
        data = self.validated_data

        items = data.get('items', [])

        if len(items) == 0:
            self._errors['items'] = _('Line items must be provided')
        else:
            # Ensure barcodes are unique
            unique_barcodes = set()

            for item in items:
                barcode = item.get('barcode', '')

                if barcode:
                    if barcode in unique_barcodes:
                        self._errors['items'] = _('Supplied barcode values must be unique')
                        break
                    else:
                        unique_barcodes.add(barcode)

        if self._errors and raise_exception:
            raise ValidationError(self.errors)

        return not bool(self._errors)

    class Meta:
        fields = [
            'items',
            'location',
        ]


class POAttachmentSerializer(InvenTreeAttachmentSerializer):
    """
    Serializers for the PurchaseOrderAttachment model
    """

    attachment = InvenTreeAttachmentSerializerField(required=True)

    class Meta:
        model = PurchaseOrderAttachment

        fields = [
            'pk',
            'order',
            'attachment',
            'filename',
            'comment',
            'upload_date',
        ]

        read_only_fields = [
            'upload_date',
        ]


class SalesOrderSerializer(InvenTreeModelSerializer):
    """
    Serializers for the SalesOrder object
    """

    def __init__(self, *args, **kwargs):

        customer_detail = kwargs.pop('customer_detail', False)

        super().__init__(*args, **kwargs)

        if customer_detail is not True:
            self.fields.pop('customer_detail')

    @staticmethod
    def annotate_queryset(queryset):
        """
        Add extra information to the queryset

        - Number of line items in the SalesOrder
        - Overdue status of the SalesOrder
        """

        queryset = queryset.annotate(
            line_items=SubqueryCount('lines')
        )

        queryset = queryset.annotate(
            overdue=Case(
                When(
                    SalesOrder.OVERDUE_FILTER, then=Value(True, output_field=BooleanField()),
                ),
                default=Value(False, output_field=BooleanField())
            )
        )

        return queryset

    customer_detail = CompanyBriefSerializer(source='customer', many=False, read_only=True)

    line_items = serializers.IntegerField(read_only=True)

    status_text = serializers.CharField(source='get_status_display', read_only=True)

    overdue = serializers.BooleanField(required=False, read_only=True)

    reference = serializers.CharField(required=True)

    class Meta:
        model = SalesOrder

        fields = [
            'pk',
            'creation_date',
            'customer',
            'customer_detail',
            'customer_reference',
            'description',
            'line_items',
            'link',
            'notes',
            'overdue',
            'reference',
            'responsible',
            'status',
            'status_text',
            'shipment_date',
            'target_date',
        ]

        read_only_fields = [
            'status',
            'creation_date',
            'shipment_date',
        ]


class SalesOrderAllocationSerializer(InvenTreeModelSerializer):
    """
    Serializer for the SalesOrderAllocation model.
    This includes some fields from the related model objects.
    """

    part = serializers.PrimaryKeyRelatedField(source='item.part', read_only=True)
    order = serializers.PrimaryKeyRelatedField(source='line.order', many=False, read_only=True)
    serial = serializers.CharField(source='get_serial', read_only=True)
    quantity = serializers.FloatField(read_only=True)
    location = serializers.PrimaryKeyRelatedField(source='item.location', many=False, read_only=True)

    # Extra detail fields
    order_detail = SalesOrderSerializer(source='line.order', many=False, read_only=True)
    part_detail = PartBriefSerializer(source='item.part', many=False, read_only=True)
    item_detail = StockItemSerializer(source='item', many=False, read_only=True)
    location_detail = LocationSerializer(source='item.location', many=False, read_only=True)

    def __init__(self, *args, **kwargs):

        order_detail = kwargs.pop('order_detail', False)
        part_detail = kwargs.pop('part_detail', False)
        item_detail = kwargs.pop('item_detail', False)
        location_detail = kwargs.pop('location_detail', False)

        super().__init__(*args, **kwargs)

        if not order_detail:
            self.fields.pop('order_detail')

        if not part_detail:
            self.fields.pop('part_detail')

        if not item_detail:
            self.fields.pop('item_detail')

        if not location_detail:
            self.fields.pop('location_detail')

    class Meta:
        model = SalesOrderAllocation

        fields = [
            'pk',
            'line',
            'serial',
            'quantity',
            'location',
            'location_detail',
            'item',
            'item_detail',
            'order',
            'order_detail',
            'part',
            'part_detail',
        ]


class SOLineItemSerializer(InvenTreeModelSerializer):
    """ Serializer for a SalesOrderLineItem object """

    def __init__(self, *args, **kwargs):

        part_detail = kwargs.pop('part_detail', False)
        order_detail = kwargs.pop('order_detail', False)
        allocations = kwargs.pop('allocations', False)

        super().__init__(*args, **kwargs)

        if part_detail is not True:
            self.fields.pop('part_detail')

        if order_detail is not True:
            self.fields.pop('order_detail')

        if allocations is not True:
            self.fields.pop('allocations')

    order_detail = SalesOrderSerializer(source='order', many=False, read_only=True)
    part_detail = PartBriefSerializer(source='part', many=False, read_only=True)
    allocations = SalesOrderAllocationSerializer(many=True, read_only=True)

    quantity = serializers.FloatField()

    allocated = serializers.FloatField(source='allocated_quantity', read_only=True)
    fulfilled = serializers.FloatField(source='fulfilled_quantity', read_only=True)
    
    sale_price = InvenTreeMoneySerializer(
        max_digits=19,
        decimal_places=4,
        allow_null=True
    )

    sale_price_string = serializers.CharField(source='sale_price', read_only=True)

    sale_price_currency = serializers.ChoiceField(
        choices=currency_code_mappings(),
        help_text=_('Sale price currency'),
    )

    class Meta:
        model = SalesOrderLineItem

        fields = [
            'pk',
            'allocated',
            'allocations',
            'quantity',
            'fulfilled',
            'reference',
            'notes',
            'order',
            'order_detail',
            'part',
            'part_detail',
            'sale_price',
            'sale_price_currency',
            'sale_price_string',
        ]


class SOAttachmentSerializer(InvenTreeAttachmentSerializer):
    """
    Serializers for the SalesOrderAttachment model
    """

    attachment = InvenTreeAttachmentSerializerField(required=True)

    class Meta:
        model = SalesOrderAttachment

        fields = [
            'pk',
            'order',
            'attachment',
            'filename',
            'comment',
            'upload_date',
        ]

        read_only_fields = [
            'upload_date',
        ]
