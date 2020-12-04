import json
from .base import Base
from .token import TokenInfo
from .trading_recode import TradingRecords
from violas_client.banktypes.bytecode import CodeType as BankCodeType
from violas_client.vlstypes.view import TransactionView
from violas_client.oracle_client.bytecodes import CodeType as OracleCodType

class BankAPI(Base):

    def __init__(self):
        self.token_infos = dict()
        self.interval_lock = TradingRecords()
        self.interval_borrow = TradingRecords()
        self.accounts = set(list())

    def add_tx(self, tx: TransactionView):
        if not tx.is_successful():
            return

        code_type = tx.get_code_type()

        if code_type == BankCodeType.REGISTER_LIBRA_TOKEN:
            return self.add_register_libra_token(tx)
        elif code_type == BankCodeType.PUBLISH:
            return self.add_publish(tx)
        elif code_type in (BankCodeType.BORROW2, BankCodeType.BORROW):
            return self.add_borrow(tx)
        elif code_type in (BankCodeType.LOCK2, BankCodeType.LOCK, BankCodeType.LOCK_INDEX):
            return self.add_lock(tx)
        elif code_type in (BankCodeType.REDEEM2, BankCodeType.REDEEM):
            return self.add_redeem(tx)
        elif code_type in (BankCodeType.REPAY_BORROW, BankCodeType.REPAY_BORROW2, BankCodeType.REPAY_BORROW_INDEX):
            return self.add_repay_borrow(tx)
        elif code_type == BankCodeType.LIQUIDATE_BORROW:
            return self.add_liquidate_borrow(tx)
        elif code_type == BankCodeType.UPDATE_COLLATERAL_FACTOR:
            return self.update_collateral_factor(tx)
        elif code_type == BankCodeType.UPDATE_PRICE_FROM_ORACLE:
            return self.update_price_from_oracle(tx)
        elif code_type == BankCodeType.UPDATE_PRICE:
            return self.update_price(tx)
        elif code_type == OracleCodType.UPDATE_EXCHANGE_RATE:
            return self.update_oracle_price(tx)
        elif code_type == BankCodeType.UPDATE_RATE_MODEL:
            return self.update_rate_model(tx)

    def add_publish(self, tx):
        '''
        添加一个账户
        '''
        self.accounts.add(tx.get_sender())

    def add_register_libra_token(self, tx):
        events = tx.get_bank_type_events(BankCodeType.REGISTER_LIBRA_TOKEN)
        if len(events) > 0:
            event = events[0].get_bank_event()
            self.token_infos[event.currency_code] = TokenInfo(
                oracle_price=self.get_oracle_price(event.currency_code),
                currency_code=event.currency_code,
                collateral_factor=event.collateral_factor,
                base_rate=event.base_rate//(365*24*60),
                rate_multiplier=event.rate_multiplier//(365*24*60),
                rate_jump_multiplier=event.rate_jump_multiplier//(365*24*60),
                rate_kink=event.rate_kink,
                last_minute=events[0].get_timestamp())

    def add_borrow(self, tx):
        '''
        1. 更新oracle价格
        2. accrue_interest
        3. 更新账户的数据
            借款人账户的数据
        '''
        ret = []
        timestamps = tx.get_bank_timestamp()
        currency_code = tx.get_currency_code()
        token_info = self.get_token_info(currency_code)
        price = self.get_price(currency_code)
        oracle_price = self.get_oracle_price(currency_code)
        if price != oracle_price:
            self.set_price(currency_code, oracle_price)
        token_info.accrue_interest(timestamps)
        token_info.add_borrow(tx)
        amount = tx.get_amount()
        currency_code = tx.get_currency_code()
        price = self.get_price(currency_code)
        self.interval_borrow.increase_records(amount * price, timestamps)
        return ret

    def add_lock(self, tx):
        '''
        1. 更新oracle价格
        2. accrue_interest
        3. 更新账户数据
            存款人账户的数据
        4. 更新token_info
        '''
        ret = []
        timestamps = tx.get_bank_timestamp()
        currency_code = tx.get_currency_code()
        token_info = self.get_token_info(currency_code)
        price = self.get_price(currency_code)
        oracle_price = self.get_oracle_price(currency_code)
        if price != oracle_price:
            self.set_price(currency_code, oracle_price)
        token_info.accrue_interest(timestamps)
        token_info.update_exchange_rate()
        token_info.add_lock(tx)
        amount = tx.get_amount()
        currency_code = tx.get_currency_code()
        price = self.get_price(currency_code)
        self.interval_lock.increase_records(amount * price, timestamps)
        return ret

    def add_redeem(self, tx):
        '''
        1. 更新oralce价格
        2. accrue_interest
        3. 更新账户数据
            取款人的数据
        4. 更新token_info
        '''
        ret = []
        timestamps = tx.get_bank_timestamp()
        currency_code = tx.get_currency_code()
        token_info = self.get_token_info(currency_code)
        price = self.get_price(currency_code)
        oracle_price = self.get_oracle_price(currency_code)
        if price != oracle_price:
            self.set_price(currency_code, oracle_price)
        token_info.accrue_interest(timestamps)
        token_info.update_exchange_rate()
        token_info.add_redeem(tx)
        amount = tx.get_amount()
        currency_code = tx.get_currency_code()
        price = self.get_price(currency_code)
        self.interval_lock.reduce_records(amount * price, timestamps)
        return ret

    def add_repay_borrow(self, tx):
        '''
        1. 更新oralce价格
        2. accrue_interest
        3. 更新账户数据
            还款人的数据
        '''
        ret = []
        timestamps = tx.get_bank_timestamp()
        currency_code = tx.get_currency_code()
        token_info = self.get_token_info(currency_code)
        price = self.get_price(currency_code)
        oracle_price = self.get_oracle_price(currency_code)
        if price != oracle_price:
            self.set_price(currency_code, oracle_price)
        token_info.accrue_interest(timestamps)
        token_info.add_repay_borrow(tx)

        amount = tx.get_amount()
        currency_code = tx.get_currency_code()
        price = self.get_price(currency_code)
        self.interval_borrow.increase_records(amount * price, timestamps)

        return ret

    def add_liquidate_borrow(self, tx: TransactionView):
        '''
        1. 质押币总额不变
        2. 借款纵隔
        '''
        ret = []
        timestamps = tx.get_bank_timestamp()
        currency_code = tx.get_currency_code()
        collateral_currency = tx.get_collateral_currency()
        token_info = self.get_token_info(currency_code)
        price = self.get_price(currency_code)
        oracle_price = self.get_oracle_price(currency_code)
        if price != oracle_price:
            self.set_price(currency_code, oracle_price)
        collateral_price = self.get_price(collateral_currency)
        collateral_oracle_price = self.get_oracle_price(collateral_currency)
        if collateral_price != collateral_oracle_price:
            self.set_price(collateral_currency, collateral_oracle_price)
        token_info.accrue_interest(timestamps)
        token_info.add_liquidate_borrow(tx)

        amount = tx.get_amount()
        currency_code = tx.get_collateral_currency()
        price = self.get_price(currency_code)
        self.interval_borrow.reduce_records(amount * price, timestamps)

        return ret

    def update_collateral_factor(self, tx):
        '''
        1. 更新token_info
        2. 更新账户数据
            变大则更新有lock且有贷款的
        '''
        ret = []
        events = tx.get_bank_type_events(BankCodeType.UPDATE_COLLATERAL_FACTOR)
        event = events[0]
        factor = event.get_factor()
        currency_code = event.get_currency_code()
        token_info = self.get_token_info(currency_code)
        token_info.collateral_factor = factor
        return ret

    def update_price_from_oracle(self, tx):
        '''
        1. 更新本地价格
        2. 更新账户信息
        '''
        ret = []
        currency_code = tx.get_currency_code()
        price = self.get_price(currency_code)
        oracle_price = self.get_oracle_price(currency_code)
        if price != oracle_price:
            self.set_price(currency_code, oracle_price)
        return ret

    def update_price(self, tx):
        self.set_price(tx.get_currency_code(), tx.get_price())

    def update_oracle_price(self, tx):
        price = tx.get_oracle_event().get_value()
        if price is not None:
            return self.set_oracle_price(tx.get_currency_code(), price)

    def update_rate_model(self, tx: TransactionView):
        events = tx.get_bank_type_events(BankCodeType.UPDATE_RATE_MODEL)
        if len(events) > 0:
            event = events[0].get_bank_event()
            token_info = self.token_infos[event.currency_code]
            token_info.base_rate = event.base_rate //(365*24*60)
            token_info.rate_multiplier = event.rate_multiplier // (365*24*60)
            token_info.rate_jump_multiplier = event.rate_jump_multiplier // (365*24*60)
            token_info.rate_kink = event.rate_kink

    def update_token_to_db(self):
        if len(self.token_infos) == 0:
            return
        values = ''
        for token in self.token_infos:
            values += f'''('{token.currency_code}', '{json.dumps(token.__dict__)}'),'''
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

    def get_sum_of_borrows(self):
        sum = 0
        for token in self.token_infos:
            sum += token.get_total_borrow()*token.price()
        return sum

    def get_sum_of_locks(self):
        sum = 0
        for token in self.token_infos:
            sum += token.get_total_lock()
        return sum

    '''................................................................................................'''

    def get_price(self, currency_code):
        token_info = self.get_token_info(currency_code)
        if token_info:
            return token_info.price

    def set_price(self, currency_code, price):
        token_info = self.get_token_info(currency_code)
        if token_info and price != 0:
            token_info.price = price

    def get_oracle_price(self, currency_code):
        token_info = self.get_token_info(currency_code)
        if token_info:
            return token_info.oracle_price

    def set_oracle_price(self, currency_code, price):
        token_info = self.get_token_info(currency_code)
        if token_info:
            token_info.oracle_price = price
        else:
            token = TokenInfo(currency_code=currency_code, oracle_price=price)
            self.token_infos[currency_code] = token

    def get_token_info(self, currency_code):
        return self.token_infos.get(currency_code)
