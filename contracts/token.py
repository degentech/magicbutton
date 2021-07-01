import smartpy as sp
import os

ACCURACY = 1_000_000_000_000_000

ZERO_ADDRESS = "tz1burnburnburnburnburnburnburjAYjjX"
LIQ_KT = sp.address(os.environ.get('LIQ_KT') or ZERO_ADDRESS)
BAKER_VALIDATOR_KT = sp.address(os.environ.get('BAKER_VALIDATOR_KT') or ZERO_ADDRESS)
STAKING_DURATION = int(os.environ.get('STAKING_DURATION') or 1278)
BET_PAYOUT = sp.nat(int(os.environ.get('BET_PAYOUT') or 1_000_000))
MAG_TICKET_COST = sp.nat(int(os.environ.get('MAG_TICKET_COST') or 10_000_000))
XTZ_TICKET_COST = sp.nat(int(os.environ.get('XTZ_TICKET_COST') or 100_000))
STAKE_LEVEL0 = sp.nat(int(os.environ.get('STAKE_LEVEL0') or 25_000_000))
STAKE_LEVEL1 = sp.nat(int(os.environ.get('STAKE_LEVEL1') or 100_000_000))
STAKE_LEVEL2 = sp.nat(int(os.environ.get('STAKE_LEVEL2') or 1000_000_000))
STAKE_LEVEL3 = sp.nat(int(os.environ.get('STAKE_LEVEL3') or 2000_000_000))
STAKE_LEVEL4 = sp.nat(int(os.environ.get('STAKE_LEVEL4') or 5000_000_000))
TOTAL_GAME_SUPPLY = sp.nat(int(os.environ.get('TOTAL_GAME_SUPPLY') or 10_000_000_000_000))
# TOTAL_SUPPLY = sp.nat(int(os.environ.get('TOTAL_SUPPLY') or 20_000_000_000_000))
ADMIN = sp.address(os.environ.get('ADMIN') or "tz1burnburnburnburnburnburnburjAYjjX")
FINISH_TIME = sp.now.add_hours(int(os.environ.get('FINISH_TIME') or 100))


accountParams = sp.TRecord(
    balance = sp.TNat, # token balance
    approvals = sp.TMap(sp.TAddress, sp.TNat), # approved addresses
    frozenBalance = sp.TNat, # frozen balance for staking
    rewardDebt = sp.TNat, # rewardPerToken price at the time of the last reward
    reward = sp.TNat, # reward that are due to the user
    usedVotes = sp.TNat, # used user votes
)

