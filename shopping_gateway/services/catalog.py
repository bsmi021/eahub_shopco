import requests
import json

uri = 'http://localhost:8080/api'

product_uri = '{}/products'.format(uri)


def get_catalog_item(id):
    data = requests.get('{}/{}'.format(product_uri, id))

    return data


def get_catalog_items():
    data = requests.get(product_uri)

    return data


if __name__ == '__main__':
    product = get_catalog_item(1)

    # print(type(product))
    print(product.json())

    product = product.json()

    print(type(product))
    print(product['name'], product['price'])

    # items = get_catalog_items().json()

    # for item in items:
    #    print(item)
