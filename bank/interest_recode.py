class InterestRecords():
    ONE_DAY = 24*60*60

    def __init__(self):
        self.records = {}

    def update_total_borrow(self, total_borrow, t):
        start_time = str(t // self.ONE_DAY)
        value = self.records.get(start_time)
        print("update_total_borrow", value)
        if value is None:
            print("set", {start_time: total_borrow})
            self.records = {start_time: total_borrow}

    def add_borrow(self, amount, t):
        start_time = str(t // self.ONE_DAY)
        value = self.records.get(start_time)
        print("add borrow", value, amount)
        assert value is not None
        self.records[start_time] = value + amount

    def add_repay_borrow(self, amount, t):
        start_time = str(t // self.ONE_DAY)
        value = self.records.get(start_time)
        assert value is not None
        self.records[start_time] = value - amount

    def get_interest(self, total_borrow, t):
        start_time = str(t // self.ONE_DAY)
        value = self.records.get(start_time)
        if value is None:
            return 0
        return total_borrow - value

