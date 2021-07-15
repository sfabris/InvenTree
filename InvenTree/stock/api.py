"""
JSON API for the Stock app
"""

from django.conf.urls import url, include
from django.urls import reverse
from django.http import JsonResponse
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _

from rest_framework import status
from rest_framework.serializers import ValidationError
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import generics, filters, permissions

from django_filters.rest_framework import DjangoFilterBackend
from django_filters import rest_framework as rest_filters

from .models import StockLocation, StockItem
from .models import StockItemTracking
from .models import StockItemAttachment
from .models import StockItemTestResult

from part.models import Part, PartCategory
from part.serializers import PartBriefSerializer

from company.models import Company, SupplierPart
from company.serializers import CompanySerializer, SupplierPartSerializer

from order.models import PurchaseOrder
from order.serializers import POSerializer

import common.settings
import common.models

from .serializers import StockItemSerializer
from .serializers import LocationSerializer, LocationBriefSerializer
from .serializers import StockTrackingSerializer
from .serializers import StockItemAttachmentSerializer
from .serializers import StockItemTestResultSerializer

from InvenTree.views import TreeSerializer
from InvenTree.helpers import str2bool, isNull
from InvenTree.api import AttachmentMixin

from decimal import Decimal, InvalidOperation

from datetime import datetime, timedelta


class StockCategoryTree(TreeSerializer):
    title = _('Stock')
    model = StockLocation

    @property
    def root_url(self):
        return reverse('stock-index')

    def get_items(self):
        return StockLocation.objects.all().prefetch_related('stock_items', 'children')

    permission_classes = [
        permissions.IsAuthenticated,
    ]


class StockDetail(generics.RetrieveUpdateDestroyAPIView):
    """ API detail endpoint for Stock object

    get:
    Return a single StockItem object

    post:
    Update a StockItem

    delete:
    Remove a StockItem
    """

    queryset = StockItem.objects.all()
    serializer_class = StockItemSerializer

    def get_queryset(self, *args, **kwargs):

        queryset = super().get_queryset(*args, **kwargs)
        queryset = StockItemSerializer.prefetch_queryset(queryset)
        queryset = StockItemSerializer.annotate_queryset(queryset)

        return queryset

    def get_serializer(self, *args, **kwargs):

        kwargs['part_detail'] = True
        kwargs['location_detail'] = True
        kwargs['supplier_part_detail'] = True
        kwargs['test_detail'] = True
        kwargs['context'] = self.get_serializer_context()

        return self.serializer_class(*args, **kwargs)

    def update(self, request, *args, **kwargs):
        """
        Record the user who updated the item
        """

        # TODO: Record the user!
        # user = request.user

        return super().update(request, *args, **kwargs)


class StockAdjust(APIView):
    """
    A generic class for handling stocktake actions.

    Subclasses exist for:

    - StockCount: count stock items
    - StockAdd: add stock items
    - StockRemove: remove stock items
    - StockTransfer: transfer stock items
    """

    queryset = StockItem.objects.none()

    allow_missing_quantity = False

    def get_items(self, request):
        """
        Return a list of items posted to the endpoint.
        Will raise validation errors if the items are not
        correctly formatted.
        """

        _items = []

        if 'item' in request.data:
            _items = [request.data['item']]
        elif 'items' in request.data:
            _items = request.data['items']
        else:
            _items = []

        if len(_items) == 0:
            raise ValidationError(_('Request must contain list of stock items'))

        # List of validated items
        self.items = []

        for entry in _items:

            if not type(entry) == dict:
                raise ValidationError(_('Improperly formatted data'))

            # Look for a 'pk' value (use 'id' as a backup)
            pk = entry.get('pk', entry.get('id', None))

            try:
                pk = int(pk)
            except (ValueError, TypeError):
                raise ValidationError(_('Each entry must contain a valid integer primary-key'))

            try:
                item = StockItem.objects.get(pk=pk)
            except (StockItem.DoesNotExist):
                raise ValidationError({
                    pk: [_('Primary key does not match valid stock item')]
                })

            if self.allow_missing_quantity and 'quantity' not in entry:
                entry['quantity'] = item.quantity

            try:
                quantity = Decimal(str(entry.get('quantity', None)))
            except (ValueError, TypeError, InvalidOperation):
                raise ValidationError({
                    pk: [_('Invalid quantity value')]
                })

            if quantity < 0:
                raise ValidationError({
                    pk: [_('Quantity must not be less than zero')]
                })

            self.items.append({
                'item': item,
                'quantity': quantity
            })

        # Extract 'notes' field
        self.notes = str(request.data.get('notes', ''))


