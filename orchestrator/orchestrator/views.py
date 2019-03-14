import os
import json
import itertools
from .config import *

from flask import Blueprint, jsonify, request
from nameko.standalone.rpc import ClusterRpcProxy

customers = Blueprint('customers', __name__)

RABBIT_USER = os.getenv('RABBIT_USER', 'guest')
RABBIT_PASSWORD = os.getenv('RABBIT_PASSWORD', 'guest')
RABBIT_HOST = os.getenv('RABBIT_HOST', '127.0.0.1')
RABBIT_PORT = os.getenv('RABBIT_PORT', '5672')

amqp_uri = 'amqp://{}:{}@{}:{}'.format(RABBIT_USER, RABBIT_PASSWORD, RABBIT_HOST, RABBIT_PORT)

CONFIG_RPC = {'AMQP_URI': amqp_uri}


@customers.route('/customers/<string:customer_id>', methods=['GET'])
def get_customer(customer_id):
    try:
        response = get_customer_rpc(customer_id)
        return jsonify(response), 200
    except Exception as e:
        return error_response(e, 500)


def get_customer_rpc(customer_id):
    with ClusterRpcProxy(CONFIG_RPC) as rpc:
        customer = rpc.customers_service.get(customer_id)

        return {
            'status': 'success',
            'customer': json.loads(customer)
        }


@customers.route('/customers', methods=['GET'])
def get_customers():
    try:
        with ClusterRpcProxy(CONFIG_RPC) as rpc:
            response_object = rpc.customers_service.list()
            return jsonify(response_object), 200
    except Exception as e:
        return error_response(e, 500)


@customers.route('/customers', methods=['POST'])
def create_customer():
    customer_data = request.get_json()

    if not customer_data:
        return error_response('Invalid payload', 400)
    try:
        with ClusterRpcProxy(CONFIG_RPC) as rpc:
            response_object = rpc.customers_service.create(customer_data)
            return jsonify(response_object), 201
    except Exception as e:
        return error_response(e, 500)


def error_response(e, code):
    response = {
        'status': 'fail',
        'message': str(e)
    }
    return jsonify(response), code
