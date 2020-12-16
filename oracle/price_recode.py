
class PriceRecodes():
    ONE_DAY = 24*60*60

    def __init__(self):
        self.recodes = {}

    def set_price(self, price, t):
        start_time = str(t // self.ONE_DAY)
        value = self.recodes.get(start_time)
        if value is None:
            self.recodes = {start_time: [price, price]}
        else:
            value[1] = price

    @classmethod
    def from_json(cls, value):
        ret = cls()
        ret.recodes = value
        return ret

