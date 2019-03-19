import uuid

class BasketItem(object):

    def __init__(self, product_id, product_name, unit_price, old_unit_price,
                 quantity):
        self.id = str(uuid.uuid4())
        self.product_name = product_name
        self.unit_price = unit_price
        self.old_unit_price = old_unit_price
        self.quantity = quantity

    def validate(self):
        return self.quantity < 1


class CustomerBasket(object):

    def __init__(self, buyer_id, items=[]):
        self.buyer_id = buyer_id
        self.items = items
