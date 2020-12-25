from dataclasses import dataclass
from violas_client.extypes.bytecode import CodeType

from db.base import Base


@dataclass
class UserInfo:
    amount: int
    reward_debt: int

@dataclass
class PoolUserInfo:
    pool_id: int
    user_info: UserInfo

@dataclass
class PoolInfo:
    id: int
    lp_supply: int
    alloc_point: int
    acc_vls_per_share: int

@dataclass
class RewardPools:
    start_time: int
    end_time: int
    last_reward_time: int
    total_reward_balance: int
    total_alloc_point: int
    pool_infos: list

@dataclass
class Token:
    index: int
    value: int

@dataclass
class Reserve:
    liquidity_total_supply: int
    coina: Token
    coinb: Token

class ExchangeAPI(Base):
    def __init__(self):
        # {currency_code: price}
        self.oracle_prices = dict()
        # 手续费{pair_name: Volumes}
        self.fees = dict()
        # 交易量{currency: Volumes}
        self.currency_trading_recodes = dict()
        # 交易量{pair_name: Volumes}
        self.pair_trading_recodes = dict()

    def add_tx(self, tx):
        code_type = tx.get_code_type()
        if code_type == CodeType.INITIALIZE:
            return self.add_initialize(tx)
        elif code_type == CodeType.ADD_CURRENCY:
            pass
        elif code_type == CodeType.SWAP:
            pass
        elif code_type == CodeType.ADD_LIQUIDITY:
            pass
        elif code_type == CodeType.REMOVE_LIQUIDITY:
            pass
        elif code_type == CodeType.WITHDRAW_MINE_REWARD:
            pass

    def add_initialize(self, tx):
        t = tx.get_swap_timestamp()
        self.reward_pool = RewardPools(t, t, t, 0, 0, list())
        self.reserves = list()
        self.registered_currencies = list()
        self.factor1 = 9997
        self.factor2 = 10000

    def add_currency(self, tx):
        currency = tx.get_currency_code()
        self.registered_currencies.append(currency)

    def add_swap(self, tx):
        script = tx.get_script()
        args = script.get_args()
        path = args[3]
        length = len(path)
        amounts = list()
        amounts.append(script[1])

        i = 0
        timestamp = tx.get_bank_timestamp()
        while i < length-1:
            amt_in = amounts[i]
            id_in = path[i]
            id_out = path[i+1]
            coin_in = self.get_coin_name(id_in)
            coin_out = self.get_coin_name(id_out)
            if id_in < id_out:
                reserve = self.get_reserve_internal(id_in, id_out)
                reserve_in, reserve_out = reserve.coina.value, reserve.coinb.value
                amount_out = self.get_amount_out(amt_in, reserve_in, reserve_out)
                amounts.append(amount_out)
                reserve.coina.value += amt_in
                reserve.coinb.value -= amount_out

                pair_name = self.get_pair_name(coin_in, coin_out)
                fee = self.get_fee(amt_in, reserve_in, reserve_out) * self.oracle_prices.get(coin_out)
                self.fees.get(pair_name).increase_value(fee, timestamp)
                self.currency_trading_recodes.get(coin_in).increase_value(amt_in, timestamp)
                self.currency_trading_recodes.get(coin_out).increase_value(amount_out, timestamp)
                self.pair_trading_recodes.get(pair_name).increase_value(amt_in * self.oracle_prices.get(coin_in))
            else:
                reserve = self.get_reserve_internal(id_out, id_in)
                reserve_in, reserve_out = reserve.coinb.value, reserve.coina.value
                amount_out = self.get_amount_out(amt_in, reserve_in, reserve_out)
                amounts.append(amount_out)
                reserve.coina.value -= amount_out
                reserve.coinb.value += amt_in

                pair_name = self.get_pair_name(coin_out, coin_in)
                fee = self.get_fee(amt_in, reserve_in, reserve_out) * self.oracle_prices.get(coin_out)
                self.fees.get(pair_name).increase_value(fee, timestamp)
                self.currency_trading_recodes.get(coin_in).increase_value(amt_in, timestamp)
                self.currency_trading_recodes.get(coin_out).increase_value(amount_out, timestamp)
                self.pair_trading_recodes.get(pair_name).increase_value(amt_in * self.oracle_prices.get(coin_in))
            i += 1


    def add_liquidity(self, tx):
        pass

    def remove_liquidity(self, tx):
        pass

    def withdraw_mine_reward(self, tx):
        pass


    '''................................called by internal..........................'''

    def get_coin_name(self, id):
        return self.registered_currencies[id]

    def get_reserve_internal(self, ida, idb):
        for reserve in self.reserves:
            if reserve.coina.index == ida and reserve.coinb.index == idb:
                return reserve
        reserve = Reserve(Token(ida, 0), Token(idb, 0))
        self.reserves.append(reserve)
        return reserve

    def get_amount_out(self, amount_in, reserve_in, reserve_out):
        amount_in_with_fee = amount_in * self.factor1
        numerator = amount_in_with_fee * reserve_out
        denominator = reserve_in * self.factor2 + amount_in_with_fee
        return int(numerator / denominator)

    def get_pair_name(self, coina, coinb):
        return coina + "_" + coinb

    def get_output_amount_without_fee(self, amount_in, reserve_in, reserve_out):
        amount_out = amount_in * reserve_out // (reserve_in + amount_in)
        return amount_out

    def get_output_amount(self, amount_in, reserve_in, reserve_out):
        assert reserve_in > 0 and reserve_out > 0
        amount_inWithFee = amount_in * self.factor1
        numerator = amount_inWithFee * reserve_out
        denominator = reserve_in * self.factor2 + amount_inWithFee
        amount_out = numerator // denominator
        return amount_out

    def get_fee(self, amount_in, reserve_in, reserve_out):
        return self.get_output_amount_without_fee(amount_in, reserve_in, reserve_out) - self.get_output_amount(amount_in, reserve_in, reserve_out)
