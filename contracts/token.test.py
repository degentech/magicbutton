import os
import smartpy as sp

os.environ['STAKE_LEVEL0'] = "1000000"
os.environ['STAKE_LEVEL1'] = "2000000"
os.environ['STAKE_LEVEL2'] = "3000000"
os.environ['STAKE_LEVEL3'] = "4000000"
os.environ['STAKE_LEVEL4'] = "5000000"
os.environ['TOTAL_GAME_SUPPLY'] = "66000000"
os.environ['ADMIN'] = "tz1burnburnburnburnburnburnburjAYjjX"

admin =  sp.test_account("Admin")
alice = sp.test_account("Alice")
bob = sp.test_account("Bob")
carol = sp.test_account("Carol")
devid = sp.test_account("Devid")

token = sp.io.import_script_from_url("file:contracts/token.py")
FA12_core = token.FA12_core
TICKET_COST = token.TICKET_COST
STAKE_LEVEL0 = token.STAKE_LEVEL0
STAKE_LEVEL1 = token.STAKE_LEVEL1

ONE_MAG = 1000000
ZERO_ADDRESS = "tz1burnburnburnburnburnburnburjAYjjX"
DEFAULT_VOTE = 0
DIVIDENDS_PART = 10000
REWARDS_PART = 80000
STAKING_DURATION = 1278

DEFAULT_LEDGER_RECORD = sp.record(
                balance = 0,
                approvals = {},
                frozenBalance = 0,
                rewardDebt = 0,
                reward = 0,
                usedVotes = 0,
            )

def successVoteCase(scenario, now, token, sender, candidate, addVote, delegate, secondCandidate, sameCandidate=False):
    # store prev state
    prevUserCandidate = scenario.compute(token.data.candidates.get(sender.address, sp.key_hash(ZERO_ADDRESS)))
    prevVotes = scenario.compute(token.data.votes.get(candidate, DEFAULT_VOTE))
    prevUserRecord = scenario.compute(token.data.ledger.get(sender.address, DEFAULT_LEDGER_RECORD))

    # vote
    if addVote:
        scenario += token.vote(candidate).run(
            sender = sender,
            now = now,
            voting_powers = {candidate : 10}
        )
    else:
        scenario += token.unvote().run(
            sender = sender,
            now = now,
            voting_powers = {candidate : 10}
        )

    # verify
    newUserCandidate = scenario.compute(token.data.candidates.get(sender.address, sp.key_hash(ZERO_ADDRESS)))
    newVotes = scenario.compute(token.data.votes.get(candidate, DEFAULT_VOTE))
    newUserRecord = scenario.compute(token.data.ledger.get(sender.address, DEFAULT_LEDGER_RECORD))    
    scenario.verify_equal(token.data.secondNextBaker, secondCandidate)
    scenario.verify_equal(token.data.currentBaker, delegate)
    if addVote:
        scenario.verify_equal(newUserCandidate, candidate)
        scenario.verify_equal(newUserRecord.usedVotes, prevUserRecord.frozenBalance)
        if sameCandidate:
            scenario.verify_equal(sp.as_nat(prevVotes - prevUserRecord.usedVotes) + prevUserRecord.frozenBalance, newVotes)
        else:
            scenario.verify_equal(prevVotes + prevUserRecord.frozenBalance, newVotes)
    else:
        scenario.show(newVotes)
        scenario.show(prevVotes)
        scenario.verify_equal(newUserCandidate, candidate)
        if sameCandidate:
            scenario.verify_equal(newVotes, sp.as_nat(prevVotes - prevUserRecord.frozenBalance))
        else:
            scenario.verify_equal(newVotes, sp.as_nat(prevVotes - prevUserRecord.frozenBalance))