class StockCount(StockAdjust):
    """
    Endpoint for counting stock (performing a stocktake).
    """

    def post(self, request, *args, **kwargs):

        self.get_items(request)

        n = 0

        for item in self.items:

            if item['item'].stocktake(item['quantity'], request.user, notes=self.notes):
                n += 1

        return Response({'success': _('Updated stock for {n} items').format(n=n)})


class StockAdd(StockAdjust):
    """
    Endpoint for adding a quantity of stock to an existing StockItem
    """

    def post(self, request, *args, **kwargs):

        self.get_items(request)

        n = 0

        for item in self.items:
            if item['item'].add_stock(item['quantity'], request.user, notes=self.notes):
                n += 1

        return Response({"success": "Added stock for {n} items".format(n=n)})


class StockRemove(StockAdjust):
    """
    Endpoint for removing a quantity of stock from an existing StockItem.
    """

    def post(self, request, *args, **kwargs):

        self.get_items(request)

        n = 0

        for item in self.items:

            if item['quantity'] > item['item'].quantity:
                raise ValidationError({
                    item['item'].pk: [_('Specified quantity exceeds stock quantity')]
                })

            if item['item'].take_stock(item['quantity'], request.user, notes=self.notes):
                n += 1

        return Response({"success": "Removed stock for {n} items".format(n=n)})


class StockTransfer(StockAdjust):
    """
    API endpoint for performing stock movements
    """

    allow_missing_quantity = True

    def post(self, request, *args, **kwargs):

        data = request.data

        try:
            location = StockLocation.objects.get(pk=data.get('location', None))
        except (ValueError, StockLocation.DoesNotExist):
            raise ValidationError({'location': [_('Valid location must be specified')]})

        n = 0

        self.get_items(request)

        for item in self.items:

            if item['quantity'] > item['item'].quantity:
                raise ValidationError({
                    item['item'].pk: [_('Specified quantity exceeds stock quantity')]
                })

            # If quantity is not specified, move the entire stock
            if item['quantity'] in [0, None]:
                item['quantity'] = item['item'].quantity

            if item['item'].move(location, self.notes, request.user, quantity=item['quantity']):
                n += 1

        return Response({'success': _('Moved {n} parts to {loc}').format(
            n=n,
            loc=str(location),
        )})


class StockLocationList(generics.ListCreateAPIView):
    """ API endpoint for list view of StockLocation objects:

    - GET: Return list of StockLocation objects
    - POST: Create a new StockLocation
    """

    queryset = StockLocation.objects.all()
    serializer_class = LocationSerializer

    def filter_queryset(self, queryset):
        """
        Custom filtering:
        - Allow filtering by "null" parent to retrieve top-level stock locations
        """

        queryset = super().filter_queryset(queryset)

        params = self.request.query_params

        loc_id = params.get('parent', None)

        cascade = str2bool(params.get('cascade', False))

        # Do not filter by location
        if loc_id is None:
            pass
        # Look for top-level locations
        elif isNull(loc_id):

            # If we allow "cascade" at the top-level, this essentially means *all* locations
            if not cascade:
                queryset = queryset.filter(parent=None)

        else:

            try:
                location = StockLocation.objects.get(pk=loc_id)

                # All sub-locations to be returned too?
                if cascade:
                    parents = location.get_descendants(include_self=True)
                    parent_ids = [p.id for p in parents]
                    queryset = queryset.filter(parent__in=parent_ids)

                else:
                    queryset = queryset.filter(parent=location)

            except (ValueError, StockLocation.DoesNotExist):
                pass

        return queryset

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    filter_fields = [
    ]

    search_fields = [
        'name',
        'description',
    ]

    ordering_fields = [
        'name',
        'items',
    ]


