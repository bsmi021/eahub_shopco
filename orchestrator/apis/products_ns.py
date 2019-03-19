# ./orchestrator/orchestrator/api/catalog/products_ns.py
import logging
import os
from flask import request, jsonify, Response
from flask_restplus import Resource, Namespace, fields
from nameko.standalone.rpc import ClusterRpcProxy
import json

logger = logging.getLogger(__name__)

api = Namespace('products')

RABBIT_USER = os.getenv('RABBIT_USER', 'guest')
RABBIT_PASSWORD = os.getenv('RABBIT_PASSWORD', 'guest')
RABBIT_HOST = os.getenv('RABBIT_HOST', '127.0.0.1')
RABBIT_PORT = os.getenv('RABBIT_PORT', '5672')

amqp_uri = 'amqp://{}:{}@{}:{}'.format(RABBIT_USER, RABBIT_PASSWORD, RABBIT_HOST, RABBIT_PORT)

CONFIG_RPC = {'AMQP_URI': amqp_uri}

shipping_details = api.model('Shipping Details',
                             dict(
                                 weight=fields.Float(),
                                 height=fields.Float(),
                                 width=fields.Float(),
                                 depth=fields.Float()
                             ))

product = api.model('Product',
                    dict(
                        _id=fields.Integer(readOnly=True, description='Item unique ID'),
                        name=fields.String(required=True, description='Item Name'),
                        description=fields.String(max_length=250, description='Item Description'),
                        price=fields.Float(description='Item Price'),
                        product_brand_id=fields.Integer(required=True),
                        product_brand=fields.String(readOnly=True, attribute='catalog_brand.brand'),
                        available_stock=fields.Integer(description='Quantity in stock'),
                        restock_threshold=fields.Integer(description='Available stock at which reorder is needed'),
                        max_stock_threshold=fields.Integer(description='Max units of item that can be inventoried'),
                        sku=fields.String(required=True, description='Product stock keeping unit'),
                        on_reorder=fields.Boolean(description='True if item is on reorder'),
                        created_at=fields.DateTime(readOnly=True, description='Date record was created'),
                        updated_at=fields.DateTime(readOnly=True, description='Date last modified'),
                        shipping_details=fields.Nested(shipping_details, required=False)
                    ))


@api.route('')
class ProductsCollection(Resource):
    #@api.marshal_with(product, code=200, description='Success', as_list=True)
    def get(self, num_page=5, limit=5):
        """ returns a list of products """
        with ClusterRpcProxy(CONFIG_RPC) as rpc:
            response_data = rpc.query_products.list(num_page, limit)
            return Response(response=response_data,
                            status=200,
                            mimetype='application/json')

    @api.expect(product)
    @api.response(201, 'Product created')
    def post(self):
        """ creates a new brand"""
        data = request.json
        with ClusterRpcProxy(CONFIG_RPC) as rpc:
            response_data = rpc.command_products.add(data)
            return response_data, 201


@api.route('/<int:id>')
class ProductItem(Resource):
    #@api.marshal_with(product)
    def get(self, id):
        """ returns a single product item"""
        with ClusterRpcProxy(CONFIG_RPC) as rpc:
            response_data = rpc.query_products.get(id)
            return Response(response=response_data,
                            status=200,
                            mimetype='application/json')

    @api.expect(product)
    @api.response(204, 'Product successfully updated')
    def put(self, id):
        data = request.json
        with ClusterRpcProxy(CONFIG_RPC) as rpc:
            response_data = rpc.command_products.update(id, data)
            return response_data, 204