def successDefaultCase(scenario, now, token, sender, amount):
    # store prev state
    prevDevidends = scenario.compute(token.data.dividends)
    prevStakingPool = scenario.compute(token.data.piggyBank)

    # vote
    scenario += token.default().run(
        sender = sender,
        now = now,
        amount = sp.mutez(amount)
    )

    # verify

    scenario.verify((token.data.liqAddress != sender.address) | (token.data.dividends == prevDevidends))
    scenario.verify((token.data.liqAddress != sender.address) | (token.data.piggyBank == prevStakingPool + amount))
    scenario.verify((token.data.liqAddress == sender.address) | (token.data.dividends == prevDevidends + amount))
    scenario.verify((token.data.liqAddress == sender.address) | (token.data.piggyBank ==  prevStakingPool))

def successBetCase(scenario, now, token, sender, magBet, newFinishTime, startNewRound=False, mintNewTokens=True):
    # store prev state
    prevUsedSupply = scenario.compute(token.data.usedSupply)
    prevDevidends = scenario.compute(token.data.dividends)
    prevStakingPool = scenario.compute(token.data.piggyBank)
    prevAliceRecord = scenario.compute(token.data.ledger.get(sender.address, DEFAULT_LEDGER_RECORD))
    prevRewardsPool = scenario.compute(token.data.totalPot)
    prevFinishTime = scenario.compute(token.data.finishTime)

    # bet
    if magBet:
        scenario += token.bet().run(
            sender = sender,
            now = now
        )
    else:
        scenario += token.bet().run(
            sender = sender,
            amount = sp.mutez(100000),
            now = now
        )

    # verify
    newAliceRecord = scenario.compute(token.data.ledger.get(sender.address, DEFAULT_LEDGER_RECORD))
    scenario.verify_equal(token.data.bestUser, sender.address)
    scenario.show(token.data.finishTime)
    scenario.show(newFinishTime)
    scenario.verify_equal(token.data.finishTime, newFinishTime)
    if magBet:
        scenario.verify_equal(token.data.totalPot, prevRewardsPool)
        scenario.verify_equal(newAliceRecord.balance, sp.as_nat(prevAliceRecord.balance - 10 * ONE_MAG))
        scenario.verify_equal(token.data.dividends, prevDevidends)
        scenario.verify_equal(token.data.piggyBank, prevStakingPool)
    else:
        # scenario.verify_equal(token.data.dividends, prevDevidends + DIVIDENDS_PART)
        # scenario.verify_equal(token.data.piggyBank, prevStakingPool + DIVIDENDS_PART)
        if mintNewTokens:
            scenario.verify_equal(token.data.usedSupply, prevUsedSupply + ONE_MAG)
            scenario.verify_equal(newAliceRecord.balance, prevAliceRecord.balance + ONE_MAG)
        else:
            scenario.verify_equal(token.data.usedSupply, prevUsedSupply)
            scenario.verify_equal(newAliceRecord.balance, prevAliceRecord.balance )
        if startNewRound:
            scenario.verify_equal(token.data.totalPot, REWARDS_PART)
        else:
            scenario.verify_equal(token.data.totalPot, prevRewardsPool + REWARDS_PART)

def successStakeCase(scenario, now, token, sender, value):
    # store prev state
    prevLpSupply = scenario.compute(token.data.totalStaked)
    prevDevidends = scenario.compute(token.data.dividends)
    prevStakingPool = scenario.compute(token.data.piggyBank)
    prevAliceRecord = scenario.compute(token.data.ledger.get(sender.address, DEFAULT_LEDGER_RECORD))

    # stake
    scenario += token.stake(value = value).run(
        sender = sender,
        now = now
    )

    # verify
    newAliceRecord = scenario.compute(token.data.ledger.get(sender.address, DEFAULT_LEDGER_RECORD))
    scenario.verify_equal(token.data.totalStaked, prevLpSupply  + value)
    scenario.verify_equal(newAliceRecord.balance, sp.as_nat(prevAliceRecord.balance - value))
    scenario.verify_equal(newAliceRecord.frozenBalance, prevAliceRecord.frozenBalance + value)
    scenario.verify_equal(newAliceRecord.rewardDebt, token.data.rewardPerToken * newAliceRecord.frozenBalance)
    scenario.verify_equal(token.data.totalStaked, prevLpSupply  + value)
    