class StockFilter(rest_filters.FilterSet):
    """
    FilterSet for StockItem LIST API
    """

    # Part name filters
    name = rest_filters.CharFilter(label='Part name (case insensitive)', field_name='part__name', lookup_expr='iexact')
    name_contains = rest_filters.CharFilter(label='Part name contains (case insensitive)', field_name='part__name', lookup_expr='icontains')
    name_regex = rest_filters.CharFilter(label='Part name (regex)', field_name='part__name', lookup_expr='iregex')

    # Part IPN filters
    IPN = rest_filters.CharFilter(label='Part IPN (case insensitive)', field_name='part__IPN', lookup_expr='iexact')
    IPN_contains = rest_filters.CharFilter(label='Part IPN contains (case insensitive)', field_name='part__IPN', lookup_expr='icontains')
    IPN_regex = rest_filters.CharFilter(label='Part IPN (regex)', field_name='part__IPN', lookup_expr='iregex')

    # Part attribute filters
    assembly = rest_filters.BooleanFilter(label="Assembly", field_name='part__assembly')
    active = rest_filters.BooleanFilter(label="Active", field_name='part__active')

    min_stock = rest_filters.NumberFilter(label='Minimum stock', field_name='quantity', lookup_expr='gte')
    max_stock = rest_filters.NumberFilter(label='Maximum stock', field_name='quantity', lookup_expr='lte')

    in_stock = rest_filters.BooleanFilter(label='In Stock', method='filter_in_stock')

    def filter_in_stock(self, queryset, name, value):

        if str2bool(value):
            queryset = queryset.filter(StockItem.IN_STOCK_FILTER)
        else:
            queryset = queryset.exclude(StockItem.IN_STOCK_FILTER)

        return queryset

    batch = rest_filters.CharFilter(label="Batch code filter (case insensitive)", lookup_expr='iexact')

    batch_regex = rest_filters.CharFilter(label="Batch code filter (regex)", field_name='batch', lookup_expr='iregex')

    is_building = rest_filters.BooleanFilter(label="In production")

    # Serial number filtering
    serial_gte = rest_filters.NumberFilter(label='Serial number GTE', field_name='serial', lookup_expr='gte')
    serial_lte = rest_filters.NumberFilter(label='Serial number LTE', field_name='serial', lookup_expr='lte')
    serial = rest_filters.NumberFilter(label='Serial number', field_name='serial', lookup_expr='exact')

    serialized = rest_filters.BooleanFilter(label='Has serial number', method='filter_serialized')

    def filter_serialized(self, queryset, name, value):

        if str2bool(value):
            queryset = queryset.exclude(serial=None)
        else:
            queryset = queryset.filter(serial=None)

        return queryset

    installed = rest_filters.BooleanFilter(label='Installed in other stock item', method='filter_installed')

    def filter_installed(self, queryset, name, value):
        """
        Filter stock items by "belongs_to" field being empty
        """

        if str2bool(value):
            queryset = queryset.exclude(belongs_to=None)
        else:
            queryset = queryset.filter(belongs_to=None)

        return queryset

    sent_to_customer = rest_filters.BooleanFilter(label='Sent to customer', method='filter_sent_to_customer')

    def filter_sent_to_customer(self, queryset, name, value):

        if str2bool(value):
            queryset = queryset.exclude(customer=None)
        else:
            queryset = queryset.filter(customer=None)
            
        return queryset

    depleted = rest_filters.BooleanFilter(label='Depleted', method='filter_depleted')

    def filter_depleted(self, queryset, name, value):

        if str2bool(value):
            queryset = queryset.filter(quantity__lte=0)
        else:
            queryset = queryset.exclude(quantity__lte=0)

        return queryset

    has_purchase_price = rest_filters.BooleanFilter(label='Has purchase price', method='filter_has_purchase_price')

    def filter_has_purchase_price(self, queryset, name, value):

        if str2bool(value):
            queryset = queryset.exclude(purcahse_price=None)
        else:
            queryset = queryset.filter(purchase_price=None)

        return queryset

    # Update date filters
    updated_before = rest_filters.DateFilter(label='Updated before', field_name='updated', lookup_expr='lte')
    updated_after = rest_filters.DateFilter(label='Updated after', field_name='updated', lookup_expr='gte')


