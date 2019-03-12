import logging
from nameko.events import event_handler, EventDispatcher
from nameko.rpc import rpc

from . import schemas, dependencies

logger = logging.getLogger(__name__)


class BasketService:
    name = 'basket_service'
    storage = dependencies.Storage()

    @rpc
    def get(self, buyer_id):
        basket = self.storage.get(buyer_id)
        return schemas.Basket().dump(basket).data

    @rpc
    def update(self, basket):
        return self.storage.update(basket)

    @rpc
    def delete(self, buyer_id):
        self.storage.delete(buyer_id)
