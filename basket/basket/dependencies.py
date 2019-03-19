from nameko.extensions import DependencyProvider
from nameko_redis import Redis
import redis
from .exceptions import NotFound
import json
import pickle

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

        return basket

    def update(self, basket):
        """
        Creates/Updates a basket in the repository
        :param basket:
        :return:
        """
        obj = json.loads(basket)

        created = self.client.set(obj.get('buyer_id'), basket)

        if not created:
            return None

        return self.get(obj.get('buyer_id'))

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