def successUnstakeCase(scenario, now, token, sender, value):
    # store prev state
    prevLpSupply = scenario.compute(token.data.totalStaked)
    prevDevidends = scenario.compute(token.data.dividends)
    prevStakingPool = scenario.compute(token.data.piggyBank)
    prevAliceRecord = scenario.compute(token.data.ledger.get(sender.address, DEFAULT_LEDGER_RECORD))

    # stake
    scenario += token.unstake(value = value).run(
        sender = sender,
        now = now
    )

    # verify
    newAliceRecord = scenario.compute(token.data.ledger.get(sender.address, DEFAULT_LEDGER_RECORD))
    scenario.verify_equal(newAliceRecord.frozenBalance, sp.as_nat(prevAliceRecord.frozenBalance - value))
    scenario.verify_equal(newAliceRecord.balance, prevAliceRecord.balance + value)
    scenario.verify_equal(newAliceRecord.rewardDebt, token.data.rewardPerToken * newAliceRecord.frozenBalance)
    scenario.verify_equal(token.data.totalStaked, sp.as_nat(prevLpSupply - value))
    
@sp.add_test(name = "Test setting liquidity address")
def testSetLiquidityAddress():
    scenario = sp.test_scenario()
    scenario.add_flag("protocol", "florence")
    scenario.table_of_contents()

    scenario.show([admin, bob])
    time = sp.timestamp_from_utc_now()

    scenario.h1("Contract")
    piggyBankBreakTime = time.add_days(STAKING_DURATION)
    token = FA12_core(piggyBankBreakTime=piggyBankBreakTime, now = time)

    scenario.h1("Test setting liquidity address by diffrent users")

    scenario += token
    scenario.h1("success in case of calling by the admin")
    scenario += token.setLiqAddress(address = bob.address).run(
        sender = admin,
        now = time
    )
    scenario.verify_equal(scenario.compute(token.data.liqAddress), bob.address)

    scenario.h1("fail in case of calling by the non-admin")
    scenario += token.setLiqAddress(address = alice.address).run(
        sender = bob,
        now = time,
        valid=False
    )

@sp.add_test(name = "Test setting the baker registry")
def tesSetBakerRegistryAddress():
    scenario = sp.test_scenario()
    scenario.add_flag("protocol", "florence")
    scenario.table_of_contents()

    scenario.show([admin, bob])
    time = sp.timestamp_from_utc_now()

    scenario.h1("Contract")
    piggyBankBreakTime = time.add_days(STAKING_DURATION)
    token = FA12_core(piggyBankBreakTime=piggyBankBreakTime, now = time)

    scenario.h1("Test setting baker registry address by diffrent users")

    scenario += token
    scenario.h1("success in case of calling by the admin")
    scenario += token.setBakerValidatorContract(address = bob.address).run(
        sender = admin,
        now = time
    )
    scenario.verify_equal(scenario.compute(token.data.bakerValidatorContract), bob.address)

    scenario.h1("fail in case of calling by the non-admin")
    scenario += token.setBakerValidatorContract(address = alice.address).run(
        sender = bob,
        now = time,
        valid=False
    )

@sp.add_test(name = "Test update the admin address")
def tesSetLiquidityAddress():
    scenario = sp.test_scenario()
    scenario.add_flag("protocol", "florence")
    scenario.table_of_contents()

    scenario.show([admin, bob])
    time = sp.timestamp_from_utc_now()

    scenario.h1("Contract")
    piggyBankBreakTime = time.add_days(STAKING_DURATION)
    token = FA12_core(piggyBankBreakTime=piggyBankBreakTime, now = time)

    scenario.h1("Test setting change admin address by diffrent users")

    scenario += token
    scenario.h1("success in case of calling by the admin")
    scenario += token.changeAdmin(bob.address).run(
        sender = admin,
        now = time
    )
    scenario.verify_equal(scenario.compute(token.data.admin), bob.address)

    scenario.h1("fail in case of calling by the non-admin")
    scenario += token.changeAdmin(alice.address).run(
        sender = carol,
        now = time,
        valid=False
    )

