import logging
from flask_restplus import Api
from flask import jsonify

from ..services.catalog import get_catalog_items, get_catalog_item

logger = logging.getLogger(__name__)

api = Api(version='1.0',
          title='Shopping Gateway')

@api.errorhandler
def default_error_handler(e):
    message = 'An unhandled exception occured'
    logger.exception(message)

    return jsonify({'message': message}), 500