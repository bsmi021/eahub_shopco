# ./orchestrator/apis/basket_ns.py
import logging
import os
from flask import request, jsonify, Response
from flask_restplus import Resource, Namespace, fields
from nameko.standalone.rpc import ClusterRpcProxy
import json

logger = logging.getLogger(__name__)

api = Namespace('basket', description='Customer Basket/Checkout System')

RABBIT_USER = os.getenv('RABBIT_USER', 'guest')
RABBIT_PASSWORD = os.getenv('RABBIT_PASSWORD', 'guest')
RABBIT_HOST = os.getenv('RABBIT_HOST', '127.0.0.1')
RABBIT_PORT = os.getenv('RABBIT_PORT', '5672')

amqp_uri = 'amqp://{}:{}@{}:{}'.format(RABBIT_USER, RABBIT_PASSWORD, RABBIT_HOST, RABBIT_PORT)

CONFIG_RPC = {'AMQP_URI': amqp_uri}

basket_item = api.model('Basket Item',
                        dict(
                            product_id=fields.Integer(required=True),
                            product_name=fields.String(),
                            unit_price=fields.Float(),
                            old_unit_price=fields.Float(),
                            quantity=fields.Integer
                        ))

basket = api.model('Basket',
                   dict(
                       buyer_id=fields.String(required=True),
                       items=fields.List(fields.Nested(basket_item))
                   ))

checkout_basket = api.model('BasketCheckout',
                            dict(
                                buyer_id=fields.String(),
                                buyer=fields.String(),
                                city=fields.String(required=True),
                                street1=fields.String(required=True),
                                street2=fields.String(),
                                state=fields.String(),
                                country=fields.String(required=True),
                                zip_code=fields.String(required=True),
                                card_number=fields.String(),
                                card_holder_name=fields.String(),
                                card_expiration=fields.String(),
                                card_security_number=fields.String(),
                                card_type_id=fields.Integer()
                            ))

@api.route('')
class BasketsCollection(Resource):

    @api.expect(basket)
    @api.response(201, 'Basket created')
    def post(self):
        """
        Creates a basket for a buyer
        :return:
        """
        data = request.json
        with ClusterRpcProxy(CONFIG_RPC) as rpc:
            response_data = rpc.basket_service.update_basket(data)


        return response_data, 201

@api.route('/<int:id>')
class BasketItem(Resource):

    def get(self, id):
        """
        returns a basket for the buyer, if none exists one will be created
        but not stored until the post is called
        :param id:
        :return:
        """
        with ClusterRpcProxy(CONFIG_RPC) as rpc:
            response_data = rpc.basket_service.get_basket_by_id(id)

        return Response(response=json.dumps(response_data),
                        status=200,
                        mimetype='application/json')

@api.route('/checkout')
class BasketActions(Resource):

    @api.expect(checkout_basket)
    @api.response(204, 'Basket sent for checkout')
    def put(self):
        data = request.json

        with ClusterRpcProxy(CONFIG_RPC) as rpc:
            rpc.basket_service.checkout(data)

        return {'message':'submitted'}, 204