@sp.add_test(name = "Test various ways to mint")
def testMinting():
    scenario = sp.test_scenario()
    scenario.add_flag("protocol", "florence")
    scenario.table_of_contents()

    scenario.show([admin, bob])
    time = sp.timestamp_from_utc_now()

    scenario.h1("Contract")
    piggyBankBreakTime = time.add_days(STAKING_DURATION)
    token = FA12_core(piggyBankBreakTime=piggyBankBreakTime, now = time)
    scenario += token

    scenario += token.setLiqAddress(address = bob.address).run(
        sender = admin,
        now = time
    )

    scenario.h1("Test minting by different users")

    scenario.h1("success in case of miting by the liquidity mining address")
    amount = 1000000
    prevBobRecord = scenario.compute(token.data.ledger.get(bob.address, DEFAULT_LEDGER_RECORD))
    prevUsedSupply = scenario.compute(token.data.usedLiqSupply)
    scenario += token.mint(address = bob.address, value = amount).run(
        sender = bob,
        now = time
    )
    newUsedSupply = scenario.compute(token.data.usedLiqSupply)
    newBobRecord = scenario.compute(token.data.ledger.get(bob.address, DEFAULT_LEDGER_RECORD))
    scenario.verify_equal(newUsedSupply, prevUsedSupply + amount)
    scenario.verify_equal(newBobRecord.balance, prevBobRecord.balance + amount)

    scenario.h1("fail in case of calling by the non-admin")
    scenario += token.mint(address = bob.address, value = amount).run(
        sender = carol,
        now = time,
        valid = False
    )

    scenario.h1("Test minting of different amounts")

    scenario.h1("success in case of 0 MAGs minted")
    amount = 0
    prevBobRecord = scenario.compute(token.data.ledger.get(bob.address, DEFAULT_LEDGER_RECORD))
    prevUsedSupply = scenario.compute(token.data.usedLiqSupply)
    scenario += token.mint(address = bob.address, value = amount).run(
        sender = bob,
        now = time
    )
    newUsedSupply = scenario.compute(token.data.usedLiqSupply)
    newBobRecord = scenario.compute(token.data.ledger.get(bob.address, DEFAULT_LEDGER_RECORD))
    scenario.verify_equal(newUsedSupply, prevUsedSupply + amount)
    scenario.verify_equal(newBobRecord.balance, prevBobRecord.balance + amount)

    scenario.h1("success in case of 100 MAGs minted")
    amount = 0
    prevBobRecord = scenario.compute(token.data.ledger.get(bob.address, DEFAULT_LEDGER_RECORD))
    prevUsedSupply = scenario.compute(token.data.usedLiqSupply)
    scenario += token.mint(address = bob.address, value = amount).run(
        sender = bob,
        now = time
    )
    newUsedSupply = scenario.compute(token.data.usedLiqSupply)
    newBobRecord = scenario.compute(token.data.ledger.get(bob.address, DEFAULT_LEDGER_RECORD))
    scenario.verify_equal(newUsedSupply, prevUsedSupply + amount)
    scenario.verify_equal(newBobRecord.balance, prevBobRecord.balance + amount)

    scenario.h1("success in case of total supply of MAGs reached")
    amount = 0
    prevBobRecord = scenario.compute(token.data.ledger.get(bob.address, DEFAULT_LEDGER_RECORD))
    prevUsedSupply = scenario.compute(token.data.usedLiqSupply)
    scenario += token.mint(address = bob.address, value = amount).run(
        sender = bob,
        now = time
    )
    newUsedSupply = scenario.compute(token.data.usedLiqSupply)
    newBobRecord = scenario.compute(token.data.ledger.get(bob.address, DEFAULT_LEDGER_RECORD))
    scenario.verify_equal(newUsedSupply, prevUsedSupply + amount)
    scenario.verify_equal(newBobRecord.balance, prevBobRecord.balance + amount)


