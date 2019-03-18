# ./orchestrator/orchestrator/api/catalog/views.py
import logging
import os
from flask import request, jsonify
from flask_restplus import Resource
from orchestrator.api.restplus import api
from nameko.standalone.rpc import ClusterRpcProxy
from orchestrator.api.catalog.serializers import brand, product
import json

logger = logging.getLogger(__name__)

brand_ns = api.namespace('brands')
product_ns = api.namespace('products')

RABBIT_USER = os.getenv('RABBIT_USER', 'guest')
RABBIT_PASSWORD = os.getenv('RABBIT_PASSWORD', 'guest')
RABBIT_HOST = os.getenv('RABBIT_HOST', '127.0.0.1')
RABBIT_PORT = os.getenv('RABBIT_PORT', '5672')

amqp_uri = 'amqp://{}:{}@{}:{}'.format(RABBIT_USER, RABBIT_PASSWORD, RABBIT_HOST, RABBIT_PORT)

CONFIG_RPC = {'AMQP_URI': amqp_uri}

@brand_ns.route('')
class BrandsCollection(Resource):

    @api.marshal_list_with(brand)
    def get(self, num_page=5, limit=5):
        """ returns a list of brands """
        with ClusterRpcProxy(CONFIG_RPC) as rpc:
            response_data = rpc.query_brands.list(num_page, limit)
            return json.loads(response_data)

    @api.expect(brand)
    @api.response(201, 'Brand created')
    def post(self):
        """ creates a new brand"""
        data = request.json
        with ClusterRpcProxy(CONFIG_RPC) as rpc:
            response_data = rpc.command_brands.add(data)
            return response_data, 201

@brand_ns.route('/<int:id>')
class BrandsItem(Resource):

    @api.marshal_with(brand)
    def get(self, id):
        """ returns a single brand item"""
        with ClusterRpcProxy(CONFIG_RPC) as rpc:
            response_data = rpc.query_brands.get(id)
            return json.loads(response_data)

    @api.expect(brand)
    @api.response(204, 'Brand successfully updated')
    def put(self, id):
        data = request.json
        with ClusterRpcProxy(CONFIG_RPC) as rpc:
            response_data = rpc.command_brands.update(id, data)
            return response_data, 204


@product_ns.route('')
class ProductsCollection(Resource):
    @api.marshal_list_with(product)
    def get(self, num_page=5, limit=5):
        """ returns a list of products """
        with ClusterRpcProxy(CONFIG_RPC) as rpc:
            response_data = rpc.query_products.list(num_page, limit)
            return json.loads(response_data)

    @api.expect(product)
    @api.response(201, 'Product created')
    def post(self):
        """ creates a new brand"""
        data = request.json
        with ClusterRpcProxy(CONFIG_RPC) as rpc:
            response_data = rpc.command_products.add(data)
            return response_data, 201

@product_ns.route('/<int:id>')
class ProductItem(Resource):
    @api.marshal_with(product)
    def get(self, id):
        """ returns a single product item"""
        with ClusterRpcProxy(CONFIG_RPC) as rpc:
            response_data = rpc.query_products.get(id)
            return json.loads(response_data)

    @api.expect(product)
    @api.response(204, 'Product successfully updated')
    def put(self, id):
        data = request.json
        with ClusterRpcProxy(CONFIG_RPC) as rpc:
            response_data = rpc.command_products.update(id, data)
            return response_data, 204
