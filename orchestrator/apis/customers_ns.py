# ./orchestrator/orchestrator/api/catalog/products_ns.py
import logging
import os
from flask import request, jsonify, Response
from flask_restplus import Resource, Namespace, fields
from nameko.standalone.rpc import ClusterRpcProxy
import json

logger = logging.getLogger(__name__)

api = Namespace('customers')

MIME_TYPE = 'application/json'
RABBIT_USER = os.getenv('RABBIT_USER', 'guest')
RABBIT_PASSWORD = os.getenv('RABBIT_PASSWORD', 'guest')
RABBIT_HOST = os.getenv('RABBIT_HOST', '127.0.0.1')
RABBIT_PORT = os.getenv('RABBIT_PORT', '5672')

amqp_uri = 'amqp://{}:{}@{}:{}'.format(RABBIT_USER, RABBIT_PASSWORD, RABBIT_HOST, RABBIT_PORT)

CONFIG_RPC = {'AMQP_URI': amqp_uri}

account = api.model('Account',
                    dict(
                        user_name=fields.String(required=True),
                        password_hash=fields.String(required=True),
                        email=fields.String(required=True),
                        name=fields.String(required=True),
                        last_name=fields.String(required=True),
                        street_1=fields.String(required=True),
                        street_2=fields.String(required=False),
                        city=fields.String(required=True),
                        state=fields.String(required=True),
                        zip_code=fields.String(required=True),
                        country=fields.String(required=True),
                        phone=fields.String(required=True)
                    ))

customer = api.model('Customer',
                     dict(
                         id=fields.Integer(readOnly=True, attribute='_id'),
                         full_name=fields.String(required=True),
                         name=fields.String(required=True),
                         last_name=fields.String(required=True),
                         street_1=fields.String(required=True),
                         street_2=fields.String(required=False),
                         city=fields.String(required=True),
                         state=fields.String(required=True),
                         zip_code=fields.String(required=True),
                         country=fields.String(required=True),
                         email=fields.String(required=True),
                         phone=fields.String(required=True),
                         account_id=fields.Integer(required=True),
                         updated_at=fields.String(),
                         created_at=fields.String()
                     ))


@api.route('')
class CustomersCollection(Resource):

    # @api.marshal_with(customer, as_list=True, envelope='customers')
    def get(self, num_pages=5, limit=100):
        """
        returns a list of customers
        :param num_pages:
        :param limits:
        :return:
        """
        with ClusterRpcProxy(CONFIG_RPC) as rpc:
            response_data = rpc.query_customers.list(num_pages, limit)
            return Response(response=response_data,
                            status=200,
                            mimetype=MIME_TYPE)

    @api.expect(customer)
    @api.response(201, 'Customer Created')
    def post(self):
        data = request.json
        with ClusterRpcProxy(CONFIG_RPC) as rpc:
            response_data = rpc.command_customers.add_customer(data)
            return Response(response=response_data,
                            status=201,
                            mimetype=MIME_TYPE)


@api.route('/register')
class RegisterAction(Resource):

    @api.expect(account)
    @api.response(201, 'Account Created')
    def post(self):
        data = request.json
        with ClusterRpcProxy(CONFIG_RPC) as rpc:
            response_data = rpc.command_customers.register(data)
            return Response(response=json.dumps(response_data),
                            status=201,
                            mimetype=MIME_TYPE)


@api.route('/<int:id>')
@api.param('id', 'Customer identifier')
@api.response(404, 'Customer not found')
class CustomersItem(Resource):

    # @api.marshal_with(customer_with_payment_methods, envelope='customer', as_list=False)
    def get(self, id):
        """
        Get's a single customer based on the provided ID
        :param id:
        :return:
        """
        with ClusterRpcProxy(CONFIG_RPC) as rpc:
            response_data = rpc.query_customers.get(id)

            logger.info('Found customer: {}'.format(response_data))

            return Response(response=response_data,
                            status=200,
                            mimetype=MIME_TYPE)

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
            return Response(response=response_data,
                            status=204,
                            mimetype=MIME_TYPE)