class StockList(generics.ListCreateAPIView):
    """ API endpoint for list view of Stock objects

    - GET: Return a list of all StockItem objects (with optional query filters)
    - POST: Create a new StockItem
    """

    serializer_class = StockItemSerializer
    queryset = StockItem.objects.all()
    filterset_class = StockFilter

    def create(self, request, *args, **kwargs):
        """
        Create a new StockItem object via the API.

        We override the default 'create' implementation.

        If a location is *not* specified, but the linked *part* has a default location,
        we can pre-fill the location automatically.
        """

        user = request.user

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        item = serializer.save()

        # A location was *not* specified - try to infer it
        if 'location' not in request.data:
            item.location = item.part.get_default_location()

        # An expiry date was *not* specified - try to infer it!
        if 'expiry_date' not in request.data:

            if item.part.default_expiry > 0:
                item.expiry_date = datetime.now().date() + timedelta(days=item.part.default_expiry)

        # Finally, save the item
        item.save(user=user)

        # Return a response
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def list(self, request, *args, **kwargs):
        """
        Override the 'list' method, as the StockLocation objects
        are very expensive to serialize.

        So, we fetch and serialize the required StockLocation objects only as required.
        """

        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
        else:
            serializer = self.get_serializer(queryset, many=True)

        data = serializer.data

        # Keep track of which related models we need to query
        location_ids = set()
        part_ids = set()
        supplier_part_ids = set()

        # Iterate through each StockItem and grab some data
        for item in data:
            loc = item['location']
            if loc:
                location_ids.add(loc)

            part = item['part']
            if part:
                part_ids.add(part)

            sp = item['supplier_part']

            if sp:
                supplier_part_ids.add(sp)

        # Do we wish to include Part detail?
        if str2bool(request.query_params.get('part_detail', False)):

            # Fetch only the required Part objects from the database
            parts = Part.objects.filter(pk__in=part_ids).prefetch_related(
                'category',
            )

            part_map = {}

            for part in parts:
                part_map[part.pk] = PartBriefSerializer(part).data

            # Now update each StockItem with the related Part data
            for stock_item in data:
                part_id = stock_item['part']
                stock_item['part_detail'] = part_map.get(part_id, None)

        # Do we wish to include SupplierPart detail?
        if str2bool(request.query_params.get('supplier_part_detail', False)):

            supplier_parts = SupplierPart.objects.filter(pk__in=supplier_part_ids)

            supplier_part_map = {}

            for part in supplier_parts:
                supplier_part_map[part.pk] = SupplierPartSerializer(part).data

            for stock_item in data:
                part_id = stock_item['supplier_part']
                stock_item['supplier_part_detail'] = supplier_part_map.get(part_id, None)

        # Do we wish to include StockLocation detail?
        if str2bool(request.query_params.get('location_detail', False)):

            # Fetch only the required StockLocation objects from the database
            locations = StockLocation.objects.filter(pk__in=location_ids).prefetch_related(
                'parent',
                'children',
            )

            location_map = {}

            # Serialize each StockLocation object
            for location in locations:
                location_map[location.pk] = LocationBriefSerializer(location).data

            # Now update each StockItem with the related StockLocation data
            for stock_item in data:
                loc_id = stock_item['location']
                stock_item['location_detail'] = location_map.get(loc_id, None)

        """
        Determine the response type based on the request.
        a) For HTTP requests (e.g. via the browseable API) return a DRF response
        b) For AJAX requests, simply return a JSON rendered response.

        Note: b) is about 100x quicker than a), because the DRF framework adds a lot of cruft
        """

        if page is not None:
            return self.get_paginated_response(data)
        elif request.is_ajax():
            return JsonResponse(data, safe=False)
        else:
            return Response(data)

    def get_queryset(self, *args, **kwargs):

        queryset = super().get_queryset(*args, **kwargs)

        queryset = StockItemSerializer.prefetch_queryset(queryset)
        queryset = StockItemSerializer.annotate_queryset(queryset)

        return queryset

    def filter_queryset(self, queryset):

        params = self.request.query_params

        queryset = super().filter_queryset(queryset)

        # Perform basic filtering:
        # Note: We do not let DRF filter here, it be slow AF

        supplier_part = params.get('supplier_part', None)

        if supplier_part:
            queryset = queryset.filter(supplier_part=supplier_part)

        belongs_to = params.get('belongs_to', None)

        if belongs_to:
            queryset = queryset.filter(belongs_to=belongs_to)

        build = params.get('build', None)

        if build:
            queryset = queryset.filter(build=build)

        sales_order = params.get('sales_order', None)

        if sales_order:
            queryset = queryset.filter(sales_order=sales_order)

        purchase_order = params.get('purchase_order', None)

        if purchase_order is not None:
            queryset = queryset.filter(purchase_order=purchase_order)

        # Filter stock items which are installed in another (specific) stock item
        installed_in = params.get('installed_in', None)

        if installed_in:
            # Note: The "installed_in" field is called "belongs_to"
            queryset = queryset.filter(belongs_to=installed_in)

        if common.settings.stock_expiry_enabled():

            # Filter by 'expired' status
            expired = params.get('expired', None)

            if expired is not None:
                expired = str2bool(expired)

                if expired:
                    queryset = queryset.filter(StockItem.EXPIRED_FILTER)
                else:
                    queryset = queryset.exclude(StockItem.EXPIRED_FILTER)

            # Filter by 'stale' status
            stale = params.get('stale', None)

            if stale is not None:
                stale = str2bool(stale)

                # How many days to account for "staleness"?
                stale_days = common.models.InvenTreeSetting.get_setting('STOCK_STALE_DAYS')

                if stale_days > 0:
                    stale_date = datetime.now().date() + timedelta(days=stale_days)

                    stale_filter = StockItem.IN_STOCK_FILTER & ~Q(expiry_date=None) & Q(expiry_date__lt=stale_date)

                    if stale:
                        queryset = queryset.filter(stale_filter)
                    else:
                        queryset = queryset.exclude(stale_filter)

        # Filter by customer
        customer = params.get('customer', None)

        if customer:
            queryset = queryset.filter(customer=customer)

        # Filter by 'allocated' parts?
        allocated = params.get('allocated', None)

        if allocated is not None:
            allocated = str2bool(allocated)

            if allocated:
                # Filter StockItem with either build allocations or sales order allocations
                queryset = queryset.filter(Q(sales_order_allocations__isnull=False) | Q(allocations__isnull=False))
            else:
                # Filter StockItem without build allocations or sales order allocations
                queryset = queryset.filter(Q(sales_order_allocations__isnull=True) & Q(allocations__isnull=True))

        # Does the client wish to filter by the Part ID?
        part_id = params.get('part', None)

        if part_id:
            try:
                part = Part.objects.get(pk=part_id)

                # Do we wish to filter *just* for this part, or also for parts *under* this one?
                include_variants = str2bool(params.get('include_variants', True))

                if include_variants:
                    # Filter by any parts "under" the given part
                    parts = part.get_descendants(include_self=True)

                    queryset = queryset.filter(part__in=parts)

                else:
                    queryset = queryset.filter(part=part)

            except (ValueError, Part.DoesNotExist):
                raise ValidationError({"part": "Invalid Part ID specified"})

        # Does the client wish to filter by the 'ancestor'?
        anc_id = params.get('ancestor', None)

        if anc_id:
            try:
                ancestor = StockItem.objects.get(pk=anc_id)

                # Only allow items which are descendants of the specified StockItem
                queryset = queryset.filter(id__in=[item.pk for item in ancestor.children.all()])

            except (ValueError, Part.DoesNotExist):
                raise ValidationError({"ancestor": "Invalid ancestor ID specified"})

        # Does the client wish to filter by stock location?
        loc_id = params.get('location', None)

        cascade = str2bool(params.get('cascade', True))

        if loc_id is not None:

            # Filter by 'null' location (i.e. top-level items)
            if isNull(loc_id):
                queryset = queryset.filter(location=None)
            else:
                try:
                    # If '?cascade=true' then include items which exist in sub-locations
                    if cascade:
                        location = StockLocation.objects.get(pk=loc_id)
                        queryset = queryset.filter(location__in=location.getUniqueChildren())
                    else:
                        queryset = queryset.filter(location=loc_id)

                except (ValueError, StockLocation.DoesNotExist):
                    pass

        # Does the client wish to filter by part category?
        cat_id = params.get('category', None)

        if cat_id:
            try:
                category = PartCategory.objects.get(pk=cat_id)
                queryset = queryset.filter(part__category__in=category.getUniqueChildren())

            except (ValueError, PartCategory.DoesNotExist):
                raise ValidationError({"category": "Invalid category id specified"})

        # Filter by StockItem status
        status = params.get('status', None)

        if status:
            queryset = queryset.filter(status=status)

        # Filter by supplier_part ID
        supplier_part_id = params.get('supplier_part', None)

        if supplier_part_id:
            queryset = queryset.filter(supplier_part=supplier_part_id)

        # Filter by company (either manufacturer or supplier)
        company = params.get('company', None)

        if company is not None:
            queryset = queryset.filter(Q(supplier_part__supplier=company) | Q(supplier_part__manufacturer_part__manufacturer=company))

        # Filter by supplier
        supplier = params.get('supplier', None)

        if supplier is not None:
            queryset = queryset.filter(supplier_part__supplier=supplier)

        # Filter by manufacturer
        manufacturer = params.get('manufacturer', None)

        if manufacturer is not None:
            queryset = queryset.filter(supplier_part__manufacturer_part__manufacturer=manufacturer)

        # Optionally, limit the maximum number of returned results
        max_results = params.get('max_results', None)

        if max_results is not None:
            try:
                max_results = int(max_results)

                if max_results > 0:
                    queryset = queryset[:max_results]
            except (ValueError):
                pass

        # Also ensure that we pre-fecth all the related items
        queryset = queryset.prefetch_related(
            'part',
            'part__category',
            'location'
        )

        return queryset

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    ordering_fields = [
        'part__name',
        'part__IPN',
        'updated',
        'stocktake_date',
        'expiry_date',
        'quantity',
        'status',
    ]

    ordering = [
        'part__name'
    ]

    search_fields = [
        'serial',
        'batch',
        'part__name',
        'part__IPN',
        'part__description',
        'location__name',
    ]


