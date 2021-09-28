import logging.config
from decimal import Decimal
from enum import Enum

import zeep.exceptions
from requests import Session
from requests.auth import HTTPBasicAuth
from zeep import Client
from zeep.transports import Transport
from saleor.payment.gateways.sipag.utils import generate_cert_files

SANDBOX = 'https://test.ipg-online.com/ipgapi/services'
PRODUCTION = 'https://test.ipg-online.com/ipgapi/services'

logger = logging.getLogger(__name__)


def enable_soap_debug():
    logging.config.dictConfig({
        'version': 1,
        'formatters': {
            'verbose': {
                'format': '%(name)s: %(message)s'
            }
        },
        'handlers': {
            'console': {
                'level': 'DEBUG',
                'class': 'logging.StreamHandler',
                'formatter': 'verbose',
            },
        },
        'loggers': {
            'zeep.transports': {
                'level': 'DEBUG',
                'propagate': True,
                'handlers': ['console'],
            },
        }
    })


class ApiConfig:
    def __init__(self,
                 client_cert: str,
                 client_pkey: str,
                 user_id: str,
                 user_pw: str,
                 use_sandbox: bool):
        self.client_cert = client_cert
        self.client_pkey = client_pkey
        self.user_id = user_id
        self.user_pw = user_pw
        self.use_sandbox = use_sandbox


def test_connection(api_config: ApiConfig):
    _init_api(api_config)


def _init_api(api_config: ApiConfig) -> Client:
    api_url = PRODUCTION if api_config.use_sandbox else SANDBOX

    (client_cert_file, client_pkey_file) = generate_cert_files(
        client_cert=api_config.client_cert,
        client_pkey=api_config.client_pkey)

    session = Session()
    session.cert = (client_cert_file, client_pkey_file)
    session.auth = HTTPBasicAuth(api_config.user_id, api_config.user_pw)

    transport = Transport(session=session)

    client = Client(
        wsdl=f'{api_url}/order.wsdl',
        transport=transport,
    )

    return client


class SipagError(Exception):
    def __init__(self, message=None, code=None, raw_response_data=None):
        super(SipagError, self).__init__(message)
        self.code = code
        self.raw_response_data = raw_response_data


def _invoke_api(api_config: ApiConfig, message: dict):
    client = _init_api(api_config)

    logger.info(message)

    try:
        return client.service.IPGApiOrder(**message)
    except zeep.exceptions.Fault as fault:

        [response] = fault.detail.getchildren()

        raw_data = client.wsdl.types.deserialize(response)

        logger.error(raw_data)

        code = raw_data['ProcessorResponseCode']
        message = raw_data['ProcessorResponseMessage']

        raise SipagError(message, code=code, raw_response_data=raw_data)


# test_connection
# def do_void(token):
#     message = {
#         'Transaction': {
#             'CreditCardTxType': {
#                 'Type': 'void'
#             },
#             'TransactionDetails': {
#                 'OrderId': token,
#             },
#         }
#     }
#
#     response = invoke_sipag(message)
#
#     print(response)
#
#
# def do_return(token):
#     message = {
#         'Transaction': {
#             'CreditCardTxType': {
#                 'Type': 'return'
#             },
#             'Payment': {
#                 'SubTotal': 100,
#                 'DeliveryAmount': 10,
#                 'ChargeTotal': 110,
#                 'Currency': '986',  # ISO 4217
#                 'numberOfInstallments': 1,
#                 'installmentsInterest': 'no',  # or yes
#             },
#             'TransactionDetails': {
#                 'OrderId': token,
#             },
#         }
#     }
#
#     response = invoke_sipag(message)
#
#     print(response)
#
#
# def do_capture(token):
#     message = {
#         'Transaction': {
#             'CreditCardTxType': {
#                 'Type': 'postAuth'
#             },
#             'Payment': {
#                 'SubTotal': 100,
#                 'DeliveryAmount': 10,
#                 'ChargeTotal': 110,
#                 'Currency': '986',  # ISO 4217
#                 'numberOfInstallments': 1,
#                 'installmentsInterest': 'no',  # or yes
#             },
#             'TransactionDetails': {
#                 'OrderId': token,
#             },
#         }
#     }
#
#     response = invoke_sipag(message)
#
#     print(response)
#

class CreditCardTxTypes(Enum):
    PRE_AUTH = 'preAuth'
    POST_AUTH = 'postAuth'
    SALE = 'sale'
    VOID = 'void'
    RETURN = 'return'


class CardFunctions(Enum):
    CREDIT = 'credit'
    DEBIT = 'debit'


