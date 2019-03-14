from .models import *
from nameko.rpc import rpc
from nameko.events import event_handler, EventDispatcher
from mongoengine import connect
import os
from .schemas import *
from .exceptions import *
import logging

logger = logging.getLogger(__name__)


class CustomersService:
    name = "customers_service"

    connect(os.getenv('MONGO_DATABASE', 'customers'),
            host=os.getenv('MONGO_HOST', '127.0.0.1'),
            port=int(os.getenv('MONGO_PORT', 27017)))

    fire_event = EventDispatcher()

    def __init__(self):
        logger.info('Connecting to {}:{} {} for mongodb'.format(
            os.getenv('MONGO_HOST', '127.0.0.1'),
            os.getenv('MONGO_PORT', 27017),
            os.getenv('MONGO_DATABASE', 'customers')
        ))

    @rpc
    def list(self):
        response = [CustomerSchema().dump(customer).data
                    for customer in Customer.objects]

        return response

    @rpc
    def get(self, id):
        """ Returns a customer based on the provided id"""
        customer = Customer.objects.get(id=id).select_related()
        return CustomerSchema().dumps(customer).data

    @rpc
    def create(self, payload):
        """
        Creates a new customer and payment method.

        Expects:
        {
            "name":<string>,
            "last_name":<string>,
            "street_1":<string>,
            "street_2":<string>,
            "city":<string>,
            "state":<string>,
            "zip_code":<string>,
            "email":<string>,
            "phone":<string>,
            <! optional !>
            "cardholder_name":<string>
            "card_number":<string>
            "card_type_id":<int>
            "security_number":<string>
            "alias":<string>
        }
        :param payload:
        :return:
        """
        customer = Customer()
        customer.name = payload["name"]
        customer.last_name = payload["last_name"]
        customer.street_1 = payload["street_1"]
        customer.street_2 = payload["street_2"]
        customer.state = payload["state"]
        customer.city = payload["city"]
        customer.zip_code = payload["zip_code"]
        customer.email = payload["email"]
        customer.phone = payload["phone"]

        customer.save(cascade=True)

        if payload['payment_method'] is not None:
            pay_method = PaymentMethod()

            payment_method = payload['payment_method']
            pay_method.cardholder_name = payment_method['cardholder_name']
            pay_method.card_number = payment_method['card_number']
            pay_method.card_type_id = payment_method['card_type_id']
            pay_method.security_number = payment_method['security_number']

            customer.payment_methods.append(pay_method)
            pay_method.customer = customer
            pay_method.save(cascade=True)

        customer = Customer.objects.get(id=customer.id).select_related(1)

        return CustomerSchema().dumps(customer).data

    @rpc
    def add_payment_method(self, payload):
        """ Creates a new payment method for the customer specified in the
        payload's customer_id key

        expects:
        {
            "customer_id":,
            "cardholder_name":,
            "expiration":,
            "card_number":,
            "security_number":,
            "card_type_id":,
            "alias":,

        }
        """
        customer = Customer.objects(id=payload['customer_id']).first()

        if customer is None:
            raise NotFound()

        pay_method = PaymentMethod()
        pay_method.cardholder_name = payload['cardholder_name']
        pay_method.card_number = payload['card_number']
        pay_method.card_type_id = payload['card_type_id']
        pay_method.security_number = payload['security_number']
        pay_method.alias = payload['alias']
        pay_method.expiration = payload['expiration']

        pay_method.customer = customer
        customer.payment_methods.append(pay_method)
        pay_method.save(cascade=True)

        return PaymentMethodSchema().dumps(pay_method).data

    @rpc
    def get_payment_method_by_customer_id(self, customer_id):
        """
        Returns the payment methods for the customer_id provided
        :param customer_id:
        :return:
        """

        payments = PaymentMethod.objects(customer=customer_id)

        results = [PaymentMethodSchema().dump(payment).data
                   for payment in payments]

        return results

    @event_handler('orders_service', 'verify_customer_payment')
    def handle_customer_and_payment_verification(self, payload):
        """ this event handler will add a payment method for a customer if the
        provided values do not match any existing payment method assigned to the customer"""
        customer_id = payload['customer_id']

        customer = Customer.objects(id=customer_id).get()

        if customer is None:
            raise NotFound()

        existing_payment = None

        payment_methods = PaymentMethod.objects(customer=customer_id)

        for payment in payment_methods:
            if payment.is_equal_to(payload['card_type_id', 'card_number', 'expiration']):
                existing_payment = payment
                break

        if existing_payment is not None:
            self.fire_event('payment_method', PaymentMethodSchema().dumps(existing_payment).data)

        payment = self.add_payment_method(payload)

        self.fire_event('cust_and_pay_method_verified', PaymentMethodSchema().dumps(payment).data)
