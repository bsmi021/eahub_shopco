# ./orchestrator/apis/catalog/brands_ns.py
import logging
import os
from flask import request, jsonify, Response
from flask_restplus import Resource, Namespace, fields
from nameko.standalone.rpc import ClusterRpcProxy
import json

logger = logging.getLogger(__name__)

api = Namespace('brands', description='Brands which products are obtained from')

RABBIT_USER = os.getenv('RABBIT_USER', 'guest')
RABBIT_PASSWORD = os.getenv('RABBIT_PASSWORD', 'guest')
RABBIT_HOST = os.getenv('RABBIT_HOST', '127.0.0.1')
RABBIT_PORT = os.getenv('RABBIT_PORT', '5672')

amqp_uri = 'amqp://{}:{}@{}:{}'.format(RABBIT_USER, RABBIT_PASSWORD, RABBIT_HOST, RABBIT_PORT)

CONFIG_RPC = {'AMQP_URI': amqp_uri}

brand = api.model('Brand',
                  dict(
                      _id=fields.Integer(readOnly=True, description="Unique identifier for the brand category"),
                      name=fields.String(required=True, description='Brand Name'),
                      created_at=fields.String(readOnly=True, description='Date record was created'),
                      updated_at=fields.String(readOnly=True, description='Date last modified')
                  ))


@api.route('')
class BrandsCollection(Resource):

    #@api.marshal_list_with(brand)
    def get(self, num_page=5, limit=5):
        """ returns a list of brands """
        with ClusterRpcProxy(CONFIG_RPC) as rpc:
            response_data = rpc.query_brands.list(num_page, limit)
            return Response(response=response_data,
                            status=200,
                            mimetype='application/json')

    @api.expect(brand)
    @api.response(201, 'Brand created')
    def post(self):
        """ creates a new brand"""
        data = request.json
        with ClusterRpcProxy(CONFIG_RPC) as rpc:
            response_data = rpc.command_brands.add(data)
            return response_data, 201

@api.route('/<int:id>')
class BrandsItem(Resource):

    #@api.marshal_with(brand)
    def get(self, id):
        """ returns a single brand item"""
        with ClusterRpcProxy(CONFIG_RPC) as rpc:
            response_data = rpc.query_brands.get(id)
            return Response(response=response_data,
                            status=200,
                            mimetype='application/json')#json.loads(response_data)

    @api.expect(brand)
    @api.response(204, 'Brand successfully updated')
    def put(self, id):
        data = request.json
        with ClusterRpcProxy(CONFIG_RPC) as rpc:
            response_data = rpc.command_brands.update(id, data)
            return response_data, 204
