from __future__ import absolute_import

import json
import logging
import time
from datetime import datetime as dt

from nameko.events import event_handler, EventDispatcher
from nameko_sqlalchemy import DatabaseSession
from nameko.rpc import rpc
from nameko.web.handlers import http

from .exceptions import NotFound
from .models import *

import mongoengine

logger = logging.getLogger(__name__)

REPLICATE_DB_EVENT = 'replicate_db_event'
ORDER_COMMAND_SERVICE = 'command_orders'
BUYER_COMMAND_SERVICE = 'command_buyers'
ORDER_QUERY_SERVICE = 'query_orders'
BUYER_QUERY_SERVICE = 'query_buyers'
PAYMENTS_SERVICE = 'command_payments'
PRODUCTS_SERVICE = 'command_products'
BASKET_SERVICE = 'basket_service'
WAREHOUSE_COMMAND_SERVICE = 'command_item'


class CommandOrders:
    """
    Integration service used to create and maintain the lifecycle of an order.
    """

    name = ORDER_COMMAND_SERVICE
    dispatch = EventDispatcher()
    db = DatabaseSession(DeclarativeBase)

    def fire_replicated_db_event(self, data):
        """
        Fires off a database replication event with an order payload
        :param data:
        :return:
        """
        self.dispatch(REPLICATE_DB_EVENT, json.dumps(data))

    def _get_order(self, order_id):
        """
        Returns an order based on the provided order id, this is an internal method only,
        orders cannot be created from external sources, only from integration event processing.
        :param order_id:
        :return:
        """
        return self.db.query(Order).get(order_id)

    def _save_order(self, order):
        """
        Saves an order to the command database, and kicks off a replication event.
        :param order:
        :return:
        """
        self.db.add(order)
        self.db.commit()

        data = {
            'id': order.id,
            'customer_id': order.customer_id,
            'address': {
                'id': order.address.id,
                'street_1': order.address.street1,
                'street_2': order.address.street2,
                'city': order.address.city,
                'state': order.address.state,
                'zip_code': order.address.zip_code,
                'country': order.address.country
            },
            'order_status_id': order.order_status_id,
            'order_date': str(order.order_date),
            'description': order.description,
            'created_at': str(order.created_at),
            'updated_at': str(order.updated_at),
            'order_items': [{'id': item.id,
                             'product_id': item.product_id,
                             'product_name': item.product_name,
                             'unit_price': item.unit_price,
                             'discount': item.discount,
                             'units': item.units}
                            for item in order.order_items]
        }

        """At this point a buyer may not exist due to domain processing, check to see if it 
        exists before trying to add it to the dictionary"""
        if order.buyer is not None:
            data['buyer_id'] = order.buyer_id
            data['buyer'] = {
                'id': order.buyer.id,
                'name': order.buyer.name
            }

        """At this point a payment_method may not exist due to domain processing, check to see if it
        exists before trying to add it to the dictionary"""
        if order.payment_method is not None:
            data['payment_method_id'] = order.payment_method_id
            data['payment_method'] = {
                'id': order.payment_method.id,
                'alias': order.payment_method.alias,
                'cardholder_name': order.payment_method.cardholder_name,
                'expiration': order.payment_method.expiration,
                'card_number': order.payment_method.card_number[-4:]
            }

        self.fire_replicated_db_event(data)

    @event_handler(ORDER_COMMAND_SERVICE, 'order_started')
    def validate_or_add_buyer_on_order_started(self, payload):
        """
        domain event handler

        When an order is created, the system will check for a buyer, if the buyer does not exist in
        the buyer repository the system will create the buyer, it will then validate or add a new payment
        method for the buyer, followed by asking for the order to be changed to submitted
        :param payload:
        :return:
        """
        if isinstance(payload, str):
            payload = json.loads(payload)

        buyer = self.db.query(Buyer).filter(Buyer.user_id == payload['user_id']).first()
        buyer_originally_existed = buyer is not None

        if not buyer_originally_existed:
            buyer = Buyer(payload['user_id'], payload['user_name'])

        payment = buyer.verify_or_add_payment_method(f'Payment Method on {datetime.datetime.utcnow()}',
                                                     payload['card_number'],
                                                     payload['security_number'],
                                                     payload['card_type_id'],
                                                     payload['cardholder_name'],
                                                     payload['expiration'])

        self.db.add(buyer)
        self.db.commit()

        order_submitted_msg = dict(
            order_id=payload['order']['id'],
            order_status_id=payload['order']['order_status_id'],
            buyer_name=buyer.name
        )

        buyer_msg = {
            'buyer_id': buyer.id,
            'payment_id': payment.id,
            'order_id': payload['order']['id']
        }

        # fire message that the buyer/payment method were verified
        self.dispatch('buyer_payment_verified', buyer_msg)

        # fire message that the order should be marked as submitted
        self.dispatch('order_status_submitted', order_submitted_msg)

        logger.info(
            f'{dt.utcnow()}: Buyer {buyer.id} and related payment method was validated for order_id: \
                {payload["order"]["id"]}')

    @event_handler(ORDER_COMMAND_SERVICE, 'buyer_payment_verified')
    def buyer_payment_verified(self, event_msg):
        """
        domain event handler
        :param event_msg:
        :return:
        """
        order_id = event_msg.get('order_id')

        order = self.db.query(Order).get(order_id)

        if order is None:
            raise NotFound(f'No order found for id {order_id}.')

        buyer = self.db.query(Buyer).get(event_msg.get('buyer_id'))
        payment = self.db.query(PaymentMethod).get(event_msg.get('payment_id'))

        order.buyer = buyer
        order.payment_method = payment

        order.set_awaiting_validation_status()

        self._save_order(order)

        payload = {
            'order_id': order.id,
            'order_stock_items': [{'product_id': od.product_id, 'units': od.units}
                                  for od in order.order_items]
        }

        self.dispatch('order_status_changed_to_awaiting_validation', payload)

        logger.info(f'{dt.utcnow()}: order_id: {order.id} status set to Awaiting Validation')

    @event_handler(ORDER_COMMAND_SERVICE, 'order_status_changed_to_submitted')
    def order_submitted(self, payload):
        """
        domain event handler
        :param payload:
        :return:
        """
        pass

    @event_handler(ORDER_COMMAND_SERVICE, 'ship_order')
    def ship_order(self, payload):
        """
        domain event handler
        :param payload:
        :return:
        """
        if isinstance(payload, str):
            payload = json.loads(payload)

        order = self._get_order(payload['id'])

        if order is None:
            raise NotFound(f'No order found for order_id: {payload["order_id"]}')

        order.set_shipped_status()

        self._save_order(order)

        self.dispatch('order_status_changed_to_shipped', payload)

    @event_handler(BASKET_SERVICE, 'user_checkout_accepted')
    def create_order_from_basket(self, payload):
        """
        integration event handler
        :param payload:
        :return:
        """
        if isinstance(payload, str):
            payload = json.loads(payload)

        # self.dispatch('order_started', {'user_id': payload['user_id']})

        street_1 = payload.get('street_1')
        street_2 = payload.get('street_2')
        city = payload.get('city')
        state = payload.get('state')
        zip_code = payload.get('zip_code')
        country = payload.get('country')

        address = CommandAddressModel(street_1, street_2, city, state, country, zip_code)

        order = Order(payload['user_id'], address)

        for item in payload.get('basket')['items']:
            order.add_order_item(item['product_id'], item['product_name'],
                                 item['unit_price'], item['quantity'])

        self._save_order(order)

        validate_buyer_payload = {
            'user_id': payload['user_id'],
            'user_name': payload['user_name'],
            'card_number': payload['card_number'],
            'cardholder_name': payload['cardholder_name'],
            'expiration': payload['expiration'],
            'card_type_id': payload['card_type_id'],
            'security_number': payload['security_number'],
            'order': {"id": order.id, "order_status_id": order.order_status_id}
        }

        self.dispatch('order_status_changed_to_submitted', {'order_id': order.id})
        self.dispatch('order_started', validate_buyer_payload)

        logger.info(f'{dt.utcnow()}: order_id: {order.id} submitted for buyer_id: {payload["user_id"]}.')

    @event_handler(WAREHOUSE_COMMAND_SERVICE, 'confirmed_order_stock')
    def order_stock_confirmed(self, payload):
        """
        integration event handler

        When the stock for an order is confirmed, update the order, and
        trigger a order_stock_confirmed message
        :param payload:
        :return:
        """

        if isinstance(payload, str):
            payload = json.loads(payload)

        order_id = payload['order_id']

        order = self._get_order(order_id)

        if order is None:
            raise NotFound()

        order.set_stock_confirmed_status()

        self._save_order(order)

        #time.sleep(5)
        self.dispatch('order_status_changed_to_stock_confirmed', {'order_id': order_id})

        logger.info(f'{dt.utcnow()}: order_id: {order.id} status set to STOCK_CONFIRMED')

    @event_handler(WAREHOUSE_COMMAND_SERVICE, 'rejected_order_stock')
    def handle_rejected_order_stock(self, payload):
        """
        integration event handler

        When there is not enough inventory of one or more order_items the order is rejected due to insufficient stock.
        :param payload:
        :return:
        """

        if isinstance(payload, str):
            payload = json.loads(payload)

        order_id = payload['order_id']

        order = self.db.query(Order).get(order_id)

        if order is None:
            raise NotFound(f'No order found for order_id: {order_id}')

        rejected_stock = [item['product_id'] for item in payload['order_stock_items']]
        order.set_cancelled_status_when_stock_is_rejected(rejected_stock)

        self._save_order(order)

        self.dispatch('order_status_changed_to_cancelled', payload)

    @event_handler(PAYMENTS_SERVICE, 'order_payment_succeeded')
    def order_payment_succeeded(self, payload):
        """
        integration event handler

        Once the payment is validated update the order to indicated that the it is paid, then fire an event
        with a collection of the order items, the products service will pick it up and decrement inventory
        :param payload:
        :return:
        """

        if isinstance(payload, str):
            payload = json.loads(payload)

        order_id = payload['order_id']

        order = self._get_order(order_id)

        if order is None:
            raise NotFound(f'No order found for order_id: {order_id}')

        order.set_paid_status()

        self._save_order(order)

        payload = {
            'order_id': order_id,
            'order_stock_items': [{'product_id': item.product_id,
                                   'units': item.units}
                                  for item in order.order_items]
        }

        #time.sleep(15)
        self.dispatch('order_status_changed_to_paid', payload)

        logger.info(f'{dt.utcnow()}: order_id: {order.id} status set to PAID.')


