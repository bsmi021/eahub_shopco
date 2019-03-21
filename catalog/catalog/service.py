import datetime
from random import randint

from nameko.events import EventDispatcher, event_handler
from nameko.rpc import rpc
from nameko.timer import timer
from nameko_sqlalchemy import DatabaseSession
from sqlalchemy import Sequence
from .exceptions import NotFound
from .models import *

import json

import mongoengine

import logging

logger = logging.getLogger(__name__)

REPLICATE_EVENT = 'replicate_db_event'
ORDERS_SERVICE = 'command_orders'
BRANDS_COMMAND_SERVICE = 'command_brands'
BRANDS_QUERY_SERVICE = 'query_brands'
PRODUCTS_COMMAND_SERVICE = 'command_products'
PRODUCTS_QUERY_SERVICE = 'query_products'


class CommandBrands:
    name = BRANDS_COMMAND_SERVICE
    dispatch = EventDispatcher()
    db = DatabaseSession(DeclarativeBase)

    def fire_replicate_db_event(self, data):
        """ fires off a replication event,
        this expose the event-sourcing pattern which will send the
        record to the query database from the command database """
        self.dispatch(REPLICATE_EVENT, data)

    @rpc
    def add(self, payload):

        if isinstance(payload, str):
            payload = json.loads(payload)

        name = payload.get('name')

        item = ProductBrand()
        item.name = name

        self.db.add(item)
        self.db.commit()

        payload['id'] = item.id
        payload['updated_at'] = item.updated_at
        payload['created_at'] = item.created_at

        self.fire_replicate_db_event(payload)

        return payload

    @rpc
    def update(self, id, payload):
        brand = self.db.query(ProductBrand).get(id)

        if brand is None:
            raise NotFound()

        brand.name = payload.get('name')
        brand.updated_at = datetime.datetime.utcnow()

        self.db.add(brand)
        self.db.commit()

        payload['id'] = brand.id
        payload['created_at'] = brand.created_at
        payload['updated_at'] = brand.updated_at

        self.fire_replicate_db_event(payload)

        return payload

    @rpc
    def delete(self, id):
        product_brand = self.db.query(ProductBrand).get(id)
        self.db.delete(product_brand)
        self.db.commit()


class QueryBrands:
    name = BRANDS_QUERY_SERVICE  # this is the service name

    @event_handler(BRANDS_COMMAND_SERVICE, REPLICATE_EVENT)
    def normalize_db(self, data):
        try:
            brand = QueryBrandModel.objects.get(
                id=data['id']
            )
            brand.update(
                name=data.get('name', brand.name),
                updated_at=data.get('updated_at', brand.updated_at)
            )
            brand.reload()
        except mongoengine.DoesNotExist:
            QueryBrandModel(
                id=data['id'],
                name=data['name'],
                created_at=data['created_at'],
                updated_at=data['updated_at']
            ).save()
        except Exception as e:
            return e

    @rpc
    def get(self, id):
        try:
            brand = QueryBrandModel.objects.get(id=id)
            return brand.to_json()
        except mongoengine.DoesNotExist as e:
            return e
        except Exception as e:
            return e

    @rpc
    def list(self, num_page, limit):
        try:
            if not num_page:
                num_page = 1
            offset = (num_page - 1) * limit
            brands = QueryBrandModel.objects  # .skip(offset).limit(limit)
            return brands.to_json()
        except Exception as e:
            return e


