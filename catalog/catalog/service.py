import datetime
from random import randint

from nameko.events import EventDispatcher, event_handler
from nameko.rpc import rpc
from nameko.timer import timer
from nameko_sqlalchemy import DatabaseSession

from .exceptions import NotFound
from .models import DeclarativeBase, ProductBrand, Product, QueryProductsModel, QueryBrandModel
from .schemas import *

import mongoengine


class CommandBrands:
    name = 'command_brands'
    dispatch = EventDispatcher()
    db = DatabaseSession(DeclarativeBase)

    def fire_replicate_db_event(self, data):
        self.dispatch('replicate_db_event', data)

    @rpc
    def add(self, brand):
        name = brand['name']

        item = ProductBrand()
        item.name = name

        self.db.add(item)
        self.db.commit()

        data = ProductBrandSchema().dump(item).data

        self.fire_replicate_db_event(data)

        return data

    @rpc
    def update_brand(self, payload):
        u_product_brand = self.db.query(ProductBrand).get(payload['id'])

        if u_product_brand is None:
            raise NotFound()

        brand = payload['brand']

        u_product_brand.name = brand['name']
        u_product_brand.updated_at = datetime.datetime.utcnow()

        self.db.commit()

        data = ProductBrandSchema().dump(u_product_brand).data

        self.fire_replicate_db_event(data)

        return data

    @rpc
    def delete_brand(self, id):
        product_brand = self.db.query(ProductBrand).get(id)
        self.db.delete(product_brand)
        self.db.commit()


class CommandProducts:
    name = 'command_products'
    dispatch = EventDispatcher()
    db = DatabaseSession(DeclarativeBase)

    def fire_replicate_db_event(self, data):
        self.dispatch('replicate_db_event', data)

    @rpc
    def add(self, product):
        brand = self.db.query(ProductBrand) \
            .get(product['product_brand_id'])

        if brand is None:
            raise NotFound()

        i_product = Product()

        i_product.product_brand = brand
        i_product.name = product['name']
        i_product.description = product['description']
        i_product.price = product['price']
        i_product.available_stock = product['available_stock']
        i_product.restock_threshold = product['restock_threshold']
        i_product.max_stock_threshold = product['max_stock_threshold']

        self.db.add(i_product)
        self.db.commit()

        data = ProductSchema().dump(i_product).data

        self.fire_replicate_db_event(data)

        return data

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

        payload: OrderStatusChangedToPaidEvent = schema.loads(payload).data

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


class QueryBrands:
    name = 'query_brands'

    @event_handler('command_brands', 'replicate_db_event')
    def normalize_db(self, data):
        try:
            brand = QueryBrandModel.objects.get(id=data['id'])
            brand.update(
                name=data['name']
            )
            brand.reload()
        except mongoengine.DoesNotExist:
            QueryBrandModel(id=data['id'], name=data['name']).save()
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
            brands = QueryBrandModel.objects.skip(offset).limit(limit)
            return brands.to_json()
        except Exception as e:
            return e


class QueryProducts:
    name = 'query_products'

    @event_handler('command_products', 'replicate_db_event')
    def normalize_db(self, data):
        try:
            product = QueryProductsModel.objects.get(id=data['id'])
            product.update(
                name=data['name'],
                description=data['description'],
                price=data['price'],
                available_stock=data['available_stock'],
                max_stock_threshold=data['max_stock_threshold'],
                on_reorder=data['on_reorder'],
                reorder_threshold=data['reorder_threshold']
            )
            product.reload()
        except mongoengine.DoesNotExist:
            QueryBrandModel(
                id=data['id'],
                name=data['name'],
                description=data['description'],
                price=data['price'],
                available_stock=data['available_stock'],
                max_stock_threshold=data['max_stock_threshold'],
                on_reorder=data['on_reorder'],
                reorder_threshold=data['reorder_threshold']
            ).save()
        except Exception as e:
            return e