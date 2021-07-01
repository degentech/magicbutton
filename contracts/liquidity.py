import os
import smartpy as sp

ACCURACY = 1_000_000_000_000_000
ZERO_ADDRESS = "tz1burnburnburnburnburnburnburjAYjjX"
ADMIN = sp.address(os.environ.get('ADMIN') or "tz1burnburnburnburnburnburnburjAYjjX")
TOKEN_ADDRESS = sp.address(os.environ.get('TOKEN_ADDRESS') or ZERO_ADDRESS)
TOTAL_STAKE_SUPPLY = sp.nat(int(os.environ.get('TOTAL_STAKE_SUPPLY') or 10_000_000_000_000))

account_params = sp.TRecord(
    balanceLiq = sp.TNat, # share pool token balance
    rewardDebtLiq = sp.TNat, # rewardPerToken price at the time of the last reward
    rewardChange = sp.TNat,
)

class Liquidity_core(sp.Contract):
    def __init__(self, **extra_storage):
        self.init(
            admin = ADMIN, # contract admin
            ledger = sp.big_map( # map for storing accounts
                tvalue = account_params # account parameters
            ),
            rewardPerSec = TOTAL_STAKE_SUPPLY * ACCURACY / sp.nat(365) / sp.nat(24) / sp.nat(60) / sp.nat(60), # formula reward per sec
            rewardUsed = sp.nat(0), # amount of used reward
            rewardsCap = TOTAL_STAKE_SUPPLY, # total number of possible rewards
            totalStaked = sp.nat(0), # total number of tokens in the stake
            rewardPerToken = sp.nat(0), # amount of reward equal to one staked token
            pause = sp.bool(False), # pause for payout of reward
            qAddress = sp.address(ZERO_ADDRESS),
            tokenAddress = sp.address(ZERO_ADDRESS),
            lastUpdateTime = sp.timestamp_from_utc_now(),
            **extra_storage
        )

    def updPoolLiq(self):
        sp.if self.data.pause == sp.bool(False):
            sp.if self.data.totalStaked == sp.nat(0):
                self.data.rewardPerToken = sp.nat(0)
            sp.else:
                periodReward = sp.local("periodReward",sp.as_nat(sp.now - self.data.lastUpdateTime) * self.data.rewardPerSec)
                availableReward = sp.local("availableReward", sp.as_nat(self.data.rewardsCap - self.data.rewardUsed) * ACCURACY)

                sp.if availableReward.value > sp.nat(0):
                    sp.if availableReward.value > periodReward.value:
                        self.data.rewardPerToken += periodReward.value / self.data.totalStaked
                    sp.else:
                        self.data.rewardPerToken += availableReward.value / self.data.totalStaked
            self.data.lastUpdateTime = sp.now

    def getRewardLiq(self, address: sp.TAddress):
        userData = sp.local("userData", self.data.ledger[address])
        rewardUsed = sp.local("rewardUsed", self.data.rewardUsed)
        userReward = sp.local("userReward", self.data.ledger[address].rewardChange)

        sp.if userData.value.balanceLiq > sp.nat(0):
            userReward.value += self.data.rewardPerToken * userData.value.balanceLiq
            userReward.value = sp.as_nat(userReward.value -  userData.value.rewardDebtLiq)
            realReward = sp.local("realReward", userReward.value / ACCURACY)

            sp.if realReward.value + rewardUsed.value > self.data.rewardsCap:
                realReward.value = sp.as_nat(self.data.rewardsCap - rewardUsed.value)

            sp.if realReward.value > sp.nat(0):
                balanceData = sp.contract(
                    sp.TRecord(address = sp.TAddress, value = sp.TNat),
                    address=self.data.tokenAddress,
                    entry_point="mint"
                ).open_some()

                sp.transfer(sp.record(
                    address=address, value=realReward.value),
                    sp.mutez(0),
                    balanceData
                )

                self.data.rewardUsed += realReward.value

            self.data.ledger[address].rewardChange = sp.as_nat(userReward.value - realReward.value * sp.nat(ACCURACY))
            userData.value.rewardDebtLiq = self.data.rewardPerToken * userData.value.balanceLiq
            self.data.ledger[address] = userData.value


    @sp.entry_point
    def stake(self, params):
        sp.set_type(params, sp.TRecord(value = sp.TNat)).layout(("value"))

        self.addAddressIfNecessary(sp.sender)

        self.updPoolLiq()
        self.getRewardLiq(sp.sender)

        sp.if self.data.pause == sp.bool(False):

            sp.if params.value > sp.nat(0):
                tokenContract = sp.contract(
                    sp.TRecord(from_=sp.TAddress,
                            to_=sp.TAddress,
                            value=sp.TNat).layout(("from_ as from", ("to_ as to", "value"))),
                    address=self.data.qAddress,
                    entry_point="transfer"
                ).open_some()

                sp.transfer(sp.record(from_=sp.sender,
                                    to_=sp.self_address,
                                    value=params.value),
                            sp.mutez(0),
                            tokenContract)

                self.data.ledger[sp.sender].balanceLiq += params.value
                self.data.ledger[sp.sender].rewardDebtLiq = self.data.rewardPerToken * self.data.ledger[sp.sender].balanceLiq
                self.data.totalStaked = self.data.totalStaked + params.value

    @sp.entry_point
    def unstake(self, params):
        sp.set_type(params, sp.TRecord(value = sp.TNat)).layout(("value"))

        self.updPoolLiq()
        self.getRewardLiq(sp.sender)

        sp.if params.value > sp.nat(0):
            sp.verify(self.data.ledger[sp.sender].balanceLiq >= params.value, "Wrong value")

            tokenContract = sp.contract(
                sp.TRecord(from_=sp.TAddress,
                        to_=sp.TAddress,
                        value=sp.TNat).layout(("from_ as from", ("to_ as to", "value"))),
                address=self.data.qAddress,
                entry_point="transfer"
            ).open_some()

            sp.transfer(sp.record(from_=sp.self_address,
                                to_=sp.sender,
                                value=params.value),
                        sp.mutez(0),
                        tokenContract)

            self.data.ledger[sp.sender].balanceLiq = sp.as_nat(self.data.ledger[sp.sender].balanceLiq - params.value)
            self.data.ledger[sp.sender].rewardDebtLiq = self.data.rewardPerToken * self.data.ledger[sp.sender].balanceLiq
            self.data.totalStaked = sp.as_nat(self.data.totalStaked - params.value)

    @sp.entry_point
    def setQAddress(self, params):
        sp.set_type(params, sp.TRecord(contractAddress = sp.TAddress))
        sp.verify(sp.sender == self.data.admin, "NotAdmin")
        self.data.qAddress = params.contractAddress

    @sp.entry_point
    def changeAdmin(self, address: sp.TAddress):
        sp.verify(sp.sender == self.data.admin, "NotAdmin")
        self.data.admin = address


    def addAddressIfNecessary(self, address):
        sp.if ~ self.data.ledger.contains(address):
            self.data.ledger[address] = sp.record(
                balanceLiq = sp.nat(0),
                rewardDebtLiq = sp.nat(0),
                rewardChange = sp.nat(0),
            )

    @sp.entry_point
    def default(self):
        sp.if sp.sender == self.data.qAddress:
            userTotal = sp.local("userTotal", sp.split_tokens(sp.amount, 3, 100))
            stakingTotal = sp.local("stakingTotal", sp.amount - userTotal.value)

            sp.send(self.data.tokenAddress, stakingTotal.value)
            sp.send(sp.source, userTotal.value)

        sp.else:
            sp.send(self.data.tokenAddress, sp.amount)

    @sp.entry_point
    def withdrawProfit(self):
        target = sp.contract(
            sp.TAddress,
            self.data.qAddress,
            entry_point = "withdrawProfit"
        ).open_some("WrongInterface")

        sp.transfer(
            sp.self_address,
            sp.mutez(0),
            target
        )

    @sp.entry_point
    def setPause(self):
        sp.verify(sp.sender == self.data.admin, "NotAdmin")
        self.updPoolLiq()
        self.data.pause = sp.bool(True)
        withdrawData = sp.self_entry_point("withdrawProfit")

        sp.transfer(
            sp.unit,
            sp.mutez(0),
            withdrawData
        )

if __name__ == "__main__":
    sp.add_compilation_target("Liquidity_core", Liquidity_core())
