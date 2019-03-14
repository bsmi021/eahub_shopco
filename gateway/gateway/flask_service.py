from flask import Flask
from nameko.standalone.rpc import ServiceRpcProxy
import os
from .schemas import ProductSchema, ProductBrandSchema, CreateProductBrandSchema
import json
from werkzeug.wrappers import Response

app = Flask(__name__)


def rpc_proxy(service):
    RABBIT_USER = os.getenv('RABBIT_USER', 'guest')
    RABBIT_PASSWORD = os.getenv('RABBIT_PASSWORD', 'guest')
    RABBIT_HOST = os.getenv('RABBIT_HOST', '127.0.0.1')
    RABBIT_PORT = os.getenv('RABBIT_PORT', '5672')

    config = {'AMQP_URI': 'amqp://{}:{}@{}:{}/'.format(RABBIT_USER,
                                                       RABBIT_PASSWORD,
                                                       RABBIT_HOST,
                                                       RABBIT_PORT)}
    return ServiceRpcProxy(service, config)


products_rpc = rpc_proxy('products_service')

@app.route('/brands/<int:brand_id>')
def get_brand(brand_id):
    with rpc_proxy('products_service') as rpc:
        brand = rpc.get_product_brand(brand_id)

    return json.dumps(ProductBrandSchema().dump(brand).data)



if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