@sp.add_test(name = "Test betting")
def testBet():
    scenario = sp.test_scenario()
    scenario.add_flag("protocol", "florence")
    scenario.table_of_contents()

    time = sp.timestamp_from_utc_now()

    scenario.h1("Contract")
    piggyBankBreakTime = time.add_days(STAKING_DURATION)
    token = FA12_core(piggyBankBreakTime=piggyBankBreakTime, now = time)

    scenario.h1("Test betting in different time")

    scenario += token
    scenario.h1("success in case of starting new round")
    time = time.add_hours(10)
    finishTime = time.add_hours(100)
    successBetCase(scenario, time, token, alice, False, finishTime)

    scenario.h1("success in case of betting after the round started")
    time = time.add_hours(10)
    successBetCase(scenario, time, token, alice, False, finishTime)

    scenario.h1("success in case of betting after rewards pool is > 25 XTZ but more than hour left")
    for i in range(0, 10):
        time = time.add_seconds(1)
        successBetCase(scenario, time, token, alice, False, finishTime)

    scenario.h1("success in case of betting after rewards pool is > 25 XTZ")
    time = time.add_hours(89)
    time = time.add_seconds(50)
    finishTime = finishTime.add_minutes(1)
    successBetCase(scenario, time, token, alice, False, finishTime)

    scenario.h1("success in case of betting after rewards pool is > 100 XTZ but more than 45 minutes left")
    for i in range(0, 12):
        time = time.add_seconds(1)
        finishTime = finishTime.add_seconds(1)
        successBetCase(scenario, time, token, alice, False, finishTime)

    scenario.h1("success in case of betting after rewards pool is > 100 XTZ")
    time = time.add_minutes(16)
    finishTime = time.add_minutes(45)
    successBetCase(scenario, time, token, alice, False, finishTime)

    scenario.h1("success in case of betting after rewards pool is > 1000 XTZ but more than 45 minutes left")
    for i in range(0, 11):
        time = time.add_seconds(1)
        finishTime = finishTime.add_seconds(1)
        successBetCase(scenario, time, token, alice, False, finishTime)

    scenario.h1("success in case of betting after rewards pool is > 1000 XTZ")
    time = time.add_minutes(31)
    finishTime = time.add_minutes(30)
    successBetCase(scenario, time, token, alice, False, finishTime)

    scenario.h1("success in case of betting after rewards pool is > 2000 XTZ but more than 15 minutes left")
    for i in range(0, 12):
        time = time.add_seconds(1)
        finishTime = finishTime.add_seconds(1)
        successBetCase(scenario, time, token, alice, False, finishTime)

    scenario.h1("success in case of betting after rewards pool is > 2000 XTZ")
    time = time.add_minutes(15)
    time = time.add_seconds(58)
    finishTime = time.add_minutes(15)
    successBetCase(scenario, time, token, alice, False, finishTime)

    scenario.h1("success in case of betting after rewards pool is > 5000 XTZ but more than 5 minutes left")
    for i in range(0, 11):
        time = time.add_seconds(1)
        finishTime = finishTime.add_seconds(1)
        successBetCase(scenario, time, token, alice, False, finishTime)

    scenario.h1("success in case of betting after rewards pool is > 5000 XTZ")
    time = time.add_minutes(11)
    finishTime = time.add_minutes(5)
    successBetCase(scenario, time, token, alice, False, finishTime)

    scenario.h1("success in case of betting after the round ended")
    time = time.add_minutes(11)
    finishTime = time.add_hours(100)
    successBetCase(scenario, time, token, alice, False, finishTime, startNewRound=True)

    scenario.h1("Test betting with different assets")

    scenario.h1("success in case of 1 XTZ sent")
    time = time.add_minutes(1)
    successBetCase(scenario, time, token, alice, False, finishTime)

    scenario.h1("success in case of 10 MAGs sent")
    time = time.add_minutes(1)
    successBetCase(scenario, time, token, alice, True, finishTime)

    scenario.h1("fail in case of 0 XTZ sent")
    scenario += token.bet().run(
        sender = bob,
        now = time,
        valid = False
    )

    scenario.h1("fail in case of 1.1 XTZ sent")
    scenario += token.bet().run(
        sender = alice,
        amount = sp.mutez(1100000),
        now = time,
        valid = False
    )

    scenario.h1("fail in case of low MAG balance")
    scenario += token.bet().run(
        sender = bob,
        now = time,
        valid = False
    )

    scenario.h1("Test betting in particular cases")

    scenario.h1("success in case of betting after the 42 monthes")
    time = time.add_hours(30660)
    finishTime = time.add_hours(100)
    successBetCase(scenario, time, token, alice, False, finishTime, startNewRound=True)

    scenario.h1("success in case of betting after all mags are distributed")
    time = time.add_hours(30660)
    finishTime = time.add_hours(100)
    successBetCase(scenario, time, token, alice, False, finishTime, startNewRound=True, mintNewTokens=False)