class CommandProducts:
    name = PRODUCTS_COMMAND_SERVICE
    dispatch = EventDispatcher()
    db = DatabaseSession(DeclarativeBase)

    def fire_replicate_db_event(self, data):
        self.dispatch(REPLICATE_EVENT, data)

    @rpc
    def add_product(self, data):

        try:

            if isinstance(data, str):
                data = json.loads(data)

            brand = self.db.query(ProductBrand) \
                .get(data['product_brand_id'])

            if brand is None:
                raise NotFound('Brand not found, cannot add product.')

            product = Product()

            product.sku = data['sku']
            product.product_brand = brand
            product.name = data['name']
            product.description = data['description']
            product.price = data['price']
            product.available_stock = data['available_stock']
            product.restock_threshold = data['restock_threshold']
            product.max_stock_threshold = data['max_stock_threshold']
            product.on_reorder = data.get('on_reorder', False)
            if data.get('shipping_details') is not None:
                product.weight = data['shipping_details'].get('weight', 0)
                product.width = data['shipping_details']['width']
                product.height = data['shipping_details']['height']
                product.depth = data['shipping_details']['depth']

            self.db.add(product)
            self.db.commit()

            data['id'] = product.id
            data['created_at'] = product.created_at
            data['updated_at'] = product.updated_at

            self.fire_replicate_db_event(data)

            return data
        except Exception as e:
            self.db.rollback()
            logger.error(f'{datetime.datetime.utcnow()}: There was an error saving this product: {e}')
            return e

    @rpc
    def update_product(self, payload):

        if isinstance(payload, str):
            payload = json.loads(payload)

        product = self.db.query(Product).get(payload['id'])

        if product is None:
            raise NotFound()

        # product = payload['product']

        product.name = payload['name']
        product.description = payload['description']
        product.price = payload['price']
        product.available_stock = payload['available_stock']
        product.restock_threshold = payload['restock_threshold']
        product.max_stock_threshold = payload['max_stock_threshold']
        product.updated_at = datetime.datetime.utcnow()

        if payload.get('shipping_details') is not None:
            product.weight = payload['shipping_details'].get('weight', product.weight)
            product.width = payload['shipping_details'].get('width', product.width)
            product.height = payload['shipping_details'].get('height', product.height)
            product.depth = payload['shipping_details'].get('depth', product.depth)

        self.db.commit()

        payload['updated_at'] = product.updated_at

        # d#ata = ProductSchema().dump(product).data

        self.fire_replicate_db_event(payload)

        return payload

    @rpc
    def delete_product(self, id):
        product = self.db.query(Product).get(id)
        self.db.delete(product)
        self.db.commit()

    @event_handler(ORDERS_SERVICE, 'order_status_changed_to_paid')
    def handle_order_status_changed_paid(self, payload):
        """
        This will remove items from stock for items from an order.
        :param payload:
        :return:
        """
        if isinstance(payload, str):
            payload = json.loads(payload)

        products = payload['order_stock_items']

        for p in products:
            product = self.db.query(Product).get(p['product_id'])
            product.remove_stock(p['units'])

            self.db.commit()

            data = {
                'id': product.id,
                'available_stock': product.available_stock,
                'on_reorder': product.on_reorder,
                'updated_at': product.updated_at
            }

            self.fire_replicate_db_event(data)

            logger.info(f'{datetime.datetime.utcnow()}: \
                {p["units"]} units removed for product_id: {product.id}: there are {product.available_stock} \
                units remaining')

    @event_handler(ORDERS_SERVICE, 'order_status_changed_to_awaiting_validation')
    def verify_stock_for_order(self, payload):
        """
        With the provided order payload, inspect each requested product to
        ensure there is enough stock to satisfy the order
        :param payload:
        :return:
        """
        if isinstance(payload, str):
            payload = json.loads(payload)

        confirmed_order_stock_items = []

        for i in payload['order_stock_items']:
            product = self.db.query(Product).get(i['product_id'])
            has_stock = product.available_stock >= i['units']
            confirmed_order_stock_items.append({'product_id': product.id, 'has_stock': has_stock})

        rejected = all(item['has_stock'] for item in confirmed_order_stock_items)

        if not rejected:
            i_payload = {'order_id': payload['order_id'],
                         'order_stock_items': confirmed_order_stock_items}
            self.dispatch('rejected_order_stock', i_payload)
        else:
            self.dispatch('confirmed_order_stock', {'order_id': payload['order_id']})

    @timer(interval=os.getenv('RESTOCK_INTERVAL', 90))
    def reorder_products(self):
        """
        Gets all products which are low on stock and reorders a
        random amount to get them over the min_stock_threshold
        :return:
        """

        products = self.db.query(Product) \
            .filter(Product.restock_threshold >
                    Product.available_stock).all()

        for product in products:
            x = product.max_stock_threshold - product.restock_threshold
            product.add_stock(randint(product.restock_threshold, x))
            product.on_reorder = False
            product.updated_at = datetime.datetime.utcnow()

            self.db.commit()

            data = {
                'id': product.id,
                'available_stock': product.available_stock,
                'on_reorder': product.on_reorder,
                'updated_at': product.updated_at
            }

            self.fire_replicate_db_event(data)