class QueryOrders:
    """
    Query service for external access to order information, this is a
    read-only service.
    """
    name = ORDER_QUERY_SERVICE

    @event_handler(ORDER_COMMAND_SERVICE, REPLICATE_DB_EVENT)
    def normalize_db(self, data):
        """ used to write changes into the orders query db"""
        if isinstance(data, str):
            data = json.loads(data)
        try:
            buyer = None
            payment_method = None
            print('No Buyer' if data['buyer'] is None else data['buyer']['id'])
            if data['buyer'] is not None:
                buyer = QueryBuyerModel(
                    id=data['buyer']['id'],
                    name=data['buyer']['name']
                )
            if data['payment_method'] is not None:
                payment_method = QueryPaymentMethod(
                    id=data['payment_method']['id'],
                    alias=data['payment_method']['alias'],
                    cardholder_name=data['payment_method']['cardholder_name'],
                    expiration=data['payment_method']['expiration'],
                    card_number=data['payment_method']['card_number']
                )

            order = QueryOrderModel.objects.get(id=data['id'])
            order.update(
                customer_id=data.get('customer_id', order.customer_id),
                order_status_id=data.get('order_status_id', order.order_status_id),
                description=data.get('description', order.description),
                updated_at=data.get('updated_at', order.updated_at),
                created_at=data.get('created_at', order.created_at),
                buyer_id=data.get('buyer_id', 0),
                order_date=data.get('order_date', order.order_date),
                buyer=buyer,
                payment_method=payment_method
            )
            order.reload()


            logger.info(f'{dt.utcnow()}: Order Id {data["id"]} has been updated in the query database.')
        except mongoengine.DoesNotExist:
            """ Create the order in the query database since it doesn't exist already"""
            QueryOrderModel(
                id=data['id'],
                customer_id=data['customer_id'],
                order_status_id=data['order_status_id'],
                order_date=data['order_date'],
                updated_at=data['updated_at'],
                created_at=data['created_at'],
                buyer_id=data.get('buyer_id',None),
                order_items=[QueryOrderItemModel(
                    id=item['id'],
                    product_id=item['product_id'],
                    product_name=item['product_name'],
                    unit_price=item['unit_price'],
                    discount=item['discount'],
                    units=item['units']
                )
                    for item in data['order_items']],
                address=QueryAddressModel(
                    id=data['address']['id'],
                    street_1=data['address']['street_1'],
                    street_2=data['address']['street_2'],
                    city=data['address']['city'],
                    state=data['address']['state'],
                    zip_code=data['address']['zip_code'],
                    country=data['address']['country']
                )
            ).save()
            logger.info(f'{dt.utcnow()}: Order Id {data["id"]} added to the query database.')
        except Exception as e:
            logger.error(f'{dt.utcnow()}: Unable to perform replication for order_id: {data["id"]}\n{e}')
            return e

    @rpc
    @http('GET', '/orders/<int:id>')
    def get(self, request, id):
        """
        returns a single order based on the provided id
        :param id:
        :return:
        """
        try:
            order = QueryOrderModel.objects.get(id=id)
            return order.to_json()
        except mongoengine.DoesNotExist as e:
            return e
        except Exception as e:
            return e

    @rpc
    def get_by_buyer_id(self, buyer_id, num_page = 1, limit = 10):
        """
        returns a collection of orders based on the provided buyer_id
        :param num_page:
        :param limit:
        :param buyer_id:
        :return:
        """
        try:
            offset = (num_page - 1) * limit
            orders = QueryOrderModel.objects(buyer_id=buyer_id)\
                .skip(offset).limit(limit)
            return orders.to_json()
        except mongoengine.DoesNotExist as e:
            return e
        except Exception as e:
            return e
