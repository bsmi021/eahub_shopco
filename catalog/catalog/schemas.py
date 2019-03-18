from marshmallow import Schema, fields

class ProductBrandSchema(Schema):
    id = fields.Int(required=True)
    name = fields.Str(required=True)
    created_at = fields.String()
    updated_at = fields.String()

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
    sku = fields.Str()


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