class StockAttachmentList(generics.ListCreateAPIView, AttachmentMixin):
    """
    API endpoint for listing (and creating) a StockItemAttachment (file upload)
    """

    queryset = StockItemAttachment.objects.all()
    serializer_class = StockItemAttachmentSerializer

    filter_backends = [
        DjangoFilterBackend,
        filters.OrderingFilter,
        filters.SearchFilter,
    ]

    filter_fields = [
        'stock_item',
    ]


class StockAttachmentDetail(generics.RetrieveUpdateDestroyAPIView, AttachmentMixin):
    """
    Detail endpoint for StockItemAttachment
    """

    queryset = StockItemAttachment.objects.all()
    serializer_class = StockItemAttachmentSerializer


class StockItemTestResultDetail(generics.RetrieveUpdateDestroyAPIView):
    """
    Detail endpoint for StockItemTestResult
    """

    queryset = StockItemTestResult.objects.all()
    serializer_class = StockItemTestResultSerializer


class StockItemTestResultList(generics.ListCreateAPIView):
    """
    API endpoint for listing (and creating) a StockItemTestResult object.
    """

    queryset = StockItemTestResult.objects.all()
    serializer_class = StockItemTestResultSerializer

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    filter_fields = [
        'stock_item',
        'test',
        'user',
        'result',
        'value',
    ]

    ordering = 'date'

    def get_serializer(self, *args, **kwargs):
        try:
            kwargs['user_detail'] = str2bool(self.request.query_params.get('user_detail', False))
        except:
            pass

        kwargs['context'] = self.get_serializer_context()

        return self.serializer_class(*args, **kwargs)

    def perform_create(self, serializer):
        """
        Create a new test result object.

        Also, check if an attachment was uploaded alongside the test result,
        and save it to the database if it were.
        """

        # Capture the user information
        test_result = serializer.save()
        test_result.user = self.request.user
        test_result.save()


