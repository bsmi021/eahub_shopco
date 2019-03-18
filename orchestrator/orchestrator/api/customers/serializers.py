from flask_restplus import fields
from orchestrator.api.restplus import api

payment_method = api.model('Payment Method',
                           dict(
                               id=fields.Integer(readOnly=True, attribute='_id'),
                               alias=fields.String(required=True,
                                                   description='A friendly name to identify the payment method'),
                               card_type_id=fields.Integer(required=True),
                               card_number=fields.String(),
                               cardholder_name=fields.String(),
                               expiration=fields.String(),
                               security_number=fields.String(),
                               created_at=fields.String(),
                               updated_at=fields.String()
                           ))

customer = api.model('Customer',
                     dict(
                         id=fields.Integer(readOnly=True, attribute='_id'),
                         name=fields.String(required=True),
                         last_name=fields.String(required=True),
                         street_1=fields.String(required=True),
                         street_2=fields.String(required=False),
                         city=fields.String(required=True),
                         state=fields.String(required=True),
                         zip_code=fields.String(required=True),
                         country=fields.String(required=True),
                         email=fields.String(required=True),
                         phone=fields.String(required=True),
                         updated_at=fields.String(),
                         created_at=fields.String()
                     ))

customer_with_payment_methods = api.inherit('Customer with Payment Methods',
                                            customer,
                                            dict(
                                                payment_methods=fields.List(fields.Nested(payment_method))
                                            ))
