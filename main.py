import json
from flask import Flask
from scan_thread import ScanThread
from bank.bank import bank_api
from violas_client import Client

# def set_default(obj):
#     if isinstance(obj, set):
#         return list(obj)
#     if type(obj) not in (list, dict, str, int, float, bool):
#         return obj.__dict__
#
# app = Flask(__name__)
# scan_thread = ScanThread()
#
# @app.route('/')
# def index():
#     return scan_thread.to_json()
#
# scan_thread.setDaemon(True)
# scan_thread.start()
# app.run(host="0.0.0.0", port=8888)

import time
print(time.time())





