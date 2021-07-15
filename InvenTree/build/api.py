"""
JSON API for the Build app
"""

# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf.urls import url, include

from rest_framework import filters
from rest_framework import generics

from django_filters.rest_framework import DjangoFilterBackend
from django_filters import rest_framework as rest_filters

from InvenTree.api import AttachmentMixin
from InvenTree.helpers import str2bool, isNull
from InvenTree.status_codes import BuildStatus

from .models import Build, BuildItem, BuildOrderAttachment
from .serializers import BuildAttachmentSerializer, BuildSerializer, BuildItemSerializer


class BuildFilter(rest_filters.FilterSet):
    """
    Custom filterset for BuildList API endpoint
    """

    status = rest_filters.NumberFilter(label='Status')

    active = rest_filters.BooleanFilter(label='Build is active', method='filter_active')

    def filter_active(self, queryset, name, value):

        if str2bool(value):
            queryset = queryset.filter(status__in=BuildStatus.ACTIVE_CODES)
        else:
            queryset = queryset.exclude(status__in=BuildStatus.ACTIVE_CODES)

        return queryset

    overdue = rest_filters.BooleanFilter(label='Build is overdue', method='filter_overdue')

    def filter_overdue(self, queryset, name, value):

        if str2bool(value):
            queryset = queryset.filter(Build.OVERDUE_FILTER)
        else:
            queryset = queryset.exclude(Build.OVERDUE_FILTER)

        return queryset


class BuildList(generics.ListCreateAPIView):
    """ API endpoint for accessing a list of Build objects.

    - GET: Return list of objects (with filters)
    - POST: Create a new Build object
    """

    queryset = Build.objects.all()
    serializer_class = BuildSerializer
    filterset_class = BuildFilter

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    filter_fields = [
        'sales_order',
    ]

    ordering_fields = [
        'reference',
        'part__name',
        'status',
        'creation_date',
        'target_date',
        'completion_date',
        'quantity',
        'issued_by',
        'responsible',
    ]

    search_fields = [
        'reference',
        'part__name',
        'title',
    ]

    def get_queryset(self):
        """
        Override the queryset filtering,
        as some of the fields don't natively play nicely with DRF
        """

        queryset = super().get_queryset().prefetch_related('part')

        queryset = BuildSerializer.annotate_queryset(queryset)

        return queryset

    def filter_queryset(self, queryset):

        queryset = super().filter_queryset(queryset)

        params = self.request.query_params

        # Filter by "parent"
        parent = params.get('parent', None)

        if parent is not None:
            queryset = queryset.filter(parent=parent)

        # Filter by "ancestor" builds
        ancestor = params.get('ancestor', None)

        if ancestor is not None:
            try:
                ancestor = Build.objects.get(pk=ancestor)

                descendants = ancestor.get_descendants(include_self=True)

                queryset = queryset.filter(
                    parent__pk__in=[b.pk for b in descendants]
                )

            except (ValueError, Build.DoesNotExist):
                pass

        # Filter by associated part?
        part = params.get('part', None)

        if part is not None:
            queryset = queryset.filter(part=part)

        # Filter by 'date range'
        min_date = params.get('min_date', None)
        max_date = params.get('max_date', None)

        if min_date is not None and max_date is not None:
            queryset = Build.filterByDate(queryset, min_date, max_date)

        return queryset

    def get_serializer(self, *args, **kwargs):

        try:
            part_detail = str2bool(self.request.GET.get('part_detail', None))
        except AttributeError:
            part_detail = None

        kwargs['part_detail'] = part_detail

        return self.serializer_class(*args, **kwargs)


class BuildDetail(generics.RetrieveUpdateAPIView):
    """ API endpoint for detail view of a Build object """

    queryset = Build.objects.all()
    serializer_class = BuildSerializer


class BuildItemList(generics.ListCreateAPIView):
    """ API endpoint for accessing a list of BuildItem objects

    - GET: Return list of objects
    - POST: Create a new BuildItem object
    """

    serializer_class = BuildItemSerializer

    def get_serializer(self, *args, **kwargs):

        try:
            params = self.request.query_params

            kwargs['part_detail'] = str2bool(params.get('part_detail', False))
            kwargs['build_detail'] = str2bool(params.get('build_detail', False))
            kwargs['location_detail'] = str2bool(params.get('location_detail', False))
        except AttributeError:
            pass
        
        return self.serializer_class(*args, **kwargs)

    def get_queryset(self):
        """ Override the queryset method,
        to allow filtering by stock_item.part
        """

        query = BuildItem.objects.all()

        query = query.select_related('stock_item')
        query = query.prefetch_related('stock_item__part')
        query = query.prefetch_related('stock_item__part__category')

        return query

    def filter_queryset(self, queryset):

        queryset = super().filter_queryset(queryset)

        params = self.request.query_params

        # Does the user wish to filter by part?
        part_pk = params.get('part', None)

        if part_pk:
            queryset = queryset.filter(stock_item__part=part_pk)

        # Filter by output target
        output = params.get('output', None)

        if output:

            if isNull(output):
                queryset = queryset.filter(install_into=None)
            else:
                queryset = queryset.filter(install_into=output)

        return queryset

    filter_backends = [
        DjangoFilterBackend,
    ]

    filter_fields = [
        'build',
        'stock_item',
        'install_into',
    ]


class BuildAttachmentList(generics.ListCreateAPIView, AttachmentMixin):
    """
    API endpoint for listing (and creating) BuildOrderAttachment objects
    """

    queryset = BuildOrderAttachment.objects.all()
    serializer_class = BuildAttachmentSerializer

    filter_backends = [
        DjangoFilterBackend,
    ]

    filter_fields = [
        'build',
    ]


class BuildAttachmentDetail(generics.RetrieveUpdateDestroyAPIView, AttachmentMixin):
    """
    Detail endpoint for a BuildOrderAttachment object
    """

    queryset = BuildOrderAttachment.objects.all()
    serializer_class = BuildAttachmentSerializer


build_api_urls = [

    # Attachments
    url(r'^attachment/', include([
        url(r'^(?P<pk>\d+)/', BuildAttachmentDetail.as_view(), name='api-build-attachment-detail'),
        url('^.*$', BuildAttachmentList.as_view(), name='api-build-attachment-list'),
    ])),

    # Build Items
    url(r'^item/', include([
        url('^.*$', BuildItemList.as_view(), name='api-build-item-list')
    ])),

    # Build Detail
    url(r'^(?P<pk>\d+)/', BuildDetail.as_view(), name='api-build-detail'),

    # Build List
    url(r'^.*$', BuildList.as_view(), name='api-build-list'),
]
