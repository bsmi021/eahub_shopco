import logging

from flask import jsonify
from flask_restplus import Api

from .brand_ns import api as brand_ns
from .products_ns import api as product_ns
from .customers_ns import api as customer_ns
from .basket_ns import api as basket_ns

logger = logging.getLogger(__name__)

api = Api(version='1.0',
          title='SAS® Enterprise Architecture Hub ShopCo API',
          description='Collection of APIs which mimic an ecom environment')


@api.errorhandler
def default_error_handler(e):
    message = 'An unhandled exception occured'
    logger.exception(message)

    return jsonify({'message': message}), 500


api.add_namespace(brand_ns)
api.add_namespace(customer_ns)
api.add_namespace(product_ns)
api.add_namespace(basket_ns)
