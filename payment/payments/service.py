from __future__ import absolute_import
from nameko.events import EventDispatcher, event_handler
import os
import json


class PaymentsService:
    name = 'payments_service'
    fire_event = EventDispatcher()

    @event_handler('orders_service', 'confirmed_order_stock')
    def handle_payment(self, payload):
        order_id = payload['order_id']

        payment_succeeded = os.getenv('PAYMENT_SUCCEEDED', True)

        if payment_succeeded:
            self.fire_event('order_payment_succeeded', {'order_id': order_id})
        else:
            self.fire_event('order_payment_failed', {'order_id': order_id})
