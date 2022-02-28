# -*- coding: utf-8 -*-

import logging

from django.apps import AppConfig
from django.core.exceptions import AppRegistryNotReady
from django.conf import settings
from django.contrib.auth import get_user_model

from InvenTree.ready import isInTestMode, canAppAccessDatabase
from .config import get_setting
import InvenTree.tasks


logger = logging.getLogger("inventree")


class InvenTreeConfig(AppConfig):
    name = 'InvenTree'

    def ready(self):

        if canAppAccessDatabase():

            self.remove_obsolete_tasks()

            self.start_background_tasks()

            if not isInTestMode():
                self.update_exchange_rates()

            self.add_user_on_startup()

    def remove_obsolete_tasks(self):
        """
        Delete any obsolete scheduled tasks in the database
        """

        obsolete = [
            'InvenTree.tasks.delete_expired_sessions',
            'stock.tasks.delete_old_stock_items',
        ]

        try:
            from django_q.models import Schedule
        except AppRegistryNotReady:  # pragma: no cover
            return

        # Remove any existing obsolete tasks
        Schedule.objects.filter(func__in=obsolete).delete()

    def start_background_tasks(self):

        try:
            from django_q.models import Schedule
        except AppRegistryNotReady:  # pragma: no cover
            return

        logger.info("Starting background tasks...")

        # Remove successful task results from the database
        InvenTree.tasks.schedule_task(
            'InvenTree.tasks.delete_successful_tasks',
            schedule_type=Schedule.DAILY,
        )

        # Check for InvenTree updates
        InvenTree.tasks.schedule_task(
            'InvenTree.tasks.check_for_updates',
            schedule_type=Schedule.DAILY
        )

        # Heartbeat to let the server know the background worker is running
        InvenTree.tasks.schedule_task(
            'InvenTree.tasks.heartbeat',
            schedule_type=Schedule.MINUTES,
            minutes=15
        )

        # Keep exchange rates up to date
        InvenTree.tasks.schedule_task(
            'InvenTree.tasks.update_exchange_rates',
            schedule_type=Schedule.DAILY,
        )

        # Delete old error messages
        InvenTree.tasks.schedule_task(
            'InvenTree.tasks.delete_old_error_logs',
            schedule_type=Schedule.DAILY,
        )

        # Delete old notification records
        InvenTree.tasks.schedule_task(
            'common.tasks.delete_old_notifications',
            schedule_type=Schedule.DAILY,
        )

    def update_exchange_rates(self):
        """
        Update exchange rates each time the server is started, *if*:

        a) Have not been updated recently (one day or less)
        b) The base exchange rate has been altered
        """

        try:
            from djmoney.contrib.exchange.models import ExchangeBackend

            from InvenTree.tasks import update_exchange_rates
            from common.settings import currency_code_default
        except AppRegistryNotReady:  # pragma: no cover
            pass

        base_currency = currency_code_default()

        update = False

        try:
            backend = ExchangeBackend.objects.get(name='InvenTreeExchange')

            last_update = backend.last_update

            if last_update is None:
                # Never been updated
                logger.info("Exchange backend has never been updated")
                update = True

            # Backend currency has changed?
            if not base_currency == backend.base_currency:
                logger.info(f"Base currency changed from {backend.base_currency} to {base_currency}")
                update = True

        except (ExchangeBackend.DoesNotExist):
            logger.info("Exchange backend not found - updating")
            update = True

        except:
            # Some other error - potentially the tables are not ready yet
            return

        if update:
            try:
                update_exchange_rates()
            except Exception as e:
                logger.error(f"Error updating exchange rates: {e}")

    def add_user_on_startup(self):
        """Add a user on startup"""

        # get values
        add_user = get_setting(
            'INVENTREE_SET_USER',
            settings.CONFIG.get('set_user', False)
        )
        add_email = get_setting(
            'INVENTREE_SET_EMAIL',
            settings.CONFIG.get('set_email', False)
        )
        add_password = get_setting(
            'INVENTREE_SET_PASSWORD',
            settings.CONFIG.get('set_password', False)
        )

        # check if all values are present
        if not (add_user and add_email and add_password):
            logger.warn('Not all required settings for adding a user on startup are present:\nINVENTREE_SET_USER, INVENTREE_SET_EMAIL, INVENTREE_SET_PASSWORD')
            return

        # create user
        user = get_user_model()
        try:
            new_user = user.objects.create_user(add_user, add_email, add_password)
            logger.info(f'User {str(new_user)} was created!')
        except Exception as _e:
            print(_e)
