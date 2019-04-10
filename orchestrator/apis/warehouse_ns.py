# ./orchestrator/orchestrator/apis/sites_ns.py
import logging
import os
from flask import request, jsonify, Response
from flask_restplus import Resource, Namespace, fields
from nameko.standalone.rpc import ClusterRpcProxy
import json

logger = logging.getLogger(__name__)

api = Namespace('warehouse')

RABBIT_USER = os.getenv('RABBIT_USER', 'guest')
RABBIT_PASSWORD = os.getenv('RABBIT_PASSWORD', 'guest')
RABBIT_HOST = os.getenv('RABBIT_HOST', '127.0.0.1')
RABBIT_PORT = os.getenv('RABBIT_PORT', '5672')

amqp_uri = 'amqp://{}:{}@{}:{}'.format(RABBIT_USER, RABBIT_PASSWORD, RABBIT_HOST, RABBIT_PORT)

CONFIG_RPC = {'AMQP_URI': amqp_uri}

site = api.model('Warehouse Site',
                 dict(
                     _id=fields.Integer(),
                     name=fields.String(required=True),
                     zip_code=fields.String(required=True),
                     type=fields.String(),
                     type_id=fields.Integer(required=True),
                     created_at=fields.DateTime(),
                     updated_at=fields.DateTime
                 ))


@api.route('/sites')
class SitesCollection(Resource):

    def get(self, num_pages=5, limit=10):
        """
        returns a list of the shipping sites
        :param num_pages:
        :param limit:
        :return:
        """

        with ClusterRpcProxy(CONFIG_RPC) as rpc:
            response_data = rpc.query_site.list(num_pages, limit)
            return Response(response_data,
                            status=200,
                            mimetype='application/json')

    @api.expect(site)
    @api.response(201, 'Site created')
    def post(self):
        data = request.json
        with ClusterRpcProxy(CONFIG_RPC) as rpc:
            response_data = rpc.command_site.add(data)
            return response_data['id'], 201


@api.route('/sites/<int:id>')
class SitesItem(Resource):

    def get(self, id):
        """
        returns a single site based on the provided id
        :param id:
        :return:
        """
        with ClusterRpcProxy(CONFIG_RPC) as rpc:
            response_data = rpc.query_site.get(id)
            return Response(response_data,
                            status=200,
                            mimetype='application/json')

    @api.expect(site)
    @api.response(204, 'Site updated successfully')
    def put(self, id):
        data = request.json
        with ClusterRpcProxy(CONFIG_RPC) as rpc:
            data['id'] = id
            response_data = rpc.command_site.update(id, data)
            return response_data, 204


@api.route('/site/<int:id>/inventory')
class SiteInventory(Resource):
    def get(self, id):

        args = request.args.to_dict()
        num_page=None
        limit=None

        if 'num_page' in args:
            num_page = int(args['num_page'])

        if 'limit' in args:
            limit = int(args['limit'])


        with ClusterRpcProxy(CONFIG_RPC) as rpc:
            response_data = rpc.query_inventory.get_by_site_id(id, num_page, limit)
            return Response(response_data,
                            status=200,
                            mimetype='application/json')


@api.route('/inventory/<int:product_id>')
class InventoryItems(Resource):

    def get(self, product_id):
        """
        gets all of the inventory for a product
        :param product_id:
        :return:
        """
        with ClusterRpcProxy(CONFIG_RPC) as rpc:
            response_data = rpc.query_inventory.get_by_product_id(product_id)
            return Response(response_data,
                            status=200,
                            mimetype='application/json')
