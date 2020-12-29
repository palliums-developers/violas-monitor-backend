import json
from db.base import Base
from .price_recode import PriceRecords
from violas_client.oracle_client.bytecodes import CodeType

class OracleAPI(Base):
    PREFIX = "oracle_"
    def __init__(self):
        super().__init__()
        self.price_recodes = {}

    def add_tx(self, tx):
        if not tx.is_successful():
            return

        code_type = tx.get_code_type()
        if code_type == CodeType.UPDATE_EXCHANGE_RATE:
            return self.update_exchange_rate(tx)

    def update_exchange_rate(self, tx):
        price = tx.get_oracle_event().get_value()
        currency_code = tx.get_currency_code()
        t = tx.get_oracle_time()
        if price is not None:
            return self.set_price(currency_code, price, t)

    def set_price(self, currency_code, price, t):
        price_codes = self.price_recodes.get(currency_code)
        if price_codes is None:
            price_codes = PriceRecords()
        price_codes.set_price(price, t)
        self.price_recodes[currency_code] = price_codes

    def get_price(self, currency_code):
        return self.price_recodes.get(currency_code)

    def update_to_db(self):
        value = dict()
        for currency, value in self.price_recodes.items():
            value[currency] = value
        self.keep("currency", value)

    def update_from_db(self):
        value = self.get("currency", {})
        for currency, recode in value.items():
            self.price_recodes[currency] = PriceRecords.from_json(recode)


oracle_api = OracleAPI()