class FA12_core(sp.Contract):
    def __init__(self, **extra_storage):
        contract_metadata = sp.big_map(
            l = {
                "": sp.utils.bytes_of_string('tezos-storage:data'),
                "data": sp.utils.bytes_of_string(
                    """{
                        "name": "MAG Token",
                        "description": "FA1.2 MAG Token Contract",
                        "authors": ["DegenTech"],
                        "homepage": "none",
                        "interfaces": ["TZIP-7","TZIP-16","TZIP-21"]
                    }"""
                )
            },
          tkey = sp.TString,
          tvalue = sp.TBytes
        )

        token_metadata = sp.big_map(
            l = {
                0: sp.record(
                    token_id = 0,
                    token_info = sp.map(
                        l = {
                            "name": sp.utils.bytes_of_string('MAG Token'),
                            "decimals": sp.utils.bytes_of_string('6'),
                            "symbol": sp.utils.bytes_of_string('MAG'),
                            "thumbnailUri": sp.utils.bytes_of_string('ipfs://QmRGzetwTheMudNFfTAXqfiTbvcN4ZAhAzgUCBSMM43CbY')
                        },
                        tkey = sp.TString,
                        tvalue = sp.TBytes
                    )
                )
            },
            tkey = sp.TNat,
            tvalue = sp.TRecord(token_id = sp.TNat, token_info = sp.TMap(sp.TString, sp.TBytes))
        )
        self.init(
            admin = ADMIN, # admin account
            ledger = sp.big_map( # map for storing accounts
                tvalue = accountParams # account parameters
            ),
            metadata = contract_metadata, # general metadata
            token_metadata = token_metadata, # metadata for token
            votes = sp.map(tkey=sp.TKeyHash, tvalue=sp.TNat), # candidats and votes
            candidates = sp.map(tkey=sp.TAddress, tvalue=sp.TKeyHash), # user and choosen candidate
            currentBaker = sp.key_hash(ZERO_ADDRESS), # current baker selected by users
            secondNextBaker = sp.key_hash(ZERO_ADDRESS), # second current baker (comes second in votes)
            bestUser = sp.address(ZERO_ADDRESS), # current leader of the game
            lastWinner = sp.address(ZERO_ADDRESS), # last winner in the game (initially zero address)
            finishTime = sp.timestamp(0), # game end time
            totalPot = sp.nat(0), # game bank
            lastPot = sp.nat(0), # last game reward paid
            totalIssued = sp.nat(0), # sum of dividends for all time
            dividends = sp.nat(0), # staker rewards
            piggyBank = sp.nat(0), # pool for voting opportunities
            rewardPerToken = sp.nat(0), # amount of reward equal to one staked token
            totalStaked = sp.nat(0), # total number of tokens in the stake
            usedSupply = sp.nat(0), # amount of minted tokens
            usedLiqSupply = sp.nat(0), # amount of minted tokens by liquidity
            maxGameSupply = TOTAL_GAME_SUPPLY, # total number of possible mint for game
            liqAddress = LIQ_KT, # liquidity contract address
            bakerValidatorContract = BAKER_VALIDATOR_KT, # baker validator contract address
            totalSupply = sp.nat(0),
            piggyBankBreakTime = sp.timestamp_from_utc_now().add_days(STAKING_DURATION), # time after which the staking pool turns into dividends
            **extra_storage
        )

    @sp.entry_point
    def transfer(self, params):
        sp.set_type(params, sp.TRecord(from_ = sp.TAddress, to_ = sp.TAddress, value = sp.TNat).layout(("from_ as from", ("to_ as to", "value"))))
        sp.verify((params.from_ == sp.sender) | (self.data.ledger[params.from_].approvals[sp.sender] >= params.value))
        self.addAddressIfNecessary(params.to_)
        self.data.ledger[params.from_].balance = sp.as_nat(self.data.ledger[params.from_].balance - params.value)
        self.data.ledger[params.to_].balance += params.value

        sp.if params.from_ != sp.sender:
            self.data.ledger[params.from_].approvals[sp.sender] = sp.as_nat(self.data.ledger[params.from_].approvals[sp.sender] - params.value)

    @sp.entry_point
    def approve(self, params):
        sp.set_type(params, sp.TRecord(spender = sp.TAddress, value = sp.TNat).layout(("spender", "value")))
        alreadyApproved = sp.local("alreadyApproved", self.data.ledger[sp.sender].approvals.get(params.spender, 0))
        sp.verify((alreadyApproved.value == 0) | (params.value == 0), "UnsafeAllowanceChange")
        self.data.ledger[sp.sender].approvals[params.spender] = params.value

    def addAddressIfNecessary(self, address):
        sp.if ~ self.data.ledger.contains(address):
            self.data.ledger[address] = sp.record(
                balance = 0,
                approvals = {},
                frozenBalance = 0,
                rewardDebt = sp.nat(0),
                reward = sp.nat(0),
                usedVotes = 0,
            )

    @sp.utils.view(sp.TNat)
    def getBalance(self, params):
        sp.if self.data.ledger.contains(params):
            sp.result(self.data.ledger[params].balance)
        sp.else:
            sp.result(sp.nat(0))

    @sp.utils.view(sp.TNat)
    def getAllowance(self, params):
        sp.if self.data.ledger.contains(params.owner):
            sp.result(self.data.ledger[params.owner].approvals.get(params.spender, 0))
        sp.else:
            sp.result(sp.nat(0))

    @sp.utils.view(sp.TNat)
    def getTotalSupply(self, params):
        sp.set_type(params, sp.TUnit)
        sp.result(self.data.totalSupply)

    def mintTokens(self, address: sp.TAddress, value: sp.TNat):
        self.addAddressIfNecessary(address)
        self.data.ledger[address].balance += value
        self.data.usedSupply += value
        self.data.totalSupply += value

    def burnTokens(self, address: sp.TAddress, value: sp.TNat):
        balance = sp.local("balance", self.data.ledger[address].balance)
        sp.verify(balance.value >= value)
        self.data.ledger[address].balance = sp.as_nat(balance.value - value)
        self.data.totalSupply = sp.as_nat(self.data.totalSupply - value)

    @sp.entry_point
    def bet(self):
        self.checkFinish()
        amountInNat = sp.local("amountInNat", sp.fst(sp.ediv(sp.amount, sp.mutez(1)).open_some()))

        sp.if amountInNat.value == sp.nat(0):
            sp.verify((self.data.ledger[sp.sender].balance >= MAG_TICKET_COST), message="Wrong token amount")
            self.burnTokens(sp.sender, MAG_TICKET_COST)
            self.data.bestUser = sp.sender
            self.addTime()

        sp.else:
            sp.verify((amountInNat.value == XTZ_TICKET_COST), message="Wrong tezos amount")

            sp.if self.data.usedSupply + BET_PAYOUT <= self.data.maxGameSupply:
                self.mintTokens(sp.sender, BET_PAYOUT)
            self.data.bestUser = sp.sender


            tenPercent = sp.local("tenPercent", amountInNat.value / sp.as_nat(10))
            self.data.totalPot += sp.as_nat(amountInNat.value - (tenPercent.value + tenPercent.value))

            sp.if self.data.piggyBankBreakTime < sp.now:
                self.updatePools(tenPercent.value + tenPercent.value)
                self.addTime()

            sp.else:
                sp.if self.data.totalStaked == sp.nat(0):
                    self.data.piggyBank += tenPercent.value + tenPercent.value
                    self.data.rewardPerToken = sp.nat(0)
                sp.else:
                    self.data.dividends += tenPercent.value
                    self.data.piggyBank += tenPercent.value
                    self.data.totalIssued += tenPercent.value
                    self.data.rewardPerToken += tenPercent.value * ACCURACY / self.data.totalStaked
                self.addTime()

    def checkFinish(self):
        sp.if self.data.finishTime < sp.now:
            sp.if self.data.totalPot > sp.nat(0):
                sp.send(self.data.bestUser, sp.utils.nat_to_mutez(self.data.totalPot))
                self.data.lastPot = self.data.totalPot
                self.data.totalPot = sp.nat(0)
                self.data.lastWinner = self.data.bestUser
            self.data.finishTime = FINISH_TIME


    def updatePools(self, amount):
        sp.if self.data.totalStaked == sp.nat(0):
            self.data.totalPot += amount
            self.data.rewardPerToken = sp.nat(0)
            self.data.piggyBank = sp.nat(0)
        sp.else:
            self.data.dividends += self.data.piggyBank + amount
            self.data.totalIssued += self.data.piggyBank + amount
            self.data.rewardPerToken += (self.data.piggyBank + amount) * ACCURACY / self.data.totalStaked
            self.data.piggyBank = sp.nat(0)

    def addTime(self):
        sp.if self.data.finishTime <= sp.now.add_hours(1):
            sp.if (self.data.totalPot > STAKE_LEVEL0) & (self.data.totalPot <= STAKE_LEVEL1):
                self.data.finishTime = sp.now.add_hours(1)

        sp.if self.data.finishTime <= sp.now.add_minutes(45):
            sp.if (self.data.totalPot > STAKE_LEVEL1) & (self.data.totalPot <= STAKE_LEVEL2):
                self.data.finishTime = sp.now.add_minutes(45)

        sp.if self.data.finishTime <= sp.now.add_minutes(30):
            sp.if (self.data.totalPot > STAKE_LEVEL2) & (self.data.totalPot <= STAKE_LEVEL3):
                self.data.finishTime = sp.now.add_minutes(30)

        sp.if self.data.finishTime <= sp.now.add_minutes(15):
            sp.if (self.data.totalPot > STAKE_LEVEL3) & (self.data.totalPot <= STAKE_LEVEL4):
                self.data.finishTime = sp.now.add_minutes(15)

        sp.if self.data.finishTime <= sp.now.add_minutes(5):
            sp.if self.data.totalPot > STAKE_LEVEL4:
                self.data.finishTime = sp.now.add_minutes(5)

    def updReward(self, address: sp.TAddress):
        reward = sp.local("reward",self.data.ledger[address].reward)
        reward.value += self.data.rewardPerToken * self.data.ledger[address].frozenBalance
        reward.value = sp.as_nat(reward.value - self.data.ledger[address].rewardDebt)
        realReward = sp.local("realReward", reward.value / ACCURACY)

        sp.if realReward.value > sp.nat(0):
            self.data.dividends = sp.as_nat(self.data.dividends - realReward.value)
            sp.send(address, sp.utils.nat_to_mutez(realReward.value))

        self.data.ledger[address].reward = sp.as_nat(reward.value - (realReward.value * ACCURACY))
        self.data.ledger[address].rewardDebt = self.data.rewardPerToken * self.data.ledger[address].frozenBalance

    @sp.entry_point
    def stake(self, params):
        sp.set_type(params, sp.TRecord(value = sp.TNat))

        self.addAddressIfNecessary(sp.sender)
        self.updReward(sp.sender)

        sp.if params.value > sp.nat(0):
            balance = sp.local("balance", self.data.ledger[sp.sender].balance)
            sp.verify(balance.value >= params.value, "Wrong value")
            self.data.ledger[sp.sender].balance = sp.as_nat(balance.value - params.value)
            self.data.ledger[sp.sender].frozenBalance += params.value
            self.data.ledger[sp.sender].rewardDebt = self.data.rewardPerToken * self.data.ledger[sp.sender].frozenBalance
            self.data.totalStaked += params.value

    @sp.entry_point
    def unstake(self, params):
        sp.set_type(params, sp.TRecord(value = sp.TNat))

        self.updReward(sp.sender)

        sp.if params.value > sp.nat(0):
            userData = sp.local("userData", self.data.ledger[sp.sender])
            sp.verify(userData.value.frozenBalance >= params.value, "Wrong value")

            userData.value.frozenBalance = sp.as_nat(userData.value.frozenBalance - params.value)
            userData.value.balance += params.value
            userData.value.rewardDebt = self.data.rewardPerToken * userData.value.frozenBalance
            self.data.totalStaked = sp.as_nat(self.data.totalStaked - params.value)
            self.data.ledger[sp.sender] = userData.value
            sp.if self.data.candidates.contains(sp.sender):
                sp.if userData.value.frozenBalance == sp.nat(0):
                    self.unvoteInternal()
                sp.else:
                    sp.if userData.value.usedVotes != sp.nat(0):
                        self.voteInternal(self.data.candidates[sp.sender])

    @sp.entry_point
    def setLiqAddress(self, params):
        sp.set_type(params, sp.TRecord(address = sp.TAddress))

        sp.verify(sp.sender == self.data.admin, "Not Admin")
        self.data.liqAddress = params.address

    @sp.entry_point
    def setBakerValidatorContract(self, params):
        sp.set_type(params, sp.TRecord(address = sp.TAddress))

        sp.verify(sp.sender == self.data.admin, "Not Admin")
        self.data.bakerValidatorContract = params.address

    @sp.entry_point
    def changeAdmin(self, address: sp.TAddress):
        sp.verify(sp.sender == self.data.admin, "Not Admin")
        self.data.admin = address

    @sp.entry_point
    def mint(self, params):
        sp.set_type(params, sp.TRecord(address = sp.TAddress, value = sp.TNat))

        sp.verify(sp.sender == self.data.liqAddress, "Wrong contract address")
        self.addAddressIfNecessary(params.address)
        self.data.ledger[params.address].balance += params.value
        self.data.usedLiqSupply += params.value

    @sp.entry_point
    def unvote(self):
        self.unvoteInternal()

    def checkSecondBaker(self):
        sp.if self.data.votes.contains(self.data.secondNextBaker):
            sp.if self.data.votes[self.data.secondNextBaker] > self.data.votes[self.data.currentBaker]:
                pastCurrent = sp.local("pastCurrent", self.data.currentBaker)
                self.data.currentBaker = self.data.secondNextBaker
                sp.set_delegate(sp.some(self.data.currentBaker))
                self.data.secondNextBaker = pastCurrent.value

    def unvoteInternal(self):
        userLedger = sp.local("userLedger", self.data.ledger[sp.sender])
        usersCandidate = sp.local("usersCandidate",sp.key_hash(ZERO_ADDRESS))

        sp.if self.data.candidates.contains(sp.sender):
            usersCandidate.value = self.data.candidates[sp.sender]
            self.data.votes[usersCandidate.value] = sp.as_nat(self.data.votes[usersCandidate.value] - userLedger.value.usedVotes)

        userLedger.value.usedVotes = 0
        self.data.ledger[sp.sender] = userLedger.value

        sp.if usersCandidate.value == self.data.currentBaker:
            self.checkSecondBaker()

    @sp.entry_point
    def vote(self, candidate: sp.TKeyHash):
        self.voteInternal(candidate)

    def voteInternal(self, candidate: sp.TKeyHash):
        userLedger = sp.local("userLedger", self.data.ledger[sp.sender])

        sp.verify(candidate != sp.key_hash(ZERO_ADDRESS), message="Wrong candidate")
        sp.verify(userLedger.value.frozenBalance != sp.nat(0), message="You havent staked amount")

        bakerValidatorData = sp.contract(
            sp.TKeyHash,
            self.data.bakerValidatorContract,
            entry_point = "validateNewBaker"
        ).open_some("WrongInterface")

        sp.transfer(
            candidate,
            sp.mutez(0),
            bakerValidatorData
        )
        ## if the user is voices - remove old voices
        sp.if self.data.candidates.contains(sp.sender):
            self.data.votes[self.data.candidates[sp.sender]] = sp.as_nat(self.data.votes[self.data.candidates[sp.sender]] - userLedger.value.usedVotes)
        ## if the candidate already exists, add votes
        sp.if self.data.votes.contains(candidate):
            self.data.votes[candidate] += userLedger.value.frozenBalance

        ## if the candidate does not exist, assign votes
        sp.else:
            self.data.votes[candidate] = userLedger.value.frozenBalance

        self.data.candidates[sp.sender] = candidate ## refresh (or add new) user choose
        userLedger.value.usedVotes = userLedger.value.frozenBalance ## refresh (or add new) used user votes
        self.data.ledger[sp.sender] = userLedger.value

        sp.if self.data.votes.contains(self.data.currentBaker):
            sp.if self.data.votes[self.data.currentBaker] != self.data.votes[candidate]:
                sp.if self.data.votes[self.data.currentBaker] < self.data.votes[candidate]:
                        self.data.secondNextBaker = self.data.currentBaker
                        self.data.currentBaker = candidate
                        sp.set_delegate(sp.some(candidate))
                sp.else:
                    sp.if self.data.votes.contains(self.data.secondNextBaker):
                        sp.if self.data.votes[self.data.secondNextBaker] < self.data.votes[candidate]:
                            self.data.secondNextBaker = candidate
                    sp.else:
                        self.data.secondNextBaker = candidate
            sp.else:
                self.checkSecondBaker()

        sp.else:
            self.data.currentBaker = candidate
            sp.set_delegate(sp.some(candidate))



    @sp.entry_point
    def default(self):
        amountInNatural = sp.local("amountInNatural", sp.fst(sp.ediv(sp.amount, sp.mutez(1)).open_some()))
        sp.if sp.sender == self.data.liqAddress:
            sp.if self.data.piggyBankBreakTime < sp.now:
                self.updatePools(amountInNatural.value)
            sp.else:
                self.data.piggyBank += amountInNatural.value

        sp.else:
            sp.if self.data.piggyBankBreakTime < sp.now:
                self.updatePools(amountInNatural.value)

            sp.else:
                sp.if self.data.totalStaked == sp.nat(0):
                    self.data.rewardPerToken = sp.nat(0)
                    self.data.piggyBank += amountInNatural.value

                sp.else:
                    self.data.dividends += amountInNatural.value
                    self.data.totalIssued += amountInNatural.value
                    self.data.rewardPerToken += amountInNatural.value * ACCURACY / self.data.totalStaked

if __name__ == "__main__":
    sp.add_compilation_target("FA12_core", FA12_core())

