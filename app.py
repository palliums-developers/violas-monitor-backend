import time
from flask import Flask
from scan_thread import ScanThread
from check_thread import CheckThread

app = Flask(__name__)
scan_thread = ScanThread()

@app.route('/')
def index():
    return scan_thread.to_json()

if __name__ == "__main__":
    scan_thread.setDaemon(True)
    scan_thread.start()
    # while True:
    #     if scan_thread.status == scan_thread.UP_TO_DATE:
    #         check_thread = CheckThread()
    #         check_thread.setDaemon(True)
    #         check_thread.start()
    #         break
    #     time.sleep(1)
    app.run(host="0.0.0.0", port=8888)