# ./orchestrator/orchestrator/api/productype_ns.py
import logging
import os
from flask import request, jsonify, Response
from flask_restplus import Resource, Namespace, fields
from nameko.standalone.rpc import ClusterRpcProxy
import json

logger = logging.getLogger(__name__)

api = Namespace('producttypes')

RABBIT_USER = os.getenv('RABBIT_USER', 'guest')
RABBIT_PASSWORD = os.getenv('RABBIT_PASSWORD', 'guest')
RABBIT_HOST = os.getenv('RABBIT_HOST', '127.0.0.1')
RABBIT_PORT = os.getenv('RABBIT_PORT', '5672')

amqp_uri = 'amqp://{}:{}@{}:{}'.format(RABBIT_USER, RABBIT_PASSWORD, RABBIT_HOST, RABBIT_PORT)

CONFIG_RPC = {'AMQP_URI': amqp_uri}

product_type = api.model('Product Types',
                         dict(
                             _id=fields.Integer(readOnly=True),
                             name=fields.String(),
                             description=fields.String(),
                             parent_type_id=fields.Integer(),
                             created_at=fields.DateTime(),
                             updated_at=fields.DateTime
                         ))

