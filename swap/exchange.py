from dataclasses import dataclass
from violas_client.extypes.bytecode import CodeType

import json
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
    start_time: int = 0
    end_time: int = 0
    last_reward_time: int = 0
    total_reward_balance: int = 0
    total_alloc_point: int = 0
    pool_infos: list = ()

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
    PREFIX = "swap_"

    def __init__(self):
        super().__init__()

        # {currency_code: price}
        self.oracle_prices = dict()
        # 手续费{pair_name: Volumes}
        self.fees = dict()
        # 交易量{currency: Volumes}
        self.currency_trading_recodes = dict()
        # 交易量{pair_name: Volumes}
        self.pair_trading_recodes = dict()
        #账户的token {addr: [Token]}
        self.account_tokens = dict()

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

    def update_to_db(self):
        self.keep("reward_pool", self.reward_pool)
        self.keep("reserves", self.reserves)
        self.keep("registered_currencies", self.registered_currencies)
        self.keep("factor", [self.factor1, self.factor2])

        self.keep("oracle_prices", self.oracle_prices)
        self.keep("fees", self.fees)
        self.keep("currency_trading_recodes", self.currency_trading_recodes)
        self.keep("pair_trading_recodes", self.pair_trading_recodes)
        self.keep("account_tokens", self.account_tokens)

    def update_from_db(self):
        value = self.get("reward_pool", {})
        self.reward_pool = RewardPools(**value)
        value = self.get("reserves", {})
        self.reserves = [Reserve(**reserve) for reserve in value]
        value = self.get("registered_currencies", [])
        self.registered_currencies = value
        value = self.get("factor", [0, 0])
        self.factor1, self.factor2 = value[0], value[1]
        value = self.get("oracle_price", {})
        self.oracle_prices = value
        value = self.get("fees", {})
        self.fees = value
        value = self.get("currency_trading_recodes", {})
        self.currency_trading_recodes = value
        value = self.get("pair_trading_recodes", {})
        self.pair_trading_recodes = value
        value = self.get("account_tokens", [])
        self.account_tokens = value

    def add_currency(self, tx):
        currency = tx.get_currency_code()
        self.registered_currencies.append(currency)

    def add_swap(self, tx):
        script = tx.get_script()
        args = script.arguments
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
        script = tx.get_script()
        type_args = script.type_arguments
        coina, coinb = type_args[0], type_args[1]
        args = script.arguments
        amounta_desired, amountb_desired, amounta_min, amountb_min = args
        ida, idb = self.get_pair_indexs(coina, coinb)
        reserve = self.get_reserve_internal(ida, idb)
        total_supply, reservea, reserveb = reserve.liquidity_total_supply, reserve.coina.value, reserve.coinb.value
        total_supply, amounta, amountb = self.mint(tx.get_sender(), ida, idb, amounta_desired, amountb_desired)
        reserve.liquidity_total_supply = total_supply
        reserve.coina.value = reservea + amounta
        reserve.coinb.value = reserve + amountb

    def remove_liquidity(self, tx):
        sender = tx.get_sender()
        script = tx.get_script()
        type_args = script.type_arguments
        coina, coinb = type_args[0], type_args[1]
        args = script.arguments
        liquidity, amounta_min, amountb_min = args
        ida, idb = self.get_pair_indexs(coina, coinb)
        reserve = self.get_reserve_internal(ida, idb)
        total_supply, reservea, reserveb = reserve.liquidity_total_supply, reserve.coina.value, reserve.coinb.value
        id = ida << 32 + idb
        token = self.get_token(id, sender)
        amounta = int(liquidity * reservea / total_supply)
        amountb = int(liquidity * reserveb / total_supply)
        reserve.liquidity_total_supply = total_supply - liquidity
        reserve.coina.value = reservea - amounta
        reserve.coinb.value = reserveb - amountb
        token.value -= liquidity
        self.update_pool()
        self.update_user_reward_info(sender, id, token.value)

    def withdraw_mine_reward(self, tx):
        pass


    '''................................called by internal..........................'''

    def get_coin_name(self, id):
        return self.registered_currencies[id]

    def get_coin_id(self, coin_name):
        for index, currency in enumerate(self.registered_currencies):
            if currency == coin_name:
                return index

    def get_pair_indexs(self, coina, coinb):
        return self.get_coin_id(coina), self.get_coin_id(coinb)

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

    def get_token(self, addr, id):
        tokens = self.account_tokens.get(addr, [])
        for token in tokens:
            if token.index == id:
                return token
        t = Token(id, 0)
        tokens.append(t)
        return t

    def get_fee(self, amount_in, reserve_in, reserve_out):
        return self.get_output_amount_without_fee(amount_in, reserve_in, reserve_out) - self.get_output_amount(amount_in, reserve_in, reserve_out)

    def quote(self, amounta, reservea, reserveb):
        return amounta * reserveb / reservea

    def sqrt(self, a, b):
        y = a * b
        z = 1
        if y > 3:
            z = y
            x = int(y // 2 + 1)
            while x < z:
                z = x
                x =(y // x + x) // 2
        elif y != 0:
            z = 1
        return int(z)

    def get_mint_liquidity(self, amounta_desired, amountb_desired, amounta_min, amountb_min, reservea, reserveb, total_supply):
        if reservea == 0 and reserveb == 0:
           amounta, amountb = amounta_desired, amountb_desired
        else:
            amountb_optimal = self.quote(amounta_desired, reservea, reserveb)
            if amountb_optimal <= amountb_desired:
                amounta, amountb = amounta_desired, amountb_optimal
            else:
                amounta_optimal = self.quote(amountb_desired, reserveb, reservea)
                amounta, amountb = amounta_optimal, amountb_desired
        if total_supply == 0:
            liquidity = self.sqrt(amounta, amountb)
        else:
            liquidity = min(amounta * total_supply / reservea, amountb * total_supply / reserveb)
        return liquidity, amounta, amountb

    def update_pool(self):
        pass

    def update_user_reward_info(self, addr, id, new_liquidity):
        pass

    def mint(self, addr, ida, idb, amounta_desired, amountb_desired, amounta_min, amountb_min, reservea, reserveb, total_supply):
        id = ida << 32 + idb
        token = self.get_token(addr, id)
        liquidity, amounta, amountb = self.get_mint_liquidity(amounta_desired, amountb_desired, amounta_min, amountb_min, reservea, reserveb, total_supply)
        token.value += liquidity
        self.update_pool()
        self.update_user_reward_info(addr, id, token.value)
        return total_supply + liquidity, amounta, amountb

exchange_api = ExchangeAPI()