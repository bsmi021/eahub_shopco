import logging
import traceback

from flask_restplus import Api
from flask import jsonify

logger = logging.getLogger(__name__)

api = Api(version='1.0',
          title='SAS® Enterprise Architecture Hub ShopCo API',
          description='Collection of APIs which mimic an ecom environment')

@api.errorhandler
def default_error_handler(e):
    message = 'An unhandled exception occured'
    logger.exception(message)

    return jsonify({'message': message}), 500