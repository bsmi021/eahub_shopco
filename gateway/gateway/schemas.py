from marshmallow import Schema, fields


class CreateProductBrandSchema(Schema):
    name = fields.Str(required=True)


class ProductBrandSchema(Schema):
    id = fields.Int(required=True)
    name = fields.Str(required=True)
    created_at = fields.DateTime()
    updated_at = fields.DateTime()


class CreateProductSchema(Schema):
    name = fields.Str(required=True)
    description = fields.Str()
    price = fields.Decimal(as_string=True)
    available_stock = fields.Int(required=True)
    restock_threshold = fields.Int(required=True)
    max_stock_threshold = fields.Int(required=True)
    product_brand_id = fields.Int(required=True)


class ProductSchema(Schema):
    id = fields.Int(required=True)
    name = fields.Str(required=True)
    description = fields.Str()
    price = fields.Decimal(as_string=True)
    available_stock = fields.Int(required=True)
    restock_threshold = fields.Int(required=True)
    max_stock_threshold = fields.Int(required=True)
    product_brand_id = fields.Int(required=True)
    product_brand = fields.Nested(ProductBrandSchema, many=False)
    created_at = fields.DateTime()
    updated_at = fields.DateTime()


class UpdateProductSchema(Schema):
    id = fields.Int(required=True)
    product = fields.Nested(CreateProductSchema, many=False)


class UpdateBrandSchema(Schema):
    id = fields.Int(required=True)
    brand = fields.Nested(CreateProductBrandSchema, many=False)


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
    card_number = fields.String()
    cardholder_name = fields.String()
    card_security_number = fields.String()
    card_expiration = fields.String()
    payment_method_id = fields.String()
    order_status_id = fields.Integer()
    order_date = fields.DateTime()
    is_draft = fields.Boolean()


class CreateAddressSchema(Schema):
    street1 = fields.String(required=True)
    street2 = fields.String()
    city = fields.String(required=True)
    state = fields.String(required=True)
    country = fields.String(required=False)
    zip_code = fields.String(required=True)


class CreateOrderDetailSchema(Schema):
    product_id = fields.Int(required=True)
    product_name = fields.String(required=True)
    unit_price = fields.Float(required=True)
    discount = fields.Float()
    units = fields.Integer()


class CreateOrderSchema(Schema):
    customer_id = fields.String(required=True)
    address = fields.Nested(CreateAddressSchema, many=False)
    order_items = fields.Nested(CreateOrderDetailSchema, many=True)
    card_number = fields.String()
    cardholder_name = fields.String()
    card_expiration = fields.String()
    card_security_number = fields.String()
    payment_method_id = fields.String()


class BasketCheckoutSchema(Schema):
    id = fields.Str(required=True)
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


class BasketSchema(Schema):
    buyer_id = fields.Str(required=True)
    items = fields.Nested(BasketItemSchema, many=True)
