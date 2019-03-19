from __future__ import absolute_import

import os
import json

from nameko.events import EventDispatcher, event_handler

COMMAND_SERVICE = 'command_payments'
ORDERS_SERVICE = 'command_orders'


class Command:
    name = COMMAND_SERVICE
    dispatch = EventDispatcher()

    @event_handler(ORDERS_SERVICE, 'order_stock_confirmed')
    def verify_payment(self, payload):
        """
        This service doesn't do much, it's here to complete the flow, it will by default
        always approve all payment methods.
        :param payload:
        :return:
        """
        payload = json.loads(payload)
        order_id = payload['order_id']

        payment_succeeded = os.getenv('PAYMENT_SUCCEEDED', True)

        if payment_succeeded:
            self.dispatch('payment_succeeded', json.dumps({'order_id': order_id}))
        else:
            self.dispatch('payment_failed', json.dumps({'order_id': order_id}))