class StockTrackingDetail(generics.RetrieveAPIView):
    """
    Detail API endpoint for StockItemTracking model
    """

    queryset = StockItemTracking.objects.all()
    serializer_class = StockTrackingSerializer


class StockTrackingList(generics.ListAPIView):
    """ API endpoint for list view of StockItemTracking objects.

    StockItemTracking objects are read-only
    (they are created by internal model functionality)

    - GET: Return list of StockItemTracking objects
    """

    queryset = StockItemTracking.objects.all()
    serializer_class = StockTrackingSerializer

    def get_serializer(self, *args, **kwargs):
        try:
            kwargs['item_detail'] = str2bool(self.request.query_params.get('item_detail', False))
        except:
            pass

        try:
            kwargs['user_detail'] = str2bool(self.request.query_params.get('user_detail', False))
        except:
            pass

        kwargs['context'] = self.get_serializer_context()

        return self.serializer_class(*args, **kwargs)

    def list(self, request, *args, **kwargs):

        queryset = self.filter_queryset(self.get_queryset())

        serializer = self.get_serializer(queryset, many=True)

        data = serializer.data

        # Attempt to add extra context information to the historical data
        for item in data:
            deltas = item['deltas']

            if not deltas:
                deltas = {}

            # Add location detail
            if 'location' in deltas:
                try:
                    location = StockLocation.objects.get(pk=deltas['location'])
                    serializer = LocationSerializer(location)
                    deltas['location_detail'] = serializer.data
                except:
                    pass

            # Add stockitem detail
            if 'stockitem' in deltas:
                try:
                    stockitem = StockItem.objects.get(pk=deltas['stockitem'])
                    serializer = StockItemSerializer(stockitem)
                    deltas['stockitem_detail'] = serializer.data
                except:
                    pass

            # Add customer detail
            if 'customer' in deltas:
                try:
                    customer = Company.objects.get(pk=deltas['customer'])
                    serializer = CompanySerializer(customer)
                    deltas['customer_detail'] = serializer.data
                except:
                    pass

            # Add purchaseorder detail
            if 'purchaseorder' in deltas:
                try:
                    order = PurchaseOrder.objects.get(pk=deltas['purchaseorder'])
                    serializer = POSerializer(order)
                    deltas['purchaseorder_detail'] = serializer.data
                except:
                    pass

        if request.is_ajax():
            return JsonResponse(data, safe=False)
        else:
            return Response(data)

    def create(self, request, *args, **kwargs):
        """ Create a new StockItemTracking object

        Here we override the default 'create' implementation,
        to save the user information associated with the request object.
        """

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Record the user who created this Part object
        item = serializer.save()
        item.user = request.user
        item.system = False

        # quantity field cannot be explicitly adjusted  here
        item.quantity = item.item.quantity
        item.save()

        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    filter_fields = [
        'item',
        'user',
    ]

    ordering = '-date'

    ordering_fields = [
        'date',
    ]

    search_fields = [
        'title',
        'notes',
    ]


