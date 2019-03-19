from marshmallow import Schema, fields, post_load

class BasketCheckoutSchema(Schema):
    buyer_id = fields.Str(required=True)
    buyer = fields.Str(required=True)
    city = fields.Str(required=True)
    street1 = fields.Str(required=True)
    street2 = fields.Str()
    state = fields.Str()
    country = fields.Str(required=True)
    zip_code = fields.Str(required=True)
    card_number = fields.Str()
    card_holder_name = fields.Str()
    card_expiration = fields.Str()
    card_security_number = fields.Str()
    card_type_id = fields.Int()


class BasketItemSchema(Schema):
    id = fields.Str(required=True)
    product_id = fields.Int(required=True)
    product_name = fields.Str()
    unit_price = fields.Decimal()
    old_unit_price = fields.Decimal()
    quantity = fields.Int()


class CustomerBasketSchema(Schema):
    buyer_id = fields.Str(required=True)
    items = fields.Nested(BasketItemSchema, many=True)


