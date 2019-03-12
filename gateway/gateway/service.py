import json

from nameko.rpc import RpcProxy
from nameko.web.handlers import http
from .schemas import *
from .exceptions import *
from nameko.exceptions import BadRequest
from marshmallow import ValidationError
from werkzeug.wrappers import Request, Response
import logging

logger = logging.getLogger(__name__)


class GatewayService:
    name = 'gateway_service'

    products_rpc = RpcProxy('products_service')
    orders_rpc = RpcProxy('orders_service')
    basket_rpc = RpcProxy('basket_service')

    @http('GET', '/brands')
    def list_brand(self, request):
        return Response(json.dumps(self.products_rpc.list_brand()),
                        mimetype='application/json')

    @http('GET', '/brands/<int:brand_id>')
    def get_brand(self, request, brand_id):
        """ gets brand by id"""
        brand = self.products_rpc.get_brand(brand_id)
        return Response(ProductBrandSchema().dumps(brand).data, mimetype='application/json')

    @http('POST', '/brands',
          expected_exceptions=(ValidationError, BadRequest))
    def create_brand(self, request):
        schema = CreateProductBrandSchema(strict=True)

        try:
            brand_data = schema.loads(request.get_data(as_text=True)).data
        except ValueError as exc:
            raise BadRequest('Invalid JSON: {}'.format(exc))

        # create the product brand
        id_ = self._create_brand(brand_data)
        return json.dumps({'id': id_})

    @http('PUT', '/brands/<int:brand_id>',
          expected_exceptions=(ValidationError, BadRequest))
    def update_brand(self, request, brand_id):
        schema = CreateProductBrandSchema(strict=True)

        try:
            brand_data = schema.loads(request.get_data(as_text=True)).data
        except ValueError as exc:
            raise BadRequest('Invalid JSON: {}'.format(exc))

        payload = { "id": brand_id, 'brand': brand_data}

        result = self.products_rpc.update_brand(payload)

        return Response(ProductBrandSchema().dumps(result).data, mimetype='application/json')

    def _create_brand(self, brand_data):
        serialized_data = CreateProductBrandSchema().dump(brand_data).data
        result = self.products_rpc.create_brand(serialized_data)

        return result['id']

    @http('GET', '/products')
    def list_product(self, request):
        return Response(json.dumps(self.products_rpc.list_product()),
                        mimetype='application/json')

    @http('GET', '/products/<int:product_id>')
    def get_product(self, request, product_id):
        product = self.products_rpc.get_product(product_id)
        return Response(ProductSchema().dumps(product).data,
                        mimetype='application/json')

    @http('POST', '/products')
    def create_product(self, request):
        schema = CreateProductSchema(strict=True)

        try:
            product_data = schema.loads(request.get_data(as_text=True)).data
        except ValueError as exc:
            raise BadRequest('Invalid Json: {}'.format(exc))

        id_ = self._create_product(product_data)
        return Response(json.dumps({'id': id_}))

    @http('PUT', '/products/<int:product_id>')
    def update_product(self, request, product_id):
        schema = CreateProductSchema(strict=True)

        try:
            product_data = schema.loads(request.get_data(as_text=True)).data
        except ValueError as exc:
            raise BadRequest('Invalid JSON: {}'.format(exc))

        payload = { "id": product_id, 'product': product_data}

        payload = UpdateProductSchema().dump(payload).data
        result = self.products_rpc.update_product(payload)

        return Response(ProductSchema().dumps(result).data,
                        mimetype='application/json')

    def _create_product(self, product_data):
        serialized_data = CreateProductSchema().dump(product_data).data
        result = self.products_rpc.create_product(serialized_data)

        return result['id']

    @http('GET', '/orders')
    def list_orders(self, request):
        return Response(json.dumps(self.orders_rpc.list_order()),
                        mimetype='application/json')

    @http('GET', '/orders/<int:order_id>')
    def get_order(self, request, order_id):
        order = self.orders_rpc.get_order(order_id)
        return Response(OrderSchema().dumps(order).data,
                        mimetype='application/json')

    @http('POST', '/orders')
    def create_order(self, request):
        schema = CreateOrderSchema(strict=True)

        try:
            # load input through schema for validation
            # this will return a ValueError or ValidationError
            order_data = schema.loads(request.get_data(as_text=True)).data
        except ValueError as exc:
            raise BadRequest("Invalid JSON: {}".format(exc))

        # create the order (this could raise a product not found)
        id_ = self._create_order(order_data)

        return json.dumps({'id': id_})

    def _create_order(self, order_data):
        # gotta parse through and check for products first
        valid_product_ids = {prod['id'] for prod in self.products_rpc.list_product()}
        for item in order_data['order_items']:
            if item['product_id'] not in valid_product_ids:
                raise ProductNotFound("Product Id {}".format(item['product_id']))

        # call the order service to create the order
        # dump the data through the schema to ensure values are set correctly
        data = CreateOrderSchema().dump(order_data).data
        result = self.orders_rpc.create_order(data)

        return result['id']

    @http('PUT', '/orders/<int:order_id>')
    def update_order(self, request, order_id):
        pass


    @http('GET', '/baskets/<string:buyer_id>')
    def get_basket(self, request, buyer_id):
        basket = self.basket_rpc.get(buyer_id)
        return json.dumps(basket)


    @http('POST', '/baskets')
    def create_basket(self, request):
        payload = BasketSchema().loads(request.get_data(as_text=True)).data
        basket = self.basket_rpc.update(payload)

        return Response(json.dumps(basket))

    @http('DELETE', '/baskets/<string:buyer_id>')
    def delete_basket(self, request, buyer_id):
        self.basket_rpc.delete(buyer_id)
        return json.dumps({"msg":"deleted"})

    @http('POST', '/checkout')
    def checkout(self, request):
        pass