class LocationDetail(generics.RetrieveUpdateDestroyAPIView):
    """ API endpoint for detail view of StockLocation object

    - GET: Return a single StockLocation object
    - PATCH: Update a StockLocation object
    - DELETE: Remove a StockLocation object
    """

    queryset = StockLocation.objects.all()
    serializer_class = LocationSerializer


stock_api_urls = [
    url(r'^location/', include([
        url(r'^(?P<pk>\d+)/', LocationDetail.as_view(), name='api-location-detail'),
        url(r'^.*$', StockLocationList.as_view(), name='api-location-list'),
    ])),

    # Endpoints for bulk stock adjustment actions
    url(r'^count/', StockCount.as_view(), name='api-stock-count'),
    url(r'^add/', StockAdd.as_view(), name='api-stock-add'),
    url(r'^remove/', StockRemove.as_view(), name='api-stock-remove'),
    url(r'^transfer/', StockTransfer.as_view(), name='api-stock-transfer'),

    # StockItemAttachment API endpoints
    url(r'^attachment/', include([
        url(r'^(?P<pk>\d+)/', StockAttachmentDetail.as_view(), name='api-stock-attachment-detail'),
        url(r'^$', StockAttachmentList.as_view(), name='api-stock-attachment-list'),
    ])),

    # StockItemTestResult API endpoints
    url(r'^test/', include([
        url(r'^(?P<pk>\d+)/', StockItemTestResultDetail.as_view(), name='api-stock-test-result-detail'),
        url(r'^.*$', StockItemTestResultList.as_view(), name='api-stock-test-result-list'),
    ])),

    # StockItemTracking API endpoints
    url(r'^track/', include([
        url(r'^(?P<pk>\d+)/', StockTrackingDetail.as_view(), name='api-stock-tracking-detail'),
        url(r'^.*$', StockTrackingList.as_view(), name='api-stock-tracking-list'),
    ])),

    url(r'^tree/', StockCategoryTree.as_view(), name='api-stock-tree'),

    # Detail for a single stock item
    url(r'^(?P<pk>\d+)/', StockDetail.as_view(), name='api-stock-detail'),

    # Anything else
    url(r'^.*$', StockList.as_view(), name='api-stock-list'),
]
