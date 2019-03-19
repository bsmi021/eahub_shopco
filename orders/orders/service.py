from __future__ import absolute_import
from nameko.events import EventDispatcher, event_handler
from nameko.rpc import rpc
from nameko_sqlalchemy import DatabaseSession

from .exceptions import NotFound
from .models import *
from .schemas import *
from datetime import datetime as dt
from uuid import uuid4
import time
import json
import logging

logger = logging.getLogger(__name__)

REPLICATE_DB_EVENT = 'replicate_db_event'
ORDER_COMMAND_SERVICE = 'command_orders'
BUYER_COMMAND_SERVICE = 'command_buyers'
ORDER_QUERY_SERVICE = 'query_orders'
BUYER_QUERY_SERVICE = 'query_buyers'
PAYMENTS_SERVICE = 'command_payments'
PRODUCTS_SERVICE = 'command_products'
BASKET_SERVICE = 'command_basket'


class CommandOrders:
    name = ORDER_COMMAND_SERVICE
    dispatch = EventDispatcher()
    db = DatabaseSession(DeclarativeBase)

    def _get_order(self, order_id):
        return self.db.query(CommandOrderModel).get(order_id)

    def _save_order(self, order):
        self.db.add(order)
        self.db.commit()

    @event_handler(ORDER_COMMAND_SERVICE, 'order_started')
    def validate_or_add_buyer_on_order_started(self, event_msg):
        """
        When an order is created, the system will check for a buyer, if the buyer does not exist in
        the buyer repository the system will create the buyer, it will then validate or add a new payment
        method for the buyer, followed by asking for the order to be changed to submitted
        :param event_msg:
        :return:
        """

        started_event = json.loads(event_msg)

        buyer = self.db.query(CommandBuyerModel).filter(CommandBuyerModel.user_id == started_event['user_id']).first()
        buyer_originally_existed = buyer is not None

        if not buyer_originally_existed:
            buyer = CommandBuyerModel(started_event['user_id'], started_event['user_name'])

        payment = buyer.verify_or_add_payment_method(f'Payment Method on {datetime.datetime.utcnow()}',
                                                     started_event['card_number'],
                                                     started_event['security_number'],
                                                     started_event['card_type_id'],
                                                     started_event['cardholder_name'],
                                                     started_event['expiration'])

        self.db.add(buyer)
        self.db.commit()

        order_submitted = dict(
            order_id=started_event['order']['id'],
            order_status_id=started_event['order']['order_status_id'],
            buyer_name=buyer.name
        )

        payment = {
            'buyer_id': buyer.id,
            'payment_id': payment.id,
            'order_id': started_event['order']['id']
        }

        # fire message that the buyer/payment method were verified
        self.dispatch('buyer_payment_verified', json.dumps(payment))

        # fire message that the order should be marked as submitted
        self.dispatch('order_status_submitted', json.dumps(order_submitted))

        logger.info(
            f'Buyer {buyer.id} and related payment method was validated for order_id: {started_event["order"]["id"]}')

    @event_handler(BASKET_SERVICE, 'user_checkout_accepted')
    def checkout_accepted(self, event_msg):
        address = CommandAddressModel(event_msg.get('street_1'),
                                      event_msg.get('street_2', None),
                                      event_msg.get('city'),
                                      event_msg.get('state'),
                                      event_msg.get('country'),
                                      event_msg.get('zip_code'))

        pass

    @event_handler(PRODUCTS_SERVICE, 'rejected_order_stock')
    def rejected_order_stock(self, payload):
        order_id = payload['order_id']

        order = self._get_order(order_id)

        if order is None:
            raise NotFound(f'No order found for order_id: {order_id}')

        rejected_stock = [item['product_id'] for item in payload['order_stock_items']]
        order.set_cancelled_status_when_stock_is_rejected(rejected_stock)

        self._save_order(order)

    @event_handler(PRODUCTS_SERVICE, 'confirmed_order_stock')
    def rejected_order_stock(self, payload):
        order_id = payload['order_id']

        order = self._get_order(order_id)

        if order is None:
            raise NotFound(f'No order found for order_id: {order_id}')

        order.set_stock_confirmed_status()

        self._save_order(order)

        time.sleep(15)
        self.dispatch('order_stock_confirmed', json.dumps({'order_id': order_id}))

    @event_handler(PAYMENTS_SERVICE, 'order_payment_succeeded')
    def order_payment_succeeded(self, payload):
        payload = json.loads(payload)
        order_id = payload['order_id']

        order = self._get_order(order_id)

        if order is None:
            raise NotFound(f'No order found for order_id: {order_id}')

        order.set_paid_status()

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
        time.sleep(15)
        self.dispatch('order_paid', payload)