class CreditCardData:
    def __init__(self,
                 card_number: str,
                 exp_month: str,
                 exp_year: str,
                 card_code_value: str):
        self.card_number = card_number
        self.exp_moth = exp_month
        self.exp_year = exp_year
        self.card_code_value = card_code_value

    def to_xml_data(self):
        return {
            'CardNumber': self.card_number,
            'ExpMonth': self.exp_moth,
            'ExpYear': self.exp_year,
            'CardCodeValue': self.card_code_value,
        }


class Payment:
    def __init__(self,
                 currency: str,
                 charge_total: Decimal,
                 delivery_amount: Decimal = 0,
                 number_of_installments: int = 1,
                 sub_total: Decimal = None,
                 installments_interest: bool = False,
                 hosted_data_id: str = None):
        self.currency = currency
        self.sub_total = sub_total
        self.charge_total = charge_total
        self.delivery_amount = delivery_amount
        self.number_of_installments = number_of_installments
        self.installments_interest = installments_interest
        self.hosted_data_id = hosted_data_id

    @staticmethod
    def _convert_boolean_to_str(value: bool) -> str:
        return 'yes' if value else 'no'

    def to_xml_data(self) -> dict:
        data = {
            'DeliveryAmount': float(self.delivery_amount),
            'ChargeTotal': float(self.charge_total),
            'Currency': self.currency,
            'numberOfInstallments': self.number_of_installments,
            'installmentsInterest': self._convert_boolean_to_str(
                self.installments_interest),
            'HostedDataID': self.hosted_data_id,
        }

        if self.sub_total:
            data['SubTotal'] = float(self.sub_total)

        return data


class TransactionDetails(object):
    def __init__(self, merchant_transaction_id: str, ip: str = None,
                 order_id: str = None):
        self.merchant_transaction_id = merchant_transaction_id
        self.ip = ip
        self.order_id = order_id

    def to_xml_data(self) -> dict:
        data = {}

        if self.order_id:
            data['OrderId'] = self.order_id

        if self.merchant_transaction_id:
            data['MerchantTransactionId'] = self.merchant_transaction_id

        if self.ip:
            data['Ip'] = self.ip

        return data


class Address(object):
    def __init__(self,
                 name: str,
                 address_1: str,
                 address_2: str,
                 city: str,
                 state: str,
                 zip: str,
                 country: str,
                 phone: str = None):
        self.name = name
        self.address_1 = address_1
        self.address_2 = address_2
        self.city = city
        self.state = state
        self.zip = zip
        self.country = country
        self.phone = phone

    def to_xml_data(self) -> dict:
        data = {
            'Name': self.name,
            'Address1': self.address_1,
            'Address2': self.address_2,
            'City': self.city,
            'State': self.state,
            'Zip': self.zip,
            'Country': self.country,
        }

        if self.phone:
            data['Phone'] = self.phone

        return data


class BillingAddress(Address):
    def __init__(self,
                 name: str,
                 address_1: str,
                 address_2: str,
                 city: str,
                 state: str,
                 zip: str,
                 country: str,
                 phone: str = None,
                 email: str = None):
        super().__init__(name=name,
                         address_1=address_1,
                         address_2=address_2,
                         city=city,
                         state=state,
                         zip=zip,
                         country=country,
                         phone=phone)
        self.email = email

    def to_xml_data(self) -> dict:
        data = super().to_xml_data()

        if self.email:
            data['Email'] = self.email

        return data


class Request(object):
    def __init__(self,
                 credit_card_tx_type: CreditCardTxTypes,
                 card_function: CardFunctions,
                 payment: Payment,
                 transaction_details: TransactionDetails,
                 billing_address: BillingAddress,
                 shipping_address: Address,
                 credit_card_data: CreditCardData = None,
                 ):
        self.credit_card_tx_type = credit_card_tx_type
        self.credit_card_data = credit_card_data
        self.card_function = card_function
        self.payment = payment
        self.transaction_details = transaction_details
        self.billing_address = billing_address
        self.shipping_address = shipping_address

    def to_xml_data(self) -> dict:
        transaction = {
            'CreditCardTxType': {
                'Type': self.credit_card_tx_type.value
            },
            'cardFunction': self.card_function.value,
            'Payment': self.payment.to_xml_data(),
            'TransactionDetails': self.transaction_details.to_xml_data(),
            'Billing': self.billing_address.to_xml_data(),
            'Shipping': self.shipping_address.to_xml_data(),
        }

        if self.credit_card_data:
            transaction['CreditCardData'] = self.credit_card_data.to_xml_data()

        return {
            'Transaction': transaction,
        }


def api_request(api_config: ApiConfig, request: Request):
    response = _invoke_api(api_config, request.to_xml_data())

    return response
