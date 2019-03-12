from __future__ import absolute_import
from nameko.events import EventDispatcher, event_handler
from nameko.rpc import rpc
from nameko_sqlalchemy import DatabaseSession

from .exceptions import NotFound
from .models import DeclarativeBase, Order, Address, OrderStatus, \
    OrderingException, OrderDetail
from .schemas import *
from datetime import datetime as dt
from uuid import uuid4
import time
import json


class OrdersService:
    name = 'orders_service'

    db = DatabaseSession(DeclarativeBase)
    fire_event = EventDispatcher()

    @rpc
    def list_order(self):
        orders = self.db.query(Order).all()

        result = [OrderSchema().dump(order).data
                  for order in orders]

        return result

    @rpc
    def get_order(self, id):
        order = self.db.query(Order).get(id)

        if not order:
            raise NotFound('Order with id {} not found'.format(id))

        return OrderSchema().dump(order).data

    @rpc
    def create_order(self, payload):
        order = Order()
        order.id = str(uuid4().__hash__())
        order.customer_id = payload['customer_id']
        order.cardholder_name = payload['cardholder_name']
        order.card_number = payload['card_number']
        order.order_date = dt.utcnow()
        order.card_expiration = payload['card_expiration']
        order.card_security_number = payload['card_security_number']
        order.order_status_id = OrderStatus.AwaitingValidation.value
        order.is_draft = False

        address = payload['address']
        order.address = Address()
        order.address.id = str(uuid4().__hash__())
        order.address.street1 = address['street1']
        order.address.street2 = address['street2']
        order.address.state = address['state']
        order.address.city = address['city']
        order.address.zip_code = address['zip_code']
        order.address.country = address['country']

        order_details = payload['order_items']

        for od in order_details:
            order_detail = OrderDetail()
            order_detail.id = str(uuid4().__hash__())
            order_detail.product_id = od['product_id']
            order_detail.product_name = od['product_name']
            order_detail.units = od['units']
            order_detail.discount = od['discount']
            order_detail.unit_price = od['unit_price']

            order.order_items.append(order_detail)

        self.db.add(order)
        self.db.commit()

        payload = {
            'order_id': order.id,
            'order_stock_items': [{'product_id': od.product_id, 'units': od.units}
                                  for od in order.order_items]
        }

        order_data = OrderStatusChangedToAwaitingValidationEvent().dumps(payload).data

        order = OrderSchema().dump(order).data
        self.fire_event('order_await_valid', order_data)

        return order

    @rpc
    def update_order(self, payload):
        pass

    @event_handler('products_service', 'rejected_order_stock')
    def handle_rejected_order_stock(self, payload):
        order_id = payload['order_id']

        order = self.db.query(Order).get(order_id)

        if order is None:
            raise NotFound()

        rejected_stock = [item['product_id'] for item in payload['order_stock_items']]
        order.set_cancelled_status_when_stock_is_rejected(rejected_stock)

        self.db.add(order)
        self.db.commit()

    @event_handler('products_service', 'confirmed_order_stock')
    def handle_confirmed_order_stock(self, payload):
        order_id = payload['order_id']

        order = self.db.query(Order).get(order_id)

        if order is None:
            raise NotFound()

        order.set_stock_confirmed_status()

        self.db.add(order)
        self.db.commit()

        time.sleep(5)
        self.fire_event('confirmed_order_stock', {'order_id': order_id})

        # raise NotImplementedError()

    @event_handler('payments_service', 'order_payment_succeeded')
    def handle_order_payment_succeeded(self, payload):
        order_id = payload['order_id']

        order = self.db.query(Order).get(order_id)

        if order is None:
            raise NotFound()

        order.set_paid_status()

        self.db.add(order)
        self.db.commit()

        payload = OrderStatusChangedToPaidEvent()
        payload.order_id = order_id

        payload.order_stock_items = [
            {
                'product_id': item.product_id,
                'units': item.units
            }
            for item in order.order_items
        ]

        payload = payload.dumps(payload).data
        time.sleep(5)
        self.fire_event('order_paid', payload)
