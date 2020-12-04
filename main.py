import json
from flask import Flask
from threading import Thread

from bank.bank import BankAPI
from violas_client import Client

def set_default(obj):
    if isinstance(obj, set):
        return list(obj)
    if type(obj) not in (list, dict, str, int, float, bool):
        return obj.__dict__

app = Flask(__name__)

api = BankAPI()

start = 0

@app.route('/')
def index():
    ret = json.dumps(api, default=set_default)
    ret = json.loads(ret)
    ret["height"] = start
    return ret

def scan_thread():
    global start
    client = Client()
    while True:
        txs = client.get_transactions(start, 500)
        for tx in txs:
            api.add_tx(tx)
        start += 500

thread = Thread(target=scan_thread)

thread.setDaemon(True)
thread.start()
app.run(host="0.0.0.0", port=9000)