class QueryProducts:
    name = PRODUCTS_QUERY_SERVICE

    @event_handler(PRODUCTS_COMMAND_SERVICE, REPLICATE_EVENT)
    def normalize_db(self, data):
        try:
            product = QueryProductsModel.objects.get(id=data['id'])
            if data.get('shipping_details') is not None:
                shipping_details = ShippingDetailsModel(
                    weight=data.get('shipping_details').get('weight', product.shipping_details.weight),
                    width=data.get('shipping_details').get('width', product.shipping_details.width),
                    height=data.get('shipping_details').get('height', product.shipping_details.height),
                    depth=data.get('shipping_details').get('depth', product.shipping_details.depth)
                )
            else:
                shipping_details = product.shipping_details

            product.update(
                name=data.get('name', product.name),
                description=data.get('description', product.description),
                price=data.get('price', product.price),
                available_stock=data.get('available_stock', product.available_stock),
                max_stock_threshold=data.get('max_stock_threshold', product.max_stock_threshold),
                on_reorder=data.get('on_reorder', product.on_reorder),
                restock_threshold=data.get('restock_threshold', product.restock_threshold),
                product_brand_id=data.get('product_brand_id', product.product_brand_id),
                updated_at=data.get('updated_at', product.updated_at),
                sku=str(data.get('sku', product.sku)),
                shipping_details=shipping_details
            )
            product.reload()
            logger.info('Product Updated')
        except mongoengine.DoesNotExist:
            logger.info('Creating a new product in Query DB')

            QueryProductsModel(
                id=data['id'],
                name=data['name'],
                description=data['description'],
                price=data['price'],
                available_stock=data['available_stock'],
                max_stock_threshold=data['max_stock_threshold'],
                on_reorder=data.get('on_reorder', False),
                restock_threshold=data['restock_threshold'],
                product_brand_id=data['product_brand_id'],
                created_at=data['created_at'],
                updated_at=data['updated_at'],
                sku=str(data['sku']),
                shipping_details=ShippingDetailsModel(
                    weight=data.get('shipping_details').get('weight', 0),
                    width=data.get('shipping_details').get('width', 0),
                    height=data.get('shipping_details').get('height', 0),
                    depth=data.get('shipping_details').get('depth', 0)
                )
            ).save()
            logger.info('Product Added')
        except Exception as e:
            logger.info(f'There was an error updating products in the QueryDB: {e}')
            return e

    @rpc
    def list(self, num_page, limit):
        """ returns all the products requested"""
        try:
            if not num_page:
                num_page = 1
            offset = (num_page - 1) * limit
            products = QueryProductsModel.objects  # .skip(offset).limit(limit)
            return products.to_json()
        except Exception as e:
            return e

    @rpc
    def get(self, id):
        """ returns a product based on the provided ID"""
        try:
            product = QueryProductsModel.objects.get(id=id)
            return product.to_json()
        except mongoengine.DoesNotExist as e:
            return e
        except Exception as e:
            return e
