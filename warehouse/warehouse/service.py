# /warehouse/warehouse/service.py

import json
import logging

from nameko.events import event_handler, EventDispatcher
from nameko.rpc import rpc
from nameko.web.handlers import http
from nameko_sqlalchemy import DatabaseSession
from sqlalchemy import Sequence, func, join
from datetime import datetime as dt

from .models import *
from .exceptions import *

from mongoengine import DoesNotExist, QuerySet
from mongoengine.queryset.visitor import Q

import logging
from py_linq import Enumerable

logger = logging.getLogger(__name__)

REPLICATE_EVENT = 'replicate_db_event'
SITE_COMMAND = 'command_site'
SITE_QUERY = 'query_site'
ITEM_COMMAND = 'command_item'
ITEM_QUERY = 'query_inventory'

PRODUCTS_COMMAND = 'command_products'
ORDER_COMMAND = 'command_orders'
ORDER_STATUS_CHANGED_TO_PAID = 'order_status_changed_to_paid'
ORDER_STATUS_CHANGED_TO_AWAITING_VERIFICATION = 'order_status_changed_to_awaiting_validation'


class CommandSite:
    name = SITE_COMMAND
    dispatch = EventDispatcher()
    db = DatabaseSession(DeclarativeBase)

    def _save_to_db(self, item):
        self.db.add(item)
        self.db.commit()

    @rpc
    def add(self, payload):

        if isinstance(payload, str):
            payload = json.loads(payload)

        name = payload.get('name')
        zip_code = payload.get('zip_code')
        type_id = payload.get('type_id')

        site = Site(name=name, zip_code=zip_code, type_id=type_id)

        self._save_to_db(site)

        payload['id'] = site.id
        payload['created_at'] = site.created_at
        payload['updated_at'] = site.updated_at

        self.dispatch(REPLICATE_EVENT, payload)

        return payload

    @rpc
    def update(self, id, payload):

        if isinstance(payload, str):
            payload = json.loads(payload)

        site = self.db.query(Site).get(id)

        if site is None:
            raise NotFound()

        site.name = payload.get('name', site.name)
        site.zip_code = payload.get('zip_code', site.zip_code)
        site.type_id = payload.get('type_id', site.type_id)
        site.updated_at = datetime.datetime.utcnow()

        self._save_to_db(site)

        payload['id'] = site.id
        payload['updated_at'] = site.updated_at

        self.dispatch(REPLICATE_EVENT, payload)


class QuerySite:
    name = SITE_QUERY

    @event_handler(SITE_COMMAND, REPLICATE_EVENT)
    def normalize_db(self, data):

        if isinstance(data, str):
            data = json.loads(data)

        site_type = SiteTypes[data['type_id']]

        try:
            site = SiteQueryModel.objects.get(id=data['id'])
            site.update(
                name=data.get('name', site.name),
                zip_code=data.get('zip_code', site.zip_code),
                type_id=data.get('type_id', site.type_id),
                type=data.get('type', site_type),
                updated_at=data.get('updated_at', site.updated_at)
            )
            site.reload()
            logger.info(f'{datetime.datetime.utcnow()}: Replicated site update')
        except DoesNotExist:
            logger.info(f'{datetime.datetime.utcnow()}: Creating new site now')

            try:
                SiteQueryModel(
                    id=data['id'],
                    name=data['name'],
                    zip_code=data['zip_code'],
                    type_id=data['type_id'],
                    type=site_type,
                    created_at=data['created_at'],
                    updated_at=data['updated_at']
                ).save()

                logger.info(f'{datetime.datetime.utcnow()}: Replicated site creation')
            except Exception as e:
                logger.error(f'{datetime.datetime.utcnow()}: There was an error in replication: {e}')
        except Exception as e:
            logger.error(f'{datetime.datetime.utcnow()}: There was an error in replication: {e}')
            return e

    @rpc
    def list(self, num_page, limit):
        try:
            if not num_page:
                num_page = 1
            offset = (num_page - 1) * limit
            sites = SiteQueryModel.objects  # .skip(offset).limit(limit)
            return sites.to_json()
        except Exception as e:
            return e

    @rpc
    def get(self, id):
        try:
            site = SiteQueryModel.objects.get(id=id)
            return site.to_json()
        except DoesNotExist as e:
            return e
        except Exception as e:
            return e


