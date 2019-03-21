import logging
from nameko.events import event_handler, EventDispatcher
from nameko.rpc import rpc
from nameko_redis import Redis
from .exceptions import NotFound
from datetime import datetime as dt
import json

from .schemas import *
from .models import *


logger = logging.getLogger(__name__)


BASKET_SERVICE = 'basket_service'
ORDERS_SERVICE = 'command_orders'


class BasketService:
    name = BASKET_SERVICE
    dispatch = EventDispatcher()

    redis = Redis('development')

    @rpc
    def get_basket_by_id(self, buyer_id):
        """
        Gets a basket, if one doesn't exist a new basket is created
        :param buyer_id:
        :return:
        """
        basket = self.redis.get(buyer_id)

        if basket is None:
            logger.info(f'No basket found for {buyer_id}. Creating one now.')
            basket = {
                'buyer_id': buyer_id,
                'items': []
            }
        else:
            basket = json.loads(basket)
            basket = {
                'buyer_id': basket.get('buyer_id'),
                'items': basket.get('items')
            }

        return basket

    @rpc
    def update_basket(self, basket):
        """
        Writes the basket to the repository
        :param basket: dict representing a shopping basket
        :return:
        """

        try:
            buyer_id = basket.get('buyer_id')

            self.redis.set(buyer_id, json.dumps(basket))

            return self.get(buyer_id)
        except Exception as e:
            print(e)


    @rpc
    def delete(self, buyer_id):
        self.redis.delete(buyer_id)


    @rpc
    def checkout(self, basket_checkout, request_id=uuid.uuid4().__str__()):
        #  TODO: add logic to get user name from User's service

        basket_checkout['request_id'] = request_id

        basket = self.redis.get(basket_checkout['buyer_id'])

        if basket is None:
            raise NotFound(f'Basket not found for buyer_id: {basket_checkout["buyer_id"]}.')

        user_name = 'Test User'

        event_message = dict(
            user_id = basket_checkout['buyer_id'],
            user_name=user_name,
            city=basket_checkout['city'],
            state=basket_checkout['state'],
            street_1=basket_checkout['street_1'],
            street_2=basket_checkout['street_2'],
            zip_code=basket_checkout['zip_code'],
            country=basket_checkout['country'],
            card_number=basket_checkout['card_number'],
            cardholder_name=basket_checkout['cardholder_name'],
            expiration=basket_checkout['expiration'],
            security_number=basket_checkout['security_number'],
            card_type_id=basket_checkout['card_type_id'],
            request_id=basket_checkout['request_id'],
            buyer=basket_checkout['buyer'],
            basket=json.loads(basket)
        )

        self.dispatch('user_checkout_accepted', event_message)

        logger.info(f'{dt.utcnow()}: Basket sent to order for buyer_id: {basket_checkout["buyer_id"]}')

    @event_handler(ORDERS_SERVICE, 'order_started')
    def remove_basket_on_order_start(self, payload):
        try:
            if isinstance(payload, str):
                payload = json.loads(payload).data

            self.delete(payload['user_id'])

            logger.info(f'{dt.utcnow()}: Basket removed for user: {payload["user_id"]}')
        except Exception as e:
            logging.error(f'{dt.utcnow()}: Unable to remove basket for user. {e}')