@sp.add_test(name = "Test staking")
def testStaking():
    scenario = sp.test_scenario()
    scenario.add_flag("protocol", "florence")
    scenario.table_of_contents()

    time = sp.timestamp_from_utc_now()

    scenario.h1("Contract")
    piggyBankBreakTime = time.add_days(STAKING_DURATION)
    token = FA12_core(piggyBankBreakTime=piggyBankBreakTime, now = time)

    scenario.h1("Preparations")
    scenario += token
    time = time.add_hours(10)
    finishTime = time.add_hours(100)
    successBetCase(scenario, time, token, alice, False, finishTime)
    for i in range(0, 10):
        time = time.add_seconds(1)
        successBetCase(scenario, time, token, alice, False, finishTime)

    scenario.h1("Test staking in different times")

    scenario.h1("success in case of first staking")
    time = time.add_hours(1)
    successStakeCase(scenario, time, token, alice, sp.as_nat(ONE_MAG))

    scenario.h1("success in case of second staking")
    for i in range(0, 5):
        time = time.add_seconds(1)
        successBetCase(scenario, time, token, alice, False, finishTime)

    time = time.add_hours(1)
    successStakeCase(scenario, time, token, alice, sp.as_nat(ONE_MAG))

    scenario.h1("success in case of staking after partial unstaking")
    for i in range(0, 5):
        time = time.add_seconds(1)
        successBetCase(scenario, time, token, alice, False, finishTime)
    time = time.add_hours(1)
    scenario += token.unstake(value = ONE_MAG).run(
        sender = alice,
        now = time
    )
    successStakeCase(scenario, time, token, alice, sp.as_nat(10 * ONE_MAG))

    scenario.h1("success in case of staking after full unstaking")
    for i in range(0, 5):
        time = time.add_seconds(1)
        successBetCase(scenario, time, token, alice, False, finishTime)
    for i in range(0, 10):
        time = time.add_seconds(1)
        successBetCase(scenario, time, token, bob, False, finishTime)
    scenario += token.unstake(value = 11 * ONE_MAG).run(
        sender = alice,
        now = time
    )
    time = time.add_hours(1)
    successStakeCase(scenario, time, token, alice, sp.as_nat(1 * ONE_MAG))

    scenario.h1("Test staking with different amounts")

    scenario.h1("success in case of 0 MAGs staked")
    time = time.add_minutes(30)
    successStakeCase(scenario, time, token, alice, sp.as_nat(0))

    scenario.h1("success in case of 10 MAGs staked")
    successStakeCase(scenario, time, token, bob, sp.as_nat(10 * ONE_MAG))

    scenario.h1("fail in case of too many MAGs staked")
    time = time.add_hours(1)
    scenario += token.stake(value=100 * ONE_MAG).run(
        sender = bob,
        now = time,
        valid = False
    )

    scenario.h1("Test staking with different amounts")

    scenario.h1("success in case of staking with no votes before")
    successStakeCase(scenario, time, token, alice, sp.as_nat(ONE_MAG))

    scenario.h1("success in case of staking with existed votes")
    scenario += token.vote(
        alice.public_key_hash,
    ).run(
        sender = alice,
        now = time,
        voting_powers = { alice.public_key_hash : 10 }
    )
    successStakeCase(scenario, time, token, alice, sp.as_nat(ONE_MAG))

