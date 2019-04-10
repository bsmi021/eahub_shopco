# ./orchestrator/apis/orders_ns.py
import logging
import os
from flask import request, jsonify, Response
from flask_restplus import Resource, Namespace, fields
from nameko.standalone.rpc import ClusterRpcProxy
import json

logger = logging.getLogger(__name__)

api = Namespace('orders', description='Api for querying orders.')

RABBIT_USER = os.getenv('RABBIT_USER', 'guest')
RABBIT_PASSWORD = os.getenv('RABBIT_PASSWORD', 'guest')
RABBIT_HOST = os.getenv('RABBIT_HOST', '127.0.0.1')
RABBIT_PORT = os.getenv('RABBIT_PORT', '5672')

amqp_uri = 'amqp://{}:{}@{}:{}'.format(RABBIT_USER, RABBIT_PASSWORD, RABBIT_HOST, RABBIT_PORT)

CONFIG_RPC = {'AMQP_URI': amqp_uri}

order = api.model('Order',
                  dict(
                      _id=fields.Integer(),
                      order_date=fields.String(),
                      customer_id=fields.Integer()
                  ))

@api.route('/<int:id>')
class OrderItem(Resource):
    def get(self, id):
        try:
            with ClusterRpcProxy(CONFIG_RPC) as rpc:
                response_data = rpc.query_orders.get(None, id)
                return Response(response=response_data,
                                status=200,
                                mimetype='application/json')
        except Exception as e:
            return e

