# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist

from django.conf.urls import url, include

from rest_framework import generics, permissions
from rest_framework.views import APIView
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework import status

from .serializers import UserSerializer, OwnerSerializer

from .models import RuleSet, Owner, check_user_role


class OwnerList(generics.ListAPIView):
    """
    List API endpoint for Owner model. Cannot create.
    """

    queryset = Owner.objects.all()
    serializer_class = OwnerSerializer


class OwnerDetail(generics.RetrieveAPIView):
    """
    Detail API endpoint for Owner model. Cannot edit or delete
    """

    queryset = Owner.objects.all()
    serializer_class = OwnerSerializer


class RoleDetails(APIView):
    """
    API endpoint which lists the available role permissions
    for the current user

    (Requires authentication)
    """

    permission_classes = [
        permissions.IsAuthenticated
    ]

    def get(self, request, *args, **kwargs):

        user = request.user

        roles = {}

        for ruleset in RuleSet.RULESET_CHOICES:

            role, text = ruleset

            permissions = []

            for permission in RuleSet.RULESET_PERMISSIONS:
                if check_user_role(user, role, permission):

                    permissions.append(permission)

            if len(permissions) > 0:
                roles[role] = permissions
            else:
                roles[role] = None

        data = {
            'user': user.pk,
            'username': user.username,
            'roles': roles,
            'is_staff': user.is_staff,
            'is_superuser': user.is_superuser,
        }

        return Response(data)


class UserDetail(generics.RetrieveAPIView):
    """ Detail endpoint for a single user """

    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = (permissions.IsAuthenticated,)


class UserList(generics.ListAPIView):
    """ List endpoint for detail on all users """

    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = (permissions.IsAuthenticated,)


class GetAuthToken(APIView):
    """ Return authentication token for an authenticated user. """

    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def get(self, request, *args, **kwargs):
        return self.login(request)

    def delete(self, request):
        return self.logout(request)

    def login(self, request):

        if request.user.is_authenticated:
            # Get the user token (or create one if it does not exist)
            token, created = Token.objects.get_or_create(user=request.user)
            return Response({
                'token': token.key,
            })

        else:
            return Response({
                'error': 'User not authenticated',
            })

    def logout(self, request):
        try:
            request.user.auth_token.delete()
            return Response({"success": "Successfully logged out."},
                            status=status.HTTP_202_ACCEPTED)
        except (AttributeError, ObjectDoesNotExist):
            return Response({"error": "Bad request"},
                            status=status.HTTP_400_BAD_REQUEST)


user_urls = [

    url(r'roles/?$', RoleDetails.as_view(), name='api-user-roles'),
    url(r'token/?$', GetAuthToken.as_view(), name='api-token'),

    url(r'^owner/', include([
        url(r'^(?P<pk>[0-9]+)/$', OwnerDetail.as_view(), name='api-owner-detail'),
        url(r'^.*$', OwnerList.as_view(), name='api-owner-list'),
    ])),

    url(r'^(?P<pk>[0-9]+)/?$', UserDetail.as_view(), name='user-detail'),
    url(r'^$', UserList.as_view()),
]
