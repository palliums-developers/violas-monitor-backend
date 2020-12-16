import copy
import time
from .trading_recode import TradingRecords
from .interest_recode import InterestRecords
from .util import new_mantissa, mantissa_mul, mantissa_div, safe_sub

class TokenInfo():
    def __init__(self, **kwargs):
        self.currency_code = kwargs.get("currency_code")
        self.total_supply = kwargs.get("total_supply", 0)
        self.total_reserves = kwargs.get("total_reserves", 0)
        self.total_borrows = kwargs.get("total_borrows", 0)
        self.borrow_index = kwargs.get("borrow_index", new_mantissa(1, 1))

        self.oracle_price = kwargs.get("oracle_price")
        self.price = kwargs.get("price", 0)

        self.collateral_factor = kwargs.get("collateral_factor", 0)
        self.base_rate = kwargs.get("base_rate", 0)
        self.rate_multiplier = kwargs.get("rate_multiplier",0)
        self.rate_jump_multiplier = kwargs.get("rate_jump_multiplier", 0)
        self.rate_kink = kwargs.get("rate_kink", 0)
        self.last_minute = kwargs.get("last_minute", 0)

        # resource struct T
        self.contract_value = kwargs.get("contract_value", 0)

        #24小时的存款总额
        self.interval_lock = TradingRecords()
        self.interval_lock.records = kwargs.get("interval_lock") or dict()

        self.interval_borrow = TradingRecords()
        self.interval_borrow.records = kwargs.get("interval_borrow") or dict()

        #24小时产生的利息(借款的存款的一样)
        self.interval_borrow_interest = InterestRecords()
        self.interval_borrow_interest.records = kwargs.get("interval_borrow_interest") or dict()

        self.lock_accounts = set(kwargs.get("lock_accounts", list()))
        self.borrow_accounts = set(kwargs.get("borrow_accounts", list()))

    def get_total_lock(self):
        return self.total_supply * self.get_exchange_rate()

    def get_total_borrow(self):
        return self.total_borrows

    def to_json(self):
        ret = {
            "currency_code": self.currency_code,
            "total_supply": self.total_supply,
            "total_reserves": self.total_reserves,
            "total_borrows": self.total_borrows,
            "borrow_index": self.borrow_index,
            "oracle_price": self.oracle_price,
            "price": self.price,
            "collateral_factor": self.collateral_factor,
            "base_rate": self.base_rate,
            "rate_multiplier": self.rate_multiplier,
            "rate_jump_multiplier": self.rate_jump_multiplier,
            "rate_kink": self.rate_kink,
            "last_minute": self.last_minute,
            "contract_value": self.contract_value,
            "interval_lock": self.interval_lock.records,
            "interval_borrow": self.interval_borrow.records,
            "interval_borrow_interest": self.interval_borrow_interest.records,
            "lock_accounts": list(self.lock_accounts),
            "borrow_accounts": list(self.borrow_accounts),
        }
        borrow_rate = self.get_borrow_rate()
        cur_time = int(time.time())
        ret["interest"] = self.interval_borrow_interest.get_interest(self.get_forecast(cur_time//60).total_borrows,
                                                                      borrow_rate, int(time.time())),
        return ret

    @classmethod
    def from_json(cls, json_value):
        return cls(**json_value)

    def accrue_interest(self, timestamp):
        borrow_rate = self.get_borrow_rate()
        minute = int(timestamp) // 60
        cnt = safe_sub(minute, self.last_minute)
        if cnt <= 0:
            return self
        borrow_rate = borrow_rate *cnt
        self.last_minute = minute
        interest_accumulated = mantissa_mul(self.total_borrows, borrow_rate)
        self.total_borrows = self.total_borrows + interest_accumulated
        reserve_factor = new_mantissa(1, 20)
        self.total_reserves = self.total_reserves +mantissa_mul(interest_accumulated, reserve_factor)
        self.borrow_index = self.borrow_index + mantissa_mul(self.borrow_index, borrow_rate)

        self.interval_borrow_interest.update_total_borrow(self.total_borrows, borrow_rate, timestamp)
        return self

    def get_forecast(self, time_minute):
        ret = copy.deepcopy(self)
        borrow_rate = ret.get_borrow_rate()
        minute = time_minute
        cnt = safe_sub(minute, ret.last_minute)
        if cnt <= 0:
            return ret
        borrow_rate = borrow_rate * cnt
        ret.last_minute = minute
        interest_accumulated = mantissa_mul(ret.total_borrows, borrow_rate)
        ret.total_borrows = ret.total_borrows + interest_accumulated
        reserve_factor = new_mantissa(1, 20)
        ret.total_reserves = ret.total_reserves + mantissa_mul(interest_accumulated, reserve_factor)
        ret.borrow_index = ret.borrow_index + mantissa_mul(ret.borrow_index, borrow_rate)
        return ret

    def get_borrow_rate(self):
        if self.total_borrows == 0:
            util = 0
        else:
            util = new_mantissa(self.total_borrows, self.total_borrows + safe_sub(self.contract_value, self.total_reserves))
        if util < self.rate_kink:
            return mantissa_mul(self.rate_multiplier, util) + self.base_rate
        normal_rate = mantissa_mul(self.rate_multiplier, self.rate_kink) + self.base_rate
        excess_util = util - self.rate_kink
        return mantissa_mul(self.rate_jump_multiplier, excess_util) + normal_rate

    def get_lock_rate(self):
        if self.total_borrows == 0:
            util = 0
        else:
            util = new_mantissa(self.total_borrows, self.total_borrows + safe_sub(self.contract_value, self.total_reserves))
        borrow_rate = self.get_borrow_rate()
        return mantissa_mul(util, mantissa_mul(borrow_rate, (new_mantissa(100, 100) - new_mantissa(1, 20))))

    def update_exchange_rate(self):
        if self.total_supply == 0:
            self.exchange_rate = new_mantissa(1, 100)
            return self.exchange_rate
        self.exchange_rate = new_mantissa(self.contract_value + self.total_borrows - self.total_reserves, self.total_supply)
        return self.exchange_rate

    def get_exchange_rate(self):
        return self.update_exchange_rate()

    def add_lock(self, tx):
        amount = tx.get_amount()
        self.contract_value += amount
        tokens = mantissa_div(amount, self.exchange_rate)
        self.total_supply += tokens

        tx_time = tx.get_bank_timestamp()
        self.interval_lock.increase_records(amount, tx_time)
        self.lock_accounts.add(tx.get_sender())

    def add_borrow(self, tx):
        amount = tx.get_amount()
        self.total_borrows += amount
        self.contract_value -= amount

        tx_time = tx.get_bank_timestamp()
        self.interval_borrow.increase_records(amount, tx_time)
        self.borrow_accounts.add(tx.get_sender())
        self.interval_borrow_interest.add_borrow(amount, tx_time)

    def add_redeem(self, tx):
        amount = tx.get_amount()
        tokens = mantissa_div(amount, self.exchange_rate)
        self.total_supply = safe_sub(self.total_supply, tokens)
        self.contract_value -= amount

        tx_time = tx.get_bank_timestamp()
        # self.interval_lock.reduce_records(amount, tx_time)

    def add_repay_borrow(self, tx):
        amount = tx.get_amount()
        self.total_borrows = safe_sub(self.total_borrows, amount)
        self.contract_value += amount

        tx_time = tx.get_bank_timestamp()
        # self.interval_borrow.reduce_records(amount, tx_time)

    def add_liquidate_borrow(self, tx):
        self.add_repay_borrow(tx)



