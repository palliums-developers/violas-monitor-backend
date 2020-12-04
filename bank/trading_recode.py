class TradingRecords():
    ONE_DAY = 24*60*60
    def __init__(self):
        self.records = {}

    def increase_records(self, amount, t):
        start_time = t // self.ONE_DAY
        value = self.records.get(start_time, 0)
        self.records = {start_time: amount+value}

    def reduce_records(self, amount, t):
        start_time = t // self.ONE_DAY
        value = self.records.get(start_time, 0)
        self.records = {start_time: value - amount}

    def get_record(self, t):
        start_time = t // self.ONE_DAY
        return self.records.get(start_time, 0)

    def __repr__(self):
        return str(self.__dict__)