@sp.add_test(name = "Test unstaking")
def testUnstaking():
    scenario = sp.test_scenario()
    scenario.add_flag("protocol", "florence")
    scenario.table_of_contents()

    time = sp.timestamp_from_utc_now()

    scenario.h1("Contract")
    piggyBankBreakTime = time.add_days(STAKING_DURATION)
    token = FA12_core(piggyBankBreakTime=piggyBankBreakTime, now = time)

    scenario.h1("Preparations")
    scenario += token
    time = time.add_hours(10)
    finishTime = time.add_hours(100)
    successBetCase(scenario, time, token, alice, False, finishTime)
    for i in range(0, 30):
        time = time.add_seconds(1)
        successBetCase(scenario, time, token, alice, False, finishTime)
    successStakeCase(scenario, time, token, alice, sp.as_nat(30 * ONE_MAG))

    scenario.h1("Test unstaking with different amounts")

    scenario.h1("success in case of partial unstaking")
    successUnstakeCase(scenario, time, token, alice, sp.as_nat(ONE_MAG))

    scenario.h1("success in case of 0 MAGs unstaked")
    successUnstakeCase(scenario, time, token, alice, sp.as_nat(0))

    scenario.h1("success in case of full unstaking")
    successUnstakeCase(scenario, time, token, alice, sp.as_nat(29 * ONE_MAG))

    scenario.h1("fail in case of too many MAGs unstaking")
    scenario += token.unstake(value=100 * ONE_MAG).run(
        sender = bob,
        now = time,
        valid = False
    )

    for i in range(0, 10):
        time = time.add_seconds(1)
        successBetCase(scenario, time, token, bob, False, finishTime)
    successStakeCase(scenario, time, token, bob, sp.as_nat(10 * ONE_MAG))
    for i in range(0, 10):
        time = time.add_seconds(1)
        successBetCase(scenario, time, token, bob, False, finishTime)

    scenario.h1("Test staking with different rewards")

    scenario.h1("success in case of unstaking with existed dividends")
    successUnstakeCase(scenario, time, token, bob, sp.as_nat(ONE_MAG))

    scenario.h1("success in case of unstaking with zero dividends")
    successUnstakeCase(scenario, time, token, bob, sp.as_nat(ONE_MAG))


@sp.add_test(name = "Test default method")
def testDefault():
    scenario = sp.test_scenario()
    scenario.add_flag("protocol", "florence")
    scenario.table_of_contents()

    time = sp.timestamp_from_utc_now()
    finishTime = time.add_hours(100)

    scenario.h1("Contract")
    piggyBankBreakTime = time.add_days(STAKING_DURATION)
    token = FA12_core(piggyBankBreakTime=piggyBankBreakTime, now = time)

    scenario.h1("Preparations")
    scenario += token
    scenario += token.setLiqAddress(address = bob.address).run(
        sender = admin,
        now = time
    )
    successBetCase(scenario, time, token, bob, False, finishTime)
    for i in range(0, 9):
        time = time.add_seconds(1)
        successBetCase(scenario, time, token, bob, False, finishTime)
    successStakeCase(scenario, time, token, bob, sp.as_nat(10 * ONE_MAG))

    scenario.h1("Test sending assets")

    scenario.h1("success in case of sending 0 tokens from liquidity address")
    time = time.add_hours(1)
    successDefaultCase(scenario, time, token, bob, 0)

    scenario.h1("success in case of sending some tokens from liquidity address")
    time = time.add_hours(1)
    successDefaultCase(scenario, time, token, bob, (100000))

    scenario.h1("success in case of sending 0 tokens from the third party address")
    time = time.add_hours(1)
    successDefaultCase(scenario, time, token, alice, (0))

    scenario.h1("success in case of sending some tokens from the third party address")
    time = time.add_hours(1)
    successDefaultCase(scenario, time, token, alice, (100000))


