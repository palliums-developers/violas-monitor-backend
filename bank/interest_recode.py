class InterestRecords():
    ONE_DAY = 24*60*60

    def __init__(self):
        self.records = {}

    def update_total_borrow(self, total_borrow, borrow_rate, t):
        start_time = str(t // self.ONE_DAY)
        value = self.records.get(start_time)
        if value is None:
            tb = self.get_start_total_borrow(total_borrow, borrow_rate, int(start_time)*self.ONE_DAY, t)
            self.records = {start_time: [tb, 0]}

    def add_borrow(self, amount, t):
        start_time = str(t // self.ONE_DAY)
        self.records[start_time][1] += amount

    def add_repay_borrow(self, amount, t):
        start_time = str(t // self.ONE_DAY)
        self.records[start_time][1] -= amount

    def get_interest(self, total_borrow, borrow_rate, t):
        start_time = str(t // self.ONE_DAY)
        value = self.records.get(start_time)
        if value is None:
            if len(self.records):
                key = list(self.records.keys())[0]
                if int(key) > int(start_time):
                    return None
                start_amount = self.get_start_total_borrow(total_borrow, borrow_rate, int(start_time)*self.ONE_DAY, t)
                return total_borrow - start_amount
            else:
                return None
        start_amount, borrow_amount = self.records.get(start_time)
        return total_borrow - start_amount - borrow_amount

    @staticmethod
    def get_start_total_borrow(end_total_borrow, borrow_rate, start_time, end_time):
        return max(end_total_borrow - int((end_time-start_time) / 60) * borrow_rate, 0)


