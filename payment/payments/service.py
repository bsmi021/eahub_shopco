from __future__ import absolute_import

import os
import json
import logging


from nameko.events import EventDispatcher, event_handler
from datetime import datetime as dt

logger = logging.getLogger(__name__)

COMMAND_SERVICE = 'command_payments'
ORDERS_SERVICE = 'command_orders'


class Command:
    name = COMMAND_SERVICE
    dispatch = EventDispatcher()

    @event_handler(ORDERS_SERVICE, 'order_status_changed_to_stock_confirmed')
    def verify_payment(self, payload):
        """
        This service doesn't do much, it's here to complete the flow, it will by default
        always approve all payment methods.
        :param payload:
        :return:
        """
        if isinstance(payload, str):
            payload = json.loads(payload)

        order_id = payload['order_id']

        payment_succeeded = os.getenv('PAYMENT_SUCCEEDED', True)

        payload = { 'order_id': order_id }

        if payment_succeeded:
            self.dispatch('order_payment_succeeded', payload)
            logger.info(f"{dt.utcnow()}: Payment Succeeded for order_id: {payload['order_id']}")
        else:
            self.dispatch('order_payment_failed', payload)
            logger.info(f"{dt.utcnow()}: Payment Declined for order_id: {payload['order_id']}")