# class OrdersService:
#     name = 'orders_service'
#
#     db = DatabaseSession(DeclarativeBase)
#     fire_event = EventDispatcher()
#
#     @rpc
#     def list_order(self):
#         orders = self.db.query(Order).all()
#
#         result = [OrderSchema().dump(order).data
#                   for order in orders]
#
#         return result
#
#     @rpc
#     def get_order(self, id):
#         order = self.db.query(Order).get(id)
#
#         if not order:
#             raise NotFound('Order with id {} not found'.format(id))
#
#         return OrderSchema().dump(order).data
#
#     @rpc
#     def create_order(self, payload):
#         order = Order()
#         order.id = str(uuid4().__hash__())
#         order.customer_id = payload['customer_id']
#         order.cardholder_name = payload['cardholder_name']
#         order.card_number = payload['card_number']
#         order.order_date = dt.utcnow()
#         order.card_expiration = payload['card_expiration']
#         order.card_security_number = payload['card_security_number']
#         order.order_status_id = OrderStatus.AwaitingValidation.value
#         order.is_draft = False
#
#         address = payload['address']
#         order.address = Address()
#         order.address.id = str(uuid4().__hash__())
#         order.address.street1 = address['street1']
#         order.address.street2 = address['street2']
#         order.address.state = address['state']
#         order.address.city = address['city']
#         order.address.zip_code = address['zip_code']
#         order.address.country = address['country']
#
#         order_details = payload['order_items']
#
#         for od in order_details:
#             order_detail = OrderDetail()
#             order_detail.id = str(uuid4().__hash__())
#             order_detail.product_id = od['product_id']
#             order_detail.product_name = od['product_name']
#             order_detail.units = od['units']
#             order_detail.discount = od['discount']
#             order_detail.unit_price = od['unit_price']
#
#             order.order_items.append(order_detail)
#
#         self.db.add(order)
#         self.db.commit()
#
#         payload = {
#             'order_id': order.id,
#             'order_stock_items': [{'product_id': od.product_id, 'units': od.units}
#                                   for od in order.order_items]
#         }
#
#         order_data = OrderStatusChangedToAwaitingValidationEvent().dumps(payload).data
#
#         order = OrderSchema().dump(order).data
#         self.fire_event('order_await_valid', order_data)
#
#         return order
#
#     @rpc
#     def update_order(self, payload):
#         pass
#
#     @event_handler('products_service', 'rejected_order_stock')
#     def handle_rejected_order_stock(self, payload):
#         order_id = payload['order_id']
#
#         order = self.db.query(Order).get(order_id)
#
#         if order is None:
#             raise NotFound()
#
#         rejected_stock = [item['product_id'] for item in payload['order_stock_items']]
#         order.set_cancelled_status_when_stock_is_rejected(rejected_stock)
#
#         self.db.add(order)
#         self.db.commit()
#
#     @event_handler('products_service', 'confirmed_order_stock')
#     def handle_confirmed_order_stock(self, payload):
#         order_id = payload['order_id']
#
#         order = self.db.query(Order).get(order_id)
#
#         if order is None:
#             raise NotFound()
#
#         order.set_stock_confirmed_status()
#
#         self.db.add(order)
#         self.db.commit()
#
#         time.sleep(5)
#         self.fire_event('confirmed_order_stock', {'order_id': order_id})
#
#         # raise NotImplementedError()
#
#     @event_handler('payments_service', 'order_payment_succeeded')
#     def handle_order_payment_succeeded(self, payload):
#         order_id = payload['order_id']
#
#         order = self.db.query(Order).get(order_id)
#
#         if order is None:
#             raise NotFound()
#
#         order.set_paid_status()
#
#         self.db.add(order)
#         self.db.commit()
#
#         payload = OrderStatusChangedToPaidEvent()
#         payload.order_id = order_id
#
#         payload.order_stock_items = [
#             {
#                 'product_id': item.product_id,
#                 'units': item.units
#             }
#             for item in order.order_items
#         ]
#
#         payload = payload.dumps(payload).data
#         time.sleep(5)
#         self.fire_event('order_paid', payload)
