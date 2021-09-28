import logging
from typing import TYPE_CHECKING

from django.core.exceptions import ValidationError
from requests.models import HTTPError

from saleor.plugins.base_plugin import BasePlugin, ConfigurationTypeField
from saleor.plugins.error_codes import PluginErrorCode
from .sipag_api import test_connection, ApiConfig

from ..utils import get_supported_currencies, require_active_plugin
from . import (
    GatewayConfig,
    capture,
    process_payment,
    refund, get_client_token,
)

GATEWAY_NAME = "Sipag"

if TYPE_CHECKING:
    from ...interface import GatewayResponse, PaymentData, TokenConfig

logger = logging.getLogger(__name__)


class SispagGatewayPlugin(BasePlugin):
    PLUGIN_ID = "tomaagoraeseu.payments.sipag"
    PLUGIN_NAME = GATEWAY_NAME
    DEFAULT_ACTIVE = False
    DEFAULT_CONFIGURATION = [
        {"name": "client_certificate", "value": None},
        {"name": "client_key", "value": None},
        {"name": "user_id", "value": None},
        {"name": "user_password", "value": None},
        {"name": "use_sandbox", "value": True},
        {"name": "automatic_payment_capture", "value": True},
        {"name": "supported_currencies", "value": "BRL"},
    ]
    CONFIG_STRUCTURE = {
        "client_certificate": {
            "type": ConfigurationTypeField.SECRET_MULTILINE,
            "help_text": "Defines the CA certificate to be authenticate the requests "
                         "to the payment system.",
            "label": "Client certificate",
        },
        "client_key": {
            "type": ConfigurationTypeField.SECRET_MULTILINE,
            "help_text": "Defines the client key to be authenticate the requests to "
                         "the payment system.",
            "label": "Client key",
        },
        "user_id": {
            "type": ConfigurationTypeField.STRING,
            "help_text": "Determines the User ID to authenticate requests to the "
                         "payment system.",
            "label": "User ID",
        },
        "user_password": {
            "type": ConfigurationTypeField.SECRET,
            "help_text": "Determines the User password to authenticate requests to "
                         "the payment system.",
            "label": "User password",
        },
        "automatic_payment_capture": {
            "type": ConfigurationTypeField.BOOLEAN,
            "help_text": "Determines if Saleor should automatically capture payments.",
            "label": "Automatic payment capture",
        },
        "supported_currencies": {
            "type": ConfigurationTypeField.STRING,
            "help_text": "Determines currencies supported by gateway."
                         " Please enter currency codes separated by a comma.",
            "label": "Supported currencies",
        },
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        configuration = {item["name"]: item["value"] for item in self.configuration}
        self.config = GatewayConfig(
            gateway_name=GATEWAY_NAME,
            auto_capture=configuration.get("automatic_payment_capture", None),
            supported_currencies=configuration.get("supported_currencies", None),
            connection_params={
                "client_certificate": configuration.get("client_certificate", None),
                "client_key": configuration.get("client_key", None),
                "user_id": configuration.get("user_id", None),
                "user_password": configuration.get("user_password", None),
                "use_sandbox": configuration.get("use_sandbox", None),
            },
        )

    def _get_gateway_config(self):
        return self.config

    @classmethod
    def _build_errors(cls, message: str, code, fields):
        errors = {}
        for field in fields:
            errors[field] = ValidationError(
                message,
                code=code,
            )
        return errors

    @classmethod
    def validate_plugin_configuration(cls, plugin_configuration: "PluginConfiguration"):
        """
        Validate if provided configuration is correct.
        """
        configuration = plugin_configuration.configuration
        configuration = {item["name"]: item["value"] for item in configuration}
        required_fields = ["client_certificate",
                           "client_key",
                           "user_id",
                           "user_password"]

        if not plugin_configuration.active:
            return

        all_required_fields_provided = all(
            [configuration.get(field) for field in required_fields]
        )

        if not all_required_fields_provided:
            raise ValidationError(
                cls._build_errors("The parameter is required.",
                                  code=PluginErrorCode.REQUIRED,
                                  fields=required_fields))

        client_certificate = configuration.get('client_certificate', None)
        client_key = configuration.get('client_key', None)
        user_id = configuration.get('user_id', None)
        user_password = configuration.get('user_password', None)
        use_sandbox = configuration.get('use_sandbox', False)

        try:
            test_connection(
                ApiConfig(
                    client_cert=client_certificate,
                    client_pkey=client_key,
                    user_id=user_id,
                    user_pw=user_password,
                    use_sandbox=use_sandbox
                ))
        except HTTPError:
            raise ValidationError(
                cls._build_errors("The parameter is invalid.",
                                  code=PluginErrorCode.INVALID,
                                  fields=required_fields))

    #
    # @require_active_plugin
    # def authorize_payment(
    #         self, payment_information: "PaymentData", previous_value
    # ) -> "GatewayResponse":
    #     return authorize(payment_information, self._get_gateway_config())

    @require_active_plugin
    def capture_payment(
            self, payment_information: "PaymentData", previous_value
    ) -> "GatewayResponse":
        return capture(payment_information, self._get_gateway_config())

    # @require_active_plugin
    # def confirm_payment(
    #         self, payment_information: "PaymentData", previous_value
    # ) -> "GatewayResponse":
    #     return confirm(payment_information, self._get_gateway_config())

    @require_active_plugin
    def process_payment(
            self, payment_information: "PaymentData", previous_value
    ) -> "GatewayResponse":
        return process_payment(payment_information, self._get_gateway_config())

    @require_active_plugin
    def refund_payment(
            self, payment_information: "PaymentData", previous_value
    ) -> "GatewayResponse":
        return refund(payment_information, self._get_gateway_config())

    # @require_active_plugin
    # def void_payment(
    #         self, payment_information: "PaymentData", previous_value
    # ) -> "GatewayResponse":
    #     return void(payment_information, self._get_gateway_config())

    @require_active_plugin
    def get_client_token(self, token_config: "TokenConfig", previous_value):
        return get_client_token()

    @require_active_plugin
    def get_supported_currencies(self, previous_value):
        config = self._get_gateway_config()
        return get_supported_currencies(config, GATEWAY_NAME)

    @require_active_plugin
    def get_payment_config(self, previous_value):
        config = self._get_gateway_config()
        return [{"field": "store_customer_card", "value": config.store_customer}]
