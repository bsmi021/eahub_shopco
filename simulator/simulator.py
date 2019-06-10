import requests
from py_linq import Enumerable
import random
import json
from werkzeug.security import generate_password_hash
from faker import Faker
from faker.providers import profile, person, address, phone_number, credit_card

from uszipcode import SearchEngine

import namesgenerator  # using this for brands and products

fake = Faker()
fake.add_provider(profile)
fake.add_provider(person)
fake.add_provider(address)
fake.add_provider(phone_number)
fake.add_provider(credit_card)

zip_search = SearchEngine(simple_zipcode=True)


def get_random_city_zip():
    state_abbr = fake.state_abbr(include_territories=False)
    #print (state_abbr)
    state_abbr = 'NY'
    #zip_code = fake.zipcode_in_state(state_abbr=state_abbr)
    #f_zip_code = zip_search.by_zipcode(zip_code)

    zip_code = random.randint(10000,99999)
    f_zip_code = zip_search.by_zipcode(zip_code)

    while f_zip_code.zipcode is None:
        zip_code = random.randint(10000,99999)
        f_zip_code = zip_search.by_zipcode(zip_code)

    print (f_zip_code)
    return f_zip_code


uri = "http://brwsmi-espserver.unx.sas.com:5000/api"

brand_uri = "{}/brands".format(uri)
products_uri = "{}/products".format(uri)
users_uri = "{}/user".format(uri)
basket_uri = "{}/basket".format(uri)
customers_uri = "{}/customers".format(uri)
register_uri = f"{customers_uri}/register"
sites_uri = f'{uri}/warehouse/sites'

brand_count = 13
product_count = 300
customer_count = 45000
site_count = 12
order_count = 5000

print('Checking on customers, creating if necessary')

customers = requests.get(customers_uri)

if customers.json() is None or len(customers.json()) < customer_count:
    max_range = customer_count - len(customers.json())

    print(f'Creating {max_range} Customers')

    for i in range(0, max_range):
        profile = fake.profile()
        person = {
            'first_name': str.split(profile['name'])[0],
            'last_name': str.split(profile['name'])[1]
        }
        #
        f_zip_code = get_random_city_zip()

        address = {
            'street_1': fake.street_address(),
            'street_2': "",
            'city': f_zip_code.major_city,
            'state': f_zip_code.state,
            'country': 'US',
            'zip_code': f_zip_code.zipcode
        }
        phone = fake.phone_number()
        #
        account = {
            'user_name': profile['username'],
            'password_hash': generate_password_hash(profile['username']),
            'email': profile['mail'],
            'name': person['first_name'],
            'last_name': person['last_name'],
            'street_1': address['street_1'],
            'street_2': address['street_2'],
            'city': address['city'],
            'state': address['state'],
            'zip_code': address['zip_code'],
            'country': address['country'],
            'phone': phone
        }

        # request_data = json.dumps(account)
        requests.post(register_uri, json=account)

print("Checking on sites, creating if necessary")
sites = requests.get(sites_uri)

if sites.json() is None or len(sites.json()) < site_count:

    if len(sites.json()) == 0:
        max_range = site_count
    else:
        max_range = site_count - len(sites.json())

    for i in range(0, max_range):
        zip_info = get_random_city_zip()

        site = {'name': zip_info.post_office_city, 'zip_code': zip_info.zipcode, 'type_id': 1}

        requests.post(sites_uri, json=site)

print("Checking on brands, creating if necessary")
brands = requests.get(brand_uri)

if brands.json() is None or len(brands.json()) < brand_count:

    if brands.json() is None:
        max_range = brand_count
    else:
        max_range = brand_count - len(brands.json())

    print(f'Creating {max_range} brands.')

    for i in range(0, max_range):
        brand = {'name': namesgenerator.get_random_name()}

        request_data = json.dumps(brand)
        response = requests.post(brand_uri, json=brand)

    brands = requests.get(brand_uri)

brands = brands.json()

print('Checking on products, creating if necessary')
products = requests.get(products_uri)

if products.json() is None or len(products.json()) < 300:

    colors = ['white', 'black', 'red', 'blue', 'yellow', 'titanium', 'steel-grey',
              'grey', 'green', 'light-blue', 'pink', 'orange']

    types = ['kitchen', 'outdoor', 'indoor', 'bedroom', 'living room']

    if products.json() is None or len(products.json()) == 0:
        max_product_id = 0
        max_range = 300
    else:
        products = Enumerable(products.json())
        max_product_id = products.max(lambda x: x['_id']) + 1
        max_range = 300 - len(products.json())

    print(f'Creating {max_range} products.')

    for i in range(max_product_id, max_product_id + max_range):
        brand_id = random.choice(brands)['_id']

        product_name = namesgenerator.get_random_name(' ')
        sku = f"WR-{f'00000000{i + 1}'[-8:]}"
        max_stock_threshold = random.randint(105, 1050)
        restock_threshold = random.randint(10, 50)
        available_stock = random.randint(restock_threshold + 5, max_stock_threshold)

        product = {
            "name": product_name,
            "description": namesgenerator.get_random_name(),
            "price": float(random.randint(1, 255)) + .99,
            "product_brand_id": brand_id,
            "product_type_id": 1,
            "discontinued": False,
            "max_stock_threshold": max_stock_threshold,
            "sku": sku,
            "attributes": {
                "weight": random.randint(10, 100),
                "height": random.randint(1, 100),
                "width": random.randint(1, 100),
                "depth": random.randint(1, 100),
                "color": random.choice(colors),
                "type": random.choice(types)
            }
        }

        request_data = json.dumps(product)
        response = requests.post(products_uri, json=request_data)

