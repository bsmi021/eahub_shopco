# ./orchestrator/orchestrator/api/catalog/views.py
import logging
import os
from flask import request, jsonify
from flask_restplus import Resource
from orchestrator.api.restplus import api
from nameko.standalone.rpc import ClusterRpcProxy
from orchestrator.api.customers.serializers import customer, payment_method, customer_with_payment_methods
import json

logger = logging.getLogger(__name__)

customer_ns = api.namespace('customers')

RABBIT_USER = os.getenv('RABBIT_USER', 'guest')
RABBIT_PASSWORD = os.getenv('RABBIT_PASSWORD', 'guest')
RABBIT_HOST = os.getenv('RABBIT_HOST', '127.0.0.1')
RABBIT_PORT = os.getenv('RABBIT_PORT', '5672')

amqp_uri = 'amqp://{}:{}@{}:{}'.format(RABBIT_USER, RABBIT_PASSWORD, RABBIT_HOST, RABBIT_PORT)

CONFIG_RPC = {'AMQP_URI': amqp_uri}

@customer_ns.route('')
class CustomersCollection(Resource):

    @api.marshal_with(customer, as_list=True, envelope='customers')
    def get(self, num_pages=5, limit=100):
        """
        returns a list of customers
        :param num_pages:
        :param limits:
        :return:
        """
        with ClusterRpcProxy(CONFIG_RPC) as rpc:
            response_data = rpc.query_customers.list(num_pages, limit)
            return json.loads(response_data), 200

    @api.expect(customer)
    @api.response(201, 'Customer Created')
    def post(self):
        data = request.json
        with ClusterRpcProxy(CONFIG_RPC) as rpc:
            response_data = rpc.command_customers.add(data)
            return response_data, 201

@customer_ns.route('/<int:id>')
class CustomersItem(Resource):

    @api.marshal_with(customer_with_payment_methods, envelope='customer', as_list=False)
    def get(self, id):
        """
        Get's a single customer based on the provided ID
        :param id:
        :return:
        """
        with ClusterRpcProxy(CONFIG_RPC) as rpc:
            response_data = rpc.query_customers.get(id)

            logger.info('Found customer: {}'.format(response_data))

            return json.loads(response_data)

    @api.expect(customer)
    @api.response(204, 'Customer successfully updated')
    def put(self, id):
        """
        Updates a customer record
        :param id:
        :return:
        """
        data = request.json
        with ClusterRpcProxy(CONFIG_RPC) as rpc:
            response_data = rpc.command_customers.update(id, data)
            return response_data, 204
