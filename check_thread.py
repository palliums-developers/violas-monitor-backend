import time
import traceback
from threading import Thread
from violas_client import Client

from const import URL
from bank.bank import bank_api

class CheckThread(Thread):
    INTERVAL = 60

    def __init__(self):
        super().__init__()
        self.client = Client.new(URL)

    def run(self):
        while True:
            time.sleep(self.INTERVAL)
            try:
                token_infos = self.client.get_account_state(self.client.get_bank_owner_address()).get_token_info_store_resource(accrue_interest=False).tokens
                currencies = self.client.bank_get_registered_currencies(True)
                for currency in currencies:
                    index = self.client.bank_get_currency_index(currency_code=currency)
                    currency_info = token_infos[index: index+2]
                    self.assert_token_consistence(currency, currency_info)
            except Exception as e:
                print("monitor_thread", traceback.print_exc())

    @staticmethod
    def assert_token_consistence(currency, token_infos):
        local_info = bank_api.get_token_info(currency)
        assert token_infos[1].total_supply == local_info.total_supply
        assert token_infos[0].total_reserves == local_info.total_reserves
        assert token_infos[0].total_borrows == local_info.total_borrows
        assert token_infos[0].borrow_index == local_info.borrow_index
        assert token_infos[0].price == local_info.price
        assert token_infos[0].collateral_factor == local_info.collateral_factor
        assert token_infos[0].base_rate == local_info.base_rate
        assert token_infos[0].rate_multiplier == local_info.rate_multiplier
        assert token_infos[0].rate_jump_multiplier == local_info.rate_jump_multiplier
        assert token_infos[0].rate_kink == local_info.rate_kink
        assert token_infos[0].last_minute == local_info.last_minute