customers = requests.get(customers_uri)
customers = customers.json()
card_types = [{'id': 1, 'value': 'discover'},
              {'id': 2, 'value': 'visa16'},
              {'id': 3, 'value': 'amex'},
              {'id': 4, 'value': 'mastercard'}]

for customer in customers:
    provider = random.choice(card_types)
    customer['card_type_id'] = provider['id']
    customer['card_provider'] = provider['value']
    customer['expiration'] = fake.credit_card_expire(start='now', end="+4y", date_format='%m/%y')
    customer['card_number'] = fake.credit_card_number(card_type=customer['card_provider'])
    customer['security_number'] = fake.credit_card_security_code(card_type=customer['card_provider'])

products = requests.get(products_uri)
products = products.json()

print(f'Creating {order_count} orders now, this may take a while...')
for i in range(0, order_count):
    basket_item_ct = random.randint(1, 6)

    customer = random.choice(customers)

    items = []

    for x in range(1, basket_item_ct):
        product = random.choice(products)

        while product in items:
            product = random.choice(products)

        items.append(product)

    quantity_gen = lambda p: random.randint(1, 5) if p < 20.99 else 1

    basket = {
        'buyer_id': customer['_id'],
        'items': [
            {
                'product_id': product['_id'],
                'product_name': product['name'],
                'unit_price': product['price'],
                'old_unit_price': product['price'],
                'quantity': quantity_gen(product['price'])
            } for product in items]
    }

    response_data = requests.post(basket_uri, json=basket)

    if response_data.status_code == 201:
        checkout_basket = {
            'buyer_id': str(customer['_id']),
            'buyer': customer['full_name'],
            'city': customer['city'],
            'street_1': customer['street_1'],
            'street_2': customer['street_2'],
            'state': customer['state'],
            'country': customer['country'],
            'zip_code': customer['zip_code'],
            'card_number': customer['card_number'],
            'cardholder_name': customer['full_name'],
            'expiration': customer['expiration'],
            'security_number': customer['security_number'],
            'card_type_id': int(customer['card_type_id'])
        }

        resp = requests.put(f'{basket_uri}/checkout', json=checkout_basket)

        if resp.status_code != 204:
            print(resp)
        else:
            print(f'Order sent for Customer {customer["_id"]}: {customer["full_name"]}')

#
# products = requests.get(products_uri)#.json()
# #users = requests.get(users_uri)
# products = products.json()
#
# for product in products:
#     print(product['_id'])
#
# buyer_id = 1
# buyer_name = 'Gordon Ramsay'
# address = {
#     'street_1':'1313 Mockingbird Ln',
#     'street_2':None,
#     'city':"Anytown",
#     'state':'NY',
#     'zip_code':'10010',
#     'country':'US'
# }
# email = 'gordon@hellskitchen.com'
# phone = '18005556666'
# card_number='4525242422'
# cardholder_name='Gordon Ramsay'
# security_number='442'
# expiration='01/99'
# card_type_id=1
#
# basket = {
#     'buyer_id':buyer_id,
#     'items':[
#     {
#         'product_id':product['_id'],
#         'product_name':product['name'],
#         'unit_price':product['price'],
#         'old_unit_price':product['price'],
#         'quantity': random.randint(1,10)
#     } for product in products]
# }
#
# basket = json.dumps(basket)
#
# print(basket)
# resp = requests.post(basket_uri, json=basket)
#
# if resp.status_code == 201:
#     checkout_basket={
#         'buyer_id':str(buyer_id),
#         'buyer':buyer_name,
#         'city':address['city'],
#         'street_1':address['street_1'],
#         'street_2':'',
#         'state':address['state'],
#         'country':address['country'],
#         'zip_code':address['zip_code'],
#         'card_number':card_number,
#         'cardholder_name':cardholder_name,
#         'expiration':expiration,
#         'security_number':security_number,
#         'card_type_id':int(card_type_id)
#     }
#
#     checkout_basket = json.dumps(checkout_basket)
#     print (checkout_basket)
#
#     resp = requests.put(f'{basket_uri}/checkout', json=checkout_basket)
#
#     print(resp.status_code)
#
# #print(products)