class CommandInventoryItem:
    name = ITEM_COMMAND

    db = DatabaseSession(DeclarativeBase)
    dispatch = EventDispatcher()

    @event_handler(PRODUCTS_COMMAND, 'product_added')
    def add_inventory_item(self, data):
        """ This is a demo app, so there are some liberties being taken here:
            1. The product being added will be added to a random count of sites' inventory
            2. Initial stock numbers are going to be generated randomly
            3. All sites are able to inventory an item (this may change)
        """
        if isinstance(data, str):
            data = json.loads(data)

        # get the sites
        sites = self.db.query(Site).all()
        items = []
        for site in random.sample(sites, random.randint(1, len(sites))):
            item = InventoryItem(product_id=data['product_id'], site_id=site.id)

            version = 1
            if data.get('version'):
                version = (data.get('version') + 1)
            if data.get('id'):
                id = data.get('id')
            else:
                id = self.db.execute(Sequence('inventory_items_id_seq'))

            item.id = id
            item.version = version

            self.db.add(item)
            self.db.commit()

            items.append(item)

        for item_data in [{'id': i.id,
                           'product_id': i.product_id,
                           'site_id': i.site_id,
                           'available_stock': i.available_stock,
                           'restock_threshold': i.restock_threshold,
                           'version': i.version,
                           'max_stock_threshold': i.max_stock_threshold,
                           'on_reorder': i.on_reorder,
                           'created_at': i.created_at,
                           'committed_stock': i.committed_stock,
                           'updated_at': i.updated_at} for i in items]:
            self.dispatch(REPLICATE_EVENT, item_data)

    @event_handler(None, 'add_item_stock')
    def add_item_stock(self, data):
        if isinstance(data, str):
            data = json.loads(data)

    @event_handler(ORDER_COMMAND, ORDER_STATUS_CHANGED_TO_PAID)
    def remove_stock_on_order_paid(self, data):
        if isinstance(data, str):
            data = json.loads(data)

        items = data['order_stock_items']

    @event_handler(ORDER_COMMAND, ORDER_STATUS_CHANGED_TO_AWAITING_VERIFICATION)
    def verify_order_item_availability(self, data):
        """
        This method will verify stock across all sites, it will not reject an order
        just because one site does not have the inventory to meet the order's needs,
        shipping fulfillment will cover the multiple warehouses shipping
        :param data:
        :return:
        """

        if isinstance(data, str):
            data = json.loads(data)

        confirmed_order_stock_items = []

        for i in data['order_stock_items']:
            subqry = self.db.query(InventoryItem.site_id,
                                   func.max(InventoryItem.version).label('maxversion')) \
                .filter(InventoryItem.product_id == i['product_id']) \
                .group_by(InventoryItem.site_id).subquery('t2')

            inventory_items = self.db.query(InventoryItem) \
                .filter(InventoryItem.product_id == i['product_id']) \
                .join(subqry,
                      (InventoryItem.site_id == subqry.c.site_id) &
                      (InventoryItem.version == subqry.c.maxversion)) \
                .all()

            inventory_items = Enumerable(inventory_items)
            inventory_count = inventory_items.sum(lambda x: x.available_stock)

            has_stock = inventory_count >= i['units']
            confirmed_order_stock_items.append({'product_id': i['product_id'],
                                                'has_stock': has_stock})

        rejected = all(item['has_stock'] for item in confirmed_order_stock_items)

        if not rejected:
            payload = {'order_id': data['order_id'],
                       'order_stock_items': confirmed_order_stock_items}
            self.dispatch('rejected_order_stock', payload)
        else:
            self.dispatch('confirmed_order_stock', {'order_id': data['order_id']})


class QueryInventoryItems:
    name = ITEM_QUERY

    @event_handler(ITEM_COMMAND, REPLICATE_EVENT)
    def normalize_db(self, data):
        if isinstance(data, str):
            data = json.loads(data)

        try:
            item = InventoryItemQueryModel.objects.get(id=data['id'])

            item.update(
                version=data['version'],
                product_id=data['product_id'],
                site_id=data['site_id'],
                available_stock=data['available_stock'],
                max_stock_threshold=data['max_stock_threshold'],
                restock_threshold=data['restock_threshold'],
                committed_stock=data['committed_stock'],
                on_reorder=data['on_reorder'],
                updated_at=data['updated_at']
            )

            item.reload()
            logger.info(f'{dt.utcnow()}: Inventory Item {data["id"]} updated to Version {data["version"]} in queryDB')
        except DoesNotExist:  # mongoengine.DoesNotExist
            logger.info(
                f'{dt.utcnow()}: Inventory Item {data["id"]} did not exist for site {data["site_id"]}, creating now.')
            InventoryItemQueryModel(
                id=data['id'],
                version=data['version'],
                product_id=data['product_id'],
                site_id=data['site_id'],
                available_stock=data['available_stock'],
                max_stock_threshold=data['max_stock_threshold'],
                restock_threshold=data['restock_threshold'],
                committed_stock=data['committed_stock'],
                on_reorder=data['on_reorder'],
                created_at=data['created_at'],
                updated_at=data['updated_at']
            ).save()
            logger.info(f'{dt.utcnow()}: Inventory Item {data["id"]} added to queryDB for site {data["site_id"]}.')
        except Exception as e:
            logger.info(f'{dt.utcnow()}: There was a problem replicating to the Query DB: {e}')
            return e

    @rpc
    def get_by_product_id(self, product_id):
        items = InventoryItemQueryModel.objects(product_id=product_id)
        return items.to_json()

    @rpc
    def get_by_site_id(self, site_id, num_page=1, limit=10):
        if not num_page:
            num_page = 1
        offset = (num_page - 1) * limit

        items = (InventoryItemQueryModel.objects(site_id=site_id)
                 .skip(offset)
                 .limit(limit))
        return items.to_json()


class InventoryApi:
    name = 'inventory_api'

    @http('GET', '/inventory/<int:product_id>')
    def get_inventory_items_by_product_id(self, request, product_id):
        """
        Gets all of the inventory items for a product
        :param product_id:
        :return:
        """

        try:

            items = InventoryItemQueryModel.objects(product_id=product_id)

            return items.to_json()

        except Exception as ex:
            error_response(500, ex)


def error_response(code, ex):
    response_object = {
        'status': 'fail',
        'message': str(ex),
    }
    return code, {'Content-Type': 'application/json'}, json.dumps(response_object)
