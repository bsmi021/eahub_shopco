import datetime
from random import randint

from nameko.events import EventDispatcher, event_handler
from nameko.rpc import rpc
from nameko.timer import timer
from nameko_sqlalchemy import DatabaseSession

from .exceptions import NotFound
from .models import *
from .schemas import *

import mongoengine

import logging

logger = logging.getLogger(__name__)


class CommandBrands:
    name = 'command_brands'
    dispatch = EventDispatcher()
    db = DatabaseSession(DeclarativeBase)

    def fire_replicate_db_event(self, data):
        """ fires off a replication event,
        this expose the event-sourcing pattern which will send the
        record to the query database from the command database """
        self.dispatch('replicate_db_event', data)

    @rpc
    def add(self, brand):
        name = brand.get('name')

        item = ProductBrand()
        item.name = name

        self.db.add(item)
        self.db.commit()

        data = ProductBrandSchema().dump(item).data

        self.fire_replicate_db_event(data)

        return data

    @rpc
    def update(self, id, payload):
        u_product_brand = self.db.query(ProductBrand).get(id)

        if u_product_brand is None:
            raise NotFound()

        u_product_brand.name = payload.get('name')
        u_product_brand.updated_at = datetime.datetime.utcnow()

        self.db.commit()

        data = ProductBrandSchema().dump(u_product_brand).data

        self.fire_replicate_db_event(data)

        return data

    @rpc
    def delete(self, id):
        product_brand = self.db.query(ProductBrand).get(id)
        self.db.delete(product_brand)
        self.db.commit()


class QueryBrands:
    name = 'query_brands'  # this is the service name

    @event_handler('command_brands', 'replicate_db_event')
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
    name = 'command_products'
    dispatch = EventDispatcher()
    db = DatabaseSession(DeclarativeBase)

    def fire_replicate_db_event(self, data):
        self.dispatch('replicate_db_event', data)

    @rpc
    def add(self, data):

        try:
            brand = self.db.query(ProductBrand) \
                .get(data['product_brand_id'])

            if brand is None:
                raise NotFound()

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
            product.weight = data.get('weight', 0)
            product.width = data.get('width', 0)
            product.height = data.get('height', 0)
            product.depth = data.get('depth', 0)

            self.db.add(product)
            self.db.commit()

            data['id'] = product.id
            data['created_at'] = product.created_at
            data['updated_at'] = product.updated_at

            self.fire_replicate_db_event(data)

            return data
        except Exception as e:
            self.db.rollback()
            return e

    @rpc
    def update_product(self, payload):
        u_product = self.db.query(Product).get(payload['id'])

        if u_product is None:
            raise NotFound()

        product = payload['product']

        u_product.name = product['name']
        u_product.description = product['description']
        u_product.price = product['price']
        u_product.available_stock = product['available_stock']
        u_product.restock_threshold = product['restock_threshold']
        u_product.max_stock_threshold = product['max_stock_threshold']

        u_product.updated_at = datetime.datetime.utcnow()

        self.db.commit()

        data = ProductSchema().dump(u_product).data

        self.fire_replicate_db_event(data)

        return data

    @rpc
    def delete_product(self, id):
        product = self.db.query(Product).get(id)
        self.db.delete(product)
        self.db.commit()

    @event_handler('orders_service', 'order_paid')
    def handle_order_status_changed_paid(self, payload):
        """
        This will remove items from stock for items from an order.


        :param payload:
        :return:
        """
        schema = OrderStatusChangedToPaidEvent()

        payload: OrderStatusChangedToPaidEvent = schema.loads(payload).data

        products = payload['order_stock_items']

        for p in products:
            product = self.db.query(Product).get(p['product_id'])
            product.remove_stock(p['units'])

            data = ProductSchema().dumps(product).data
            self.fire_replicate_db_event(data)

        self.db.commit()

    @event_handler('orders_service', 'order_await_valid')
    def handle_order_status_awaiting_validation(self, payload):
        schema = OrderStatusChangedToAwaitingValidationEvent()

        payload = schema.loads(payload).data

        confirmed_order_stock_items = []

        for i in payload['order_stock_items']:
            product = self.db.query(Product).get(i['product_id'])
            has_stock = product.available_stock >= i['units']
            confirmed_order_stock_items.append({'product_id': product.id, 'has_stock': has_stock})

        rejected = all(item['has_stock'] for item in confirmed_order_stock_items)

        if not rejected:
            i_payload = {'order_id': payload['order_id'],
                         'order_stock_items': confirmed_order_stock_items}
            self.event_dispatcher('rejected_order_stock', i_payload)
        else:
            self.event_dispatcher('confirmed_order_stock', {'order_id': payload['order_id']})

    @timer(interval=90)
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

            data = ProductSchema().dumps(product).data

            self.fire_replicate_db_event(data)

        self.db.commit()


class QueryProducts:
    name = 'query_products'

    @event_handler('command_products', 'replicate_db_event')
    def normalize_db(self, data):
        try:
            product = QueryProductsModel.objects.get(id=data['id'])
            product.update(
                name=data.get('name', product.name),
                description=data.get('description', product.description),
                price=data.get('price', product.price),
                available_stock=data.get('available_stock', product.available_stock),
                max_stock_threshold=data.get('max_stock_threshold', product.max_stock_threshold),
                on_reorder=data.get('on_reorder', product.on_reorder),
                reorder_threshold=data.get('restock_threshold', product.restock_threshold),
                product_brand_id=data.get('product_brand_id', product.product_brand_id),
                updated_at=data.get('updated_at', product.updated_at),
                sku=str(data.get('sku', product.sku))
            )
            product.reload()
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
                    weight=data.get('weight', 0),
                    width=data.get('width', 0),
                    height=data.get('height', 0),
                    depth=data.get('depth', 0)
                )
            ).save()
        except Exception as e:
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
