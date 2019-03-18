from flask_restplus import fields
from orchestrator.api.restplus import api

brand = api.model('Brand',
                          dict(
                              _id=fields.Integer(readOnly=True, description="Unique identifier for the brand category"),
                              name=fields.String(required=True, description='Brand Name'),
                              created_at=fields.String(readOnly=True, description='Date record was created'),
                              updated_at=fields.String(readOnly=True, description='Date last modified')
                          ))


shipping_details = api.model('Shipping Details',
                                 dict(
                                     weight=fields.Float(),
                                     height=fields.Float(),
                                     width=fields.Float(),
                                     depth=fields.Float()
                                 ))



product = api.model('Product',
                         dict(
                             _id=fields.Integer(readOnly=True, description='Item unique ID'),
                             name=fields.String(required=True, description='Item Name'),
                             description=fields.String(max_length=250, description='Item Description'),
                             price=fields.Float(description='Item Price'),
                             product_brand_id=fields.Integer(required=True),
                             product_brand=fields.String(readOnly=True, attribute='catalog_brand.brand'),
                             available_stock=fields.Integer(description='Quantity in stock'),
                             restock_threshold=fields.Integer(description='Available stock at which reorder is needed'),
                             max_stock_threshold=fields.Integer(description='Max units of item that can be inventoried'),
                             sku=fields.String(required=True, description='Product stock keeping unit'),
                             on_reorder=fields.Boolean(description='True if item is on reorder'),
                             created_at=fields.DateTime(readOnly=True, description='Date record was created'),
                             updated_at=fields.DateTime(readOnly=True, description='Date last modified'),
                             shipping_details=fields.Nested(shipping_details, required=False)
                         ))

