from marshmallow import Schema, fields

class AddPaymentMethodSchema(Schema):
    customer_id = fields.Str(required=True)
    cardholder_name = fields.Str(required=True)
    expiration = fields.Str(required=True)
    card_number = fields.Str(required=True)
    security_number = fields.Str(required=True)
    card_type_id = fields.Int(require=True)
    alias = fields.Str()

class CreateCustomerSchema(Schema):
    name = fields.Str(required=True)
    last_name = fields.Str(required=True)
    street_1 = fields.Str(required=True)
    street_2 = fields.Str(required=False)
    state = fields.Str(required=True)
    city = fields.Str(required=True)
    zip_code = fields.Str(required=True)
    email = fields.Str(required=True)
    phone = fields.Str(required=True)
    payment_method = fields.Nested('PaymentMethodSchema', many=False)

class PaymentMethodSchema(Schema):
    customer = fields.Str(required=False)
    cardholder_name = fields.Str(required=True)
    expiration = fields.Str(required=True)
    card_number = fields.Str(required=True)
    security_number = fields.Str(required=True)
    card_type_id = fields.Int(required=True)
    alias = fields.Str()
    created_at = fields.DateTime()
    updated_at = fields.DateTime()

class CustomerSchema(Schema):
    id = fields.Str(required=True)
    name = fields.Str(required=True)
    last_name = fields.Str(required=True)
    street_1 = fields.Str(required=True)
    street_2 = fields.Str(required=False)
    state = fields.Str(required=True)
    city = fields.Str(required=True)
    zip_code = fields.Str(required=True)
    email = fields.Str(required=True)
    phone = fields.Str(required=True)
    payment_methods=fields.Nested(PaymentMethodSchema, many=True)

