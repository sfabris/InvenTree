"""
Provides system status functionality checks.
"""
# -*- coding: utf-8 -*-

from django.utils.translation import ugettext_lazy as _

import logging
from datetime import datetime, timedelta

from django_q.models import Success
from django_q.monitor import Stat

from django.conf import settings


logger = logging.getLogger("inventree")


def is_worker_running(**kwargs):
    """
    Return True if the background worker process is oprational
    """

    clusters = Stat.get_all()

    if len(clusters) > 0:
        # TODO - Introspect on any cluster information
        return True

    """
    Sometimes Stat.get_all() returns [].
    In this case we have the 'heartbeat' task running every 15 minutes.
    Check to see if we have a result within the last 20 minutes
    """

    now = datetime.now()
    past = now - timedelta(minutes=20)

    results = Success.objects.filter(
        func='InvenTree.tasks.heartbeat',
        started__gte=past
    )

    # If any results are returned, then the background worker is running!
    return results.exists()


def is_email_configured():
    """
    Check if email backend is configured.

    NOTE: This does not check if the configuration is valid!
    """

    configured = True

    if not settings.EMAIL_HOST:
        configured = False

        # Display warning unless in test mode
        if not settings.TESTING:
            logger.warning("EMAIL_HOST is not configured")

    if not settings.EMAIL_HOST_USER:
        configured = False

        # Display warning unless in test mode
        if not settings.TESTING:
            logger.warning("EMAIL_HOST_USER is not configured")

    if not settings.EMAIL_HOST_PASSWORD:
        configured = False

        # Display warning unless in test mode
        if not settings.TESTING:
            logger.warning("EMAIL_HOST_PASSWORD is not configured")

    return configured


def check_system_health(**kwargs):
    """
    Check that the InvenTree system is running OK.

    Returns True if all system checks pass.
    """

    result = True

    if not is_worker_running(**kwargs):
        result = False
        logger.warning(_("Background worker check failed"))

    if not is_email_configured():
        result = False
        logger.warning(_("Email backend not configured"))

    if not result:
        logger.warning(_("InvenTree system health checks failed"))

    return result
