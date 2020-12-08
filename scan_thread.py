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

class ScanThread(Thread):

    KEEP_HEIGHT = 10000

    def __init__(self):
        super().__init__()
        self.height = 0
        self.client = Client.new(URL)

    def to_json(self):
        ret = json.dumps(bank_api, default=set_default)
        ret = json.loads(ret)
        ret["height"] = self.height
        return ret

    def run(self) -> None:
        self.init_from_db()
        height = self.height
        while True:
            try:
                txs = self.client.get_transactions(height, 500)
                for tx in txs:
                    if tx.get_code_type() != CodeType.BLOCK_METADATA:
                        bank_api.add_tx(tx)
                self.height += len(txs)
                if self.height > height + self.KEEP_HEIGHT:
                    height = self.height
                    bank_api.update_to_db()
                    general_api.set_key("height", self.height)
            except urllib3.exceptions.ReadTimeoutError as e:
                print("timeout")
                time.sleep(0.5)

            # time.sleep(1)

    def init_from_db(self):
        bank_api.update_from_db()
        height = general_api.get_key("height")
        self.height = height or 0
