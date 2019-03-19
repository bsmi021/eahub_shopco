from marshmallow import Schema, fields





class AddressSchema(Schema):
    id = fields.String(required=True)
    street1 = fields.String(required=True)
    street2 = fields.String()
    city = fields.String(required=True)
    state = fields.String(required=True)
    country = fields.String(required=True)
    zip_code = fields.String(required=True)


class OrderDetailSchema(Schema):
    id = fields.String(required=True)
    order_id = fields.String(required=True)
    product_id = fields.String(required=True)
    product_name = fields.String(required=True)
    unit_price = fields.Float(required=True)
    discount = fields.Float()
    units = fields.Integer()


class OrderSchema(Schema):
    id = fields.String(required=True)
    customer_id = fields.String(required=True)
    address_id = fields.String(required=True)
    address = fields.Nested(AddressSchema, many=False)
    order_items = fields.Nested(OrderDetailSchema, many=True)
    order_status_id = fields.Integer()
    order_date = fields.DateTime()
    is_draft = fields.Boolean()

class OrderStartedEvent(Schema):
    user_id = fields.Int(required=True),
    user_name = fields.Str(required=True),
    card_type_id = fields.Int(),
    card_number = fields.Str(),
    security_number = fields.Str(),
    cardholder_name = fields.Str(),
    expiration = fields.Str(),
    order = fields.Nested(OrderSchema, many=False)

class OrderStatusChangedToSubmittedEvent(Schema):
    order_id = fields.Int(),
    order_status_id = fields.Int(),
    buyer_name = fields.Str()

class OrderStockItemSchema(Schema):
    product_id = fields.Int(required=True)
    units = fields.Int(required=True)

class OrderStatusChangedToAwaitingValidationEvent(Schema):
    order_id = fields.Int(required=True)
    order_stock_items = fields.Nested(OrderStockItemSchema, many=True)


class OrderStockConfirmedEvent(Schema):
    order_id = fields.Int(required=True)


class OrderStockRejectedEvent(Schema):
    order_id = fields.Int(required=True)
    order_stock_items = fields.Nested(OrderStockItemSchema, many=True)

class OrderStatusChangedToPaidEvent(Schema):
    order_id = fields.Int(required=True)
    order_stock_items = fields.Nested(OrderStockItemSchema, many=True)

class BuyerAndPaymentMethodVerifiedEvent(Schema):
    buyer_id = fields.Int
    payment_id = fields.Int
    order_id = fields.Int