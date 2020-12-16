import time
import json
import urllib3
from threading import Thread
from bank.bank import bank_api
from db.general import general_api
from violas_client import Client
from violas_client.lbrtypes.bytecode import CodeType
from const import URL
from util import set_default
from oracle.oracle import oracle_api

class ScanThread(Thread):

    KEEP_HEIGHT = 10000
    BACKWARD = 0
    UP_TO_DATE = 1

    def __init__(self):
        super().__init__()
        self.height = 0
        self.client = Client.new(URL)
        self.status = self.BACKWARD

    def to_json(self):
        bank_ret = json.dumps(bank_api, default=set_default)
        bank_ret = json.loads(bank_ret)
        bank_ret["height"] = self.height

        oracle_ret = json.dumps(oracle_api, default=set_default)
        oracle_ret = json.loads(oracle_ret)
        ret = bank_ret
        ret.update(oracle_ret)

        return ret

    def run(self) -> None:
        self.init_from_db()
        height = self.height
        while True:
            try:
                txs = self.client.get_transactions(self.height, 500)
                for tx in txs:
                    if tx.get_code_type() != CodeType.BLOCK_METADATA:
                        bank_api.add_tx(tx)
                        oracle_api.add_tx(tx)
                self.height += len(txs)
                if self.height > height + self.KEEP_HEIGHT:
                    height = self.height
                    bank_api.update_to_db()
                    oracle_api.update_to_db()
                    general_api.set_key("height", self.height)
                if self.status == self.BACKWARD and len(txs) < 500:
                    self.status = self.UP_TO_DATE
            except urllib3.exceptions.ReadTimeoutError as e:
                print("timeout")
                time.sleep(0.5)

            # time.sleep(1)

    def init_from_db(self):
        bank_api.update_from_db()
        oracle_api.update_from_db()
        height = general_api.get_key("height")
        self.height = height or 0
