
class Volume():
    def __init__(self, interval):
        self.records = {}
        self.interval = interval

    def increase_value(self, value, t):
        start_time = t // self.interval
        bef = self.records.get(start_time, 0)
        self.records = {start_time: bef+value}

    def decrease_value(self, value, t):
        start_time = t // self.interval
        bef = self.records.get(start_time, 0)
        self.records = {start_time: bef - value}

    def set_value(self, value, t):
        self.records = {t: value}

class Volumes():
    ONE_DAY = 24*60*60

    def __init__(self):
        self.volumes = {
            self.ONE_DAY: Volume(self.ONE_DAY)
        }

    def increase_value(self, value, t):
        for volume in self.volumes.values():
            volume.increase_value(value, t)


    def decrease_value(self, value, t):
        for volume in self.volumes.values():
            volume.decrease_value(value, t)

    def __repr__(self):
        return str(self.__dict__)
