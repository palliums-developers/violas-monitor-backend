import json

from .exdep import Exdep
from .volume import Volumes

class RegisteredCurrencies():
    def __init__(self, currency_codes=None):
        self.currency_codes = currency_codes or list()

class Token():
    def __init__(self, index, value):
        self.index = index
        self.value = value

    def __repr__(self):
        return str(self.__dict__)

class Reserve():
    def __init__(self, coina, coinb, liquidity_total_supply=None):
        self.liquidity_total_supply = liquidity_total_supply or 0
        self.coina = coina
        self.coinb = coinb

    def __repr__(self):
        return str(self.__dict__)

class Exchange():
    def __init__(self):
        self.reserves = list()
        self.currency_codes = list()
        #币种的24小时交易量
        self.trading_recodes = dict()
        #交易对的gas_fee
        self.fees = dict()
        self.oracle_prices = dict()

    def add_currency(self, tx):
        currency_code = tx.get_currency_code()
        if currency_code in self.currency_codes:
            return
        self.currency_codes.append(currency_code)
        self.trading_recodes[currency_code] = Volumes()

    def add_liquidity(self, tx):
        script = tx.get_script()
        coina, coinb = script.type_arguments
        amounta_desired, amountb_desired = script.arguments[0], script.arguments[1]
        ida, idb = self.get_pair_indexes(coina, coinb)
        reserve = self.get_reserve_internal(ida, idb)
        total_supply, reservea, reserveb = reserve.liquidity_total_supply, reserve.coina.value, reserve.coinb.value

        total_supply, amounta, amountb = self.mint(amounta_desired, amountb_desired, reservea, reserveb, total_supply)
        reserve.liquidity_total_supply = total_supply
        reserve.coina.value = reservea + amounta
        reserve.coinb.value = reserveb + amountb

    def remove_liquidity(self, tx):
        script = tx.get_script()
        coina, coinb = script.type_arguments
        liquidity = script.arguments[0]

        ida, idb = self.get_pair_indexes(coina, coinb)
        reserve = self.get_reserve_internal(ida, idb)
        total_supply, reservea, reserveb = reserve.liquidity_total_supply, reserve.coina.value, reserve.coinb.value

        amounta = int(liquidity*reservea / total_supply)
        amountb = int(liquidity*reserveb / total_supply)
        reserve.liquidity_total_supply = total_supply - liquidity
        reserve.coina.value = reservea - amounta
        reserve.coinb.value = reserveb - amountb

    def swap(self, tx):
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
                amount_out = Exdep.get_amount_out(amt_in, reserve_in, reserve_out)
                amounts.append(amount_out)
                key = self.get_key(coin_in, coin_out)
                fee = Exdep.get_fee(amt_in, reserve_in, reserve_out) * self.oracle_prices.get(coin_out)
                self.fees.get(key).increase_value(fee, timestamp)
                reserve.coina.value += amt_in
                self.trading_recodes.get(coin_in).increase_value(amt_in, timestamp)
                reserve.coinb.value -= amount_out
                self.trading_recodes.get(coin_out).increase_value(amount_out, timestamp)
            else:
                reserve = self.get_reserve_internal(id_out, id_in)
                reserve_in, reserve_out = reserve.coinb.value, reserve.coina.value
                amount_out = Exdep.get_amount_out(amt_in, reserve_in, reserve_out)
                amounts.append(amount_out)
                key = self.get_key(coin_out, coin_in)
                fee = Exdep.get_fee(amt_in, reserve_in, reserve_out)
                self.fees.get(key).increase_value(fee, timestamp)
                reserve.coina.value -= amount_out
                self.trading_recodes.get(coin_out).increase_value(amount_out, timestamp)
                reserve.coinb.value += amt_in
                self.trading_recodes.get(coin_in).increase_value(amt_in, timestamp)
            i += 1

    def update_reserves_to_db(self):
        if len(self.reserves) == 0:
            return
        values = ''
        for reserve in self.reserves:
            coina = self.get_coin_name(reserve.coina.index)
            coinb = self.get_coin_name(reserve.coinb.index)
            key = self.get_key(coina, coinb)
            values += f'''('{key}', '{json.dumps(reserve.__dict__)}'),'''
        values = values[:-1]

        sql = f'''
        INSERT INTO monitor (key, value) VALUES {values} ON CONFLICT (key) DO UPDATE
        SET value=excluded.value;
        '''
        self.execute(sql)

    def update_interval_lock_to_db(self):
        values = f"('interval_lock', '{json.dumps({self.interval_lock})}')"
        sql = f'''
        INSERT INTO monitor (key, value) VALUES {values} ON CONFLICT (key) DO UPDATE
        SET value=exclude.value
        '''
        self.execute(sql)

    def update_interval_borrow_to_db(self):
        values = f"('interval_borrow', '{json.dumps({self.interval_borrow})}')"
        sql = f'''
        INSERT INTO monitor (key, value) VALUES {values} ON CONFLICT (key) DO UPDATE
        SET value=exclude.value
        '''
        self.execute(sql)

    def update_to_db(self):
        self.update_token_to_db()
        self.update_interval_borrow_to_db()
        self.update_interval_lock_to_db()

    def update_from_db(self):
        sql = "SELECT * FROM monitor"
        values = self.query(sql)
        for key, value in values.items():
            if key == "interval_lock":
                self.interval_lock = value
            elif key == "interval_borrow":
                self.interval_borrow = value
            else:
                self.token_infos[key] = value

    '''...............................internal.................................'''

    def get_coin_id(self, currency_code):
        for index, code in enumerate(self.currency_codes):
            if code == currency_code:
                return index

    def get_pair_id(self, coina, coinb):
        return self.get_coin_id(coina), self.get_coin_id(coinb)

    def get_pair_indexes(self, coina, coinb):
        return self.get_coin_id(coina), self.get_coin_id(coinb)

    def get_reserve_internal(self, ida, idb):
        for reserve in self.reserves:
            if reserve.coina.index == ida and reserve.coinb.index == idb:
                return reserve
        reserve = Reserve(Token(ida, 0), Token(idb, 0))
        self.reserves.append(reserve)
        return reserve

    def get_key(self, coina, coinb):
        return coina + "_" + coinb

    def get_coin_name(self, id):
        return self.currency_codes[id]

    def mint(self, amounta_desired, amountb_desired, reservea, reserveb, total_supply):
        return Exdep.get_mint_liquidity(amounta_desired, amountb_desired, reservea, reserveb, total_supply)



