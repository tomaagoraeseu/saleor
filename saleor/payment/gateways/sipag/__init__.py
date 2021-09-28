import uuid
import logging
import pycountry
from .sipag_api import Request, CreditCardData, CreditCardTxTypes, \
    CardFunctions, Payment, BillingAddress, Address, TransactionDetails, ApiConfig, \
    api_request, SipagError
from ... import TransactionKind
from ...interface import GatewayConfig, GatewayResponse, PaymentData, PaymentMethodInfo

logger = logging.getLogger(__name__)


def get_client_token(**_):
    token = str(uuid.uuid4())

    logger.info(f'get_client_token.....{token}')

    return token


#
# def authorize(
#         payment_information: PaymentData, config: GatewayConfig
# ) -> GatewayResponse:
#     logger.info(f'authorize....{payment_information}')
#
#     success = dummy_success()
#     error = None
#     if not success:
#         error = "Unable to authorize transaction"
#
#     return GatewayResponse(
#         is_success=success,
#         action_required=False,
#         kind=TransactionKind.AUTH,
#         amount=payment_information.amount,
#         currency=payment_information.currency,
#         transaction_id=payment_information.token or "",
#         error=error,
#         payment_method_info=PaymentMethodInfo(
#             last_4="1234",
#             exp_year=2222,
#             exp_month=12,
#             brand="dummy_visa",
#             name="Holder name",
#             type="card",
#         ),
#     )


# def void(payment_information: PaymentData, config: GatewayConfig) -> GatewayResponse:
#     logger.info(f'void....{payment_information}')
#
#     error = None
#     success = dummy_success()
#     if not success:
#         error = "Unable to void the transaction."
#     return GatewayResponse(
#         is_success=success,
#         action_required=False,
#         kind=TransactionKind.VOID,
#         amount=payment_information.amount,
#         currency=payment_information.currency,
#         transaction_id=payment_information.token or "",
#         error=error,
#     )


def capture(payment_information: PaymentData, config: GatewayConfig) -> GatewayResponse:
    logger.info(f'capture....{payment_information}')

    request = Request(
        credit_card_tx_type=CreditCardTxTypes.SALE,
        card_function=CardFunctions.CREDIT,
        payment=Payment(
            sub_total=payment_information.amount,
            charge_total=payment_information.amount,
            currency=get_currency_numeric_code(payment_information.currency),
            hosted_data_id=payment_information.token,
        ),
        billing_address=BillingAddress(
            name=f'{payment_information.billing.first_name} {payment_information.billing.last_name}',
            address_1=payment_information.billing.street_address_1,
            address_2=payment_information.billing.street_address_2,
            city=payment_information.billing.city,
            state=payment_information.billing.country_area,
            country=get_country_alpha_3(payment_information.billing.country),
            zip=payment_information.billing.postal_code,
            email=payment_information.customer_email,
        ),
        shipping_address=Address(
            name=f'{payment_information.shipping.first_name} {payment_information.shipping.last_name}',
            address_1=payment_information.shipping.street_address_1,
            address_2=payment_information.shipping.street_address_2,
            city=payment_information.shipping.city,
            state=payment_information.shipping.country_area,
            country=get_country_alpha_3(payment_information.shipping.country),
            zip=payment_information.shipping.postal_code,
        ),
        transaction_details=TransactionDetails(
            merchant_transaction_id=f'{payment_information.payment_id}',
            ip=payment_information.customer_ip_address,
        )
    )

    logger.info(f'request is....{request}')

    error = None
    brand = None

    try:
        response = api_request(api_config=create_app_config(config), request=request)
        brand = response['Brand'].lower()

        logger.info(f'response is....{response}')
    except SipagError as err:
        error = str(err)

    success = not error

    return GatewayResponse(
        is_success=success,
        action_required=False,
        kind=TransactionKind.CAPTURE,
        amount=payment_information.amount,
        currency=payment_information.currency,
        transaction_id=payment_information.token or "",
        error=error,
        payment_method_info=PaymentMethodInfo(
            brand=brand,
            type="card",
        ),
    )


#
# def confirm(payment_information: PaymentData, config: GatewayConfig) -> GatewayResponse:
#     logger.info(f'confirm....{payment_information}')
#
#     """Perform confirm transaction."""
#     error = None
#     success = dummy_success()
#     if not success:
#         error = "Unable to process capture"
#
#     return GatewayResponse(
#         is_success=success,
#         action_required=False,
#         kind=TransactionKind.CAPTURE,
#         amount=payment_information.amount,
#         currency=payment_information.currency,
#         transaction_id=payment_information.token or "",
#         error=error,
#     )


def refund(payment_information: PaymentData, config: GatewayConfig) -> GatewayResponse:
    logger.info(f'refund....{payment_information}')

    error = None
    success = True
    if not success:
        error = "Unable to process refund"
    return GatewayResponse(
        is_success=success,
        action_required=False,
        kind=TransactionKind.REFUND,
        amount=payment_information.amount,
        currency=payment_information.currency,
        transaction_id=payment_information.token or "",
        error=error,
    )


def get_country_alpha_3(alpha_2: str):
    # country = pycountry.countries.get(alpha_2=alpha_2)
    country = pycountry.countries.get(alpha_2='BR')
    return country.alpha_3


def get_currency_numeric_code(alpha_3: str):
    # currency = pycountry.currencies.get(alpha_3=alpha_3)
    currency = pycountry.currencies.get(alpha_3='BRL')
    return currency.numeric


def create_app_config(config: GatewayConfig):
    return ApiConfig(
        client_cert=config.connection_params.get('client_certificate'),
        client_pkey=config.connection_params.get('client_key'),
        user_id=config.connection_params.get('user_id'),
        user_pw=config.connection_params.get('user_password'),
        use_sandbox=config.connection_params.get('use_sandbox', True)
    )


def process_payment(
        payment_information: PaymentData, config: GatewayConfig
) -> GatewayResponse:
    logger.info(f'process_payment....{payment_information}....{config}')

    # if not config.auto_capture:
    #     return authorize(payment_information, config)

    return capture(payment_information, config)
