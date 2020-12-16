import json
from db.base import Base
from .price_recode import PriceRecords
from violas_client.oracle_client.bytecodes import CodeType

class OracleAPI(Base):
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
        key = self.get_key(currency_code)
        price_codes = self.price_recodes.get(key)
        if price_codes is None:
            price_codes = PriceRecords()
        price_codes.set_price(price, t)
        self.price_recodes[currency_code] = price_codes

    def get_price(self, currency_code):
        key = self.get_key(currency_code)
        return self.price_recodes.get(key)

    def update_to_db(self):
        for currency, value in self.price_recodes.items():
            values = f"('oracle-{currency}', '{json.dumps(value.records)}')"
            sql = f'''
            INSERT INTO monitor (key, value) VALUES {values} ON CONFLICT (key) DO UPDATE
            SET value=excluded.value
            '''
            self.execute(sql)

    def update_from_db(self):
        sql = "SELECT * FROM monitor"
        values = self.query(sql)
        for key, value in values:
            if key.startswith("oracle"):
                self.price_recodes[key] = PriceRecords.from_json(value)

    def get_key(self, currency_code):
        return "oracle-" + currency_code

oracle_api = OracleAPI()