@sp.add_test(name = "Test vote method")
def testVoting():
    scenario = sp.test_scenario()
    scenario.add_flag("protocol", "florence")
    scenario.table_of_contents()

    time = sp.timestamp_from_utc_now()
    finishTime = time.add_hours(100)

    scenario.h1("Contract")
    piggyBankBreakTime = time.add_days(STAKING_DURATION)
    token = FA12_core(piggyBankBreakTime=piggyBankBreakTime, now = time)

    scenario.h1("Preparations")
    scenario += token
    scenario += token.setLiqAddress(address = bob.address).run(
        sender = admin,
        now = time
    )
    successBetCase(scenario, time, token, bob, False, finishTime)
    for i in range(0, 9):
        time = time.add_seconds(1)
        successBetCase(scenario, time, token, bob, False, finishTime)
    for i in range(0, 10):
        time = time.add_seconds(1)
        successBetCase(scenario, time, token, alice, False, finishTime)
    for i in range(0, 2):
        time = time.add_seconds(1)
        successBetCase(scenario, time, token, carol, False, finishTime)

    scenario.h1("success in case of withdrawing 0 votes")
    time = time.add_hours(1)
    successVoteCase(scenario, time, token, bob, sp.key_hash(ZERO_ADDRESS), False, sp.key_hash(ZERO_ADDRESS), sp.key_hash(ZERO_ADDRESS))

    scenario.h1("success in case of voting with some staked tokens")
    successStakeCase(scenario, time, token, bob, sp.as_nat(10 * ONE_MAG))
    time = time.add_hours(1)
    successVoteCase(scenario, time, token, bob, alice.public_key_hash, True, alice.public_key_hash, sp.key_hash(ZERO_ADDRESS))

    scenario.h1("success in case of withdrawing some votes")
    time = time.add_hours(1)
    successVoteCase(scenario, time, token, bob, alice.public_key_hash, False, alice.public_key_hash, sp.key_hash(ZERO_ADDRESS))
    successUnstakeCase(scenario, time, token, bob, sp.as_nat(10 * ONE_MAG))

    scenario.h1("Test voting for different candidates")
    successStakeCase(scenario, time, token, alice, sp.as_nat(10 * ONE_MAG))
    successStakeCase(scenario, time, token, bob, sp.as_nat(10 * ONE_MAG))
    successStakeCase(scenario, time, token, carol, sp.as_nat(2 * ONE_MAG))

    scenario.h1("success in case of voting for baker")
    successVoteCase(scenario, time, token, bob, carol.public_key_hash, True, carol.public_key_hash, alice.public_key_hash)
    
    scenario.h1("success in case of voting for current delegate")
    successVoteCase(scenario, time, token, alice, carol.public_key_hash, True, carol.public_key_hash, alice.public_key_hash)
    
    scenario.h1("success in case of voting for second candidate")
    successVoteCase(scenario, time, token, carol, alice.public_key_hash, True, carol.public_key_hash, alice.public_key_hash)
    
    scenario.h1("success in case of voting for the chosen baker twice")
    successVoteCase(scenario, time, token, bob, carol.public_key_hash, True, carol.public_key_hash, alice.public_key_hash, True)
    
    scenario.h1("success in case of removing votes")
    successVoteCase(scenario, time, token, bob, carol.public_key_hash, False, carol.public_key_hash, alice.public_key_hash)

    scenario.h1("fail in case of voting for non-baker")
    scenario += token.vote(
        devid.public_key_hash,
    ).run(
        sender = bob,
        now = time,
        voting_powers = {devid.public_key_hash : 0}
    )