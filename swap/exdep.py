import math

class Exdep():
    factor1 = 9997
    factor2 = 10000

    @classmethod
    def get_amount_out(cls, amount_in, reserve_in, reserve_out):
        amount_in_with_fee = amount_in * cls.factor1
        numerator = amount_in_with_fee * reserve_out
        denominator = reserve_in * cls.factor2 + amount_in_with_fee
        amount_in * cls.factor1 * reserve_out / (reserve_in * cls.factor2 + amount_in_with_fee)
        return int(numerator / denominator)

    @staticmethod
    def get_mint_liquidity(amounta_desired, amountb_desired, reservea, reserveb, total_supply):
        if reservea == 0 and reserveb == 0:
            amounta, amountb = amounta_desired, amountb_desired
        else:
            amountb_optimal = Exdep.quote(amounta_desired, reservea, reserveb)
            if amountb_optimal <= amountb_desired:
                amounta, amountb = amounta_desired, amountb_optimal
            else:
                amounta_optimal = Exdep.quote(amountb_desired, reserveb, reservea)
                amounta, amountb = amounta_optimal, amountb_desired
        if total_supply == 0:
            liquidity = math.sqrt(amounta * amountb)
        else:
            liquidity = min(amounta * total_supply / reservea, amountb * total_supply / reserveb)
        return liquidity, amounta, amountb

    @staticmethod
    def get_fee(amount_in, reserve_in, reserve_out):
        return int(amount_in * reserve_out // (reserve_in + amount_in))

    @staticmethod
    def quote(amounta, reservea, reserveb):
        return int(amounta * reserveb /reservea)


