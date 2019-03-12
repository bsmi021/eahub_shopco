from flask import Flask
from nameko.standalone.rpc import ServiceRpcProxy
import os
from gateway.schemas import ProductSchema, ProductBrandSchema, CreateProductBrandSchema
import json
from werkzeug.wrappers import Response

app = Flask(__name__)


def rpc_proxy(service):
    rabbit_user = os.getenv('RABBIT_USER').strip()
    rabbit_password = os.getenv('RABBIT_PASSWORD').strip()
    rabbit_host = os.getenv('RABBIT_HOST').strip()
    rabbit_port = os.getenv('RABBIT_PORT').strip()

    config = {'AMQP_URI': 'amqp://{}:{}@{}:{}/'.format(rabbit_user,
                                                       rabbit_password,
                                                       rabbit_host,
                                                       rabbit_port)}
    return ServiceRpcProxy(service, config)


products_rpc = rpc_proxy('products_service')

@app.route('/brands/<int:brand_id>')
def get_brand(brand_id):
    with rpc_proxy('products_service') as rpc:
        brand = rpc.get_product_brand(brand_id)

    return json.dumps(ProductBrandSchema().dump(brand).data)



if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
