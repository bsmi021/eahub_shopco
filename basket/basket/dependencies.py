from nameko.extensions import DependencyProvider
import redis
from .exceptions import NotFound
import json
from .schemas import *

REDIS_URI_KEY = 'REDIS_URI'


class StorageWrapper:

    def __init__(self, client):
        self.client: redis.StrictRedis = client


    def _format_key(self, customer_id):
        return 'baskets:{}'.format(customer_id)

    def _from_hash(self, document):
        return {
            ''
        }

    def get(self, customer_id):
        basket = self.client.get(customer_id)
        if not basket:
            return NotFound('Basket for {} not found'.format(customer_id))
        else:
            return json.loads(basket)

    def update(self, basket):

        created = self.client.set(basket['buyer_id'], json.dumps(basket))

        if not created:
            return None

        return self.get(basket['buyer_id'])

    def delete(self, id):
        return self.client.delete(id)


class Storage(DependencyProvider):
    client = None

    def setup(self):
        self.client = redis.StrictRedis.from_url(
            self.container.config.get(REDIS_URI_KEY)
        )

    def get_dependency(self, worker_ctx):
        return StorageWrapper(self.client)