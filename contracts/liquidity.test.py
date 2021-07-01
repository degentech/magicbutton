import os
import smartpy as sp

os.environ['ADMIN'] = "tz1burnburnburnburnburnburnburjAYjjX"

admin =  sp.test_account("Admin")
alice = sp.test_account("Alice")
bob = sp.test_account("Bob")
carol = sp.test_account("Carol")

liquidity = sp.io.import_script_from_url("file:contracts/liquidity.py")
mockQPToken = sp.io.import_script_from_url("file:contracts/mockQPToken.py")
Liquidity_core = liquidity.Liquidity_core
MockToken = mockQPToken.FA12Mock

ONE_MAG = 1000000
ZERO_ADDRESS = "tz1burnburnburnburnburnburnburjAYjjX"
ACCURACY = 1000000

DEFAULT_TOKEN_LEDGER_RECORD = sp.record(
                balance = 0,
                approvals = {},
            )
DEFAULT_LEDGER_RECORD = sp.record(
                balanceLiq = 0,
                rewardDebtLiq = 0,
                rewardChange = 0,
            )

def successDefaultCase(scenario, now, liquidity, sender):
    scenario += liquidity.default().run(
        sender = sender,
        source = sender,
        now = now
    )

def successStakeCase(scenario, now, liquidity, qtoken, sender, value):
    # store prev state
    prevLpSupply = scenario.compute(liquidity.data.totalStaked)
    prevAliceTokenRecord = scenario.compute(qtoken.data.balances.get(sender.address, DEFAULT_TOKEN_LEDGER_RECORD))
    prevAliceRecord = scenario.compute(liquidity.data.ledger.get(sender.address, DEFAULT_LEDGER_RECORD))

    # stake
    scenario += qtoken.approve(spender = liquidity.address, value = value).run(
        sender = sender,
        now = now
    )
    scenario += liquidity.stake(value = value).run(
        sender = sender,
        now = now
    )

    # verify
    newAliceRecord = scenario.compute(liquidity.data.ledger.get(sender.address, DEFAULT_LEDGER_RECORD))
    newAliceTokenRecord = scenario.compute(qtoken.data.balances.get(sender.address, DEFAULT_TOKEN_LEDGER_RECORD))
    scenario.show(newAliceRecord.rewardDebtLiq)
    scenario.show(liquidity.data.rewardPerToken * newAliceRecord.balanceLiq)
    scenario.verify_equal(liquidity.data.totalStaked, prevLpSupply  + value)
    scenario.verify_equal(newAliceTokenRecord.balance, sp.as_nat(prevAliceTokenRecord.balance - value))
    scenario.verify_equal(newAliceRecord.balanceLiq, prevAliceRecord.balanceLiq + value)
    scenario.verify_equal(newAliceRecord.rewardDebtLiq, liquidity.data.rewardPerToken * newAliceRecord.balanceLiq)
    
def successUnstakeCase(scenario, now, liquidity, qtoken, sender, value):
    # store prev state
    prevLpSupply = scenario.compute(liquidity.data.totalStaked)
    prevAliceTokenRecord = scenario.compute(qtoken.data.balances.get(sender.address, DEFAULT_TOKEN_LEDGER_RECORD))
    prevAliceRecord = scenario.compute(liquidity.data.ledger.get(sender.address, DEFAULT_LEDGER_RECORD))

    # unstake
    scenario += liquidity.unstake(value = value).run(
        sender = sender,
        now = now
    )

    # verify
    scenario.show(liquidity.data.rewardPerSec)
    scenario.show(liquidity.data.rewardPerToken)
    newAliceRecord = scenario.compute(liquidity.data.ledger.get(sender.address, DEFAULT_LEDGER_RECORD))
    newAliceTokenRecord = scenario.compute(qtoken.data.balances.get(sender.address, DEFAULT_TOKEN_LEDGER_RECORD))
    scenario.show(newAliceRecord.balanceLiq)
    scenario.verify_equal(liquidity.data.totalStaked, sp.as_nat(prevLpSupply  - value))
    scenario.verify_equal(newAliceTokenRecord.balance, prevAliceTokenRecord.balance + value)
    scenario.verify_equal(newAliceRecord.balanceLiq, sp.as_nat(prevAliceRecord.balanceLiq - value))
    scenario.verify_equal(newAliceRecord.rewardDebtLiq, liquidity.data.rewardPerToken * newAliceRecord.balanceLiq / ACCURACY)

    
@sp.add_test(name = "Test setting admin address")
def testChangeAdmin():
    scenario = sp.test_scenario()
    scenario.add_flag("protocol", "florence")
    scenario.table_of_contents()

    scenario.show([admin, bob])
    time = sp.timestamp_from_utc_now()

    scenario.h1("Contract")
    liquidity = Liquidity_core(qAddress = sp.address(ZERO_ADDRESS),tokenAddress = sp.address(ZERO_ADDRESS), lastUpdateTime = sp.timestamp_from_utc_now(), now = time)

    scenario.h1("Test permissions")

    scenario += liquidity
    scenario.h1("success in case of calling by the admin")
    scenario += liquidity.changeAdmin(bob.address).run(
        sender = admin,
        now = time
    )
    scenario.verify_equal(scenario.compute(liquidity.data.admin), bob.address)

    scenario.h1("fail in case of calling by the non-admin")
    scenario += liquidity.changeAdmin(alice.address).run(
        sender = admin,
        now = time,
        valid=False
    )

@sp.add_test(name = "Test setting the quipuswap exchange address")
def tesSetQAddress():
    scenario = sp.test_scenario()
    scenario.add_flag("protocol", "florence")
    scenario.table_of_contents()

    scenario.show([admin, bob])
    time = sp.timestamp_from_utc_now()

    scenario.h1("Contract")
    liquidity = Liquidity_core(qAddress = sp.address(ZERO_ADDRESS),tokenAddress = sp.address(ZERO_ADDRESS),lastUpdateTime = sp.timestamp_from_utc_now(), now = time)

    scenario.h1("Test setting the quipuswap contract")

    scenario += liquidity
    scenario.h1("success in case of calling by the admin")
    scenario += liquidity.setQAddress(contractAddress = bob.address).run(
        sender = admin,
        now = time
    )
    scenario.verify_equal(scenario.compute(liquidity.data.qAddress), bob.address)

    scenario.h1("fail in case of calling by the non-admin")
    scenario += liquidity.setQAddress(contractAddress = alice.address).run(
        sender = bob,
        now = time,
        valid=False
    )

@sp.add_test(name = "Test update the admin address")
def tesSetPause():
    scenario = sp.test_scenario()
    scenario.add_flag("protocol", "florence")
    scenario.table_of_contents()

    scenario.show([admin, bob])
    time = sp.timestamp_from_utc_now()

    scenario.h1("Contract")
    liquidity = Liquidity_core(qAddress = sp.address(ZERO_ADDRESS),tokenAddress = sp.address(ZERO_ADDRESS), lastUpdateTime = sp.timestamp_from_utc_now(), now = time)

    scenario.h1("Test setting change admin address by diffrent users")

    scenario += liquidity
    scenario.h1("success in case of calling by the admin")
    scenario += liquidity.setPause().run(
        sender = admin,
        now = time
    )
    scenario.verify_equal(scenario.compute(liquidity.data.pause), True)

    scenario.h1("fail in case of calling by the non-admin")
    scenario += liquidity.setPause().run(
        sender = carol,
        now = time,
        valid=False
    )

@sp.add_test(name = "Test staking")
def testStaking():
    scenario = sp.test_scenario()
    scenario.add_flag("protocol", "florence")
    scenario.table_of_contents()

    time = sp.timestamp_from_utc_now()

    scenario.h1("Contract")
    magToken = MockToken()
    mockToken = MockToken()
    liquidity = Liquidity_core(qAddress =mockToken.address,tokenAddress = magToken.address, lastUpdateTime = sp.timestamp_from_utc_now(), now = time)

    scenario.h1("Preparations")
    scenario += liquidity
    scenario += mockToken
    scenario += magToken
    value = 100 * ACCURACY
    scenario += mockToken.mint(address=alice.address,value=value).run(sender = admin, now = time)
    scenario += mockToken.mint(address=bob.address,value=value).run(sender = admin, now = time)
    scenario += mockToken.mint(address=carol.address,value=value).run(sender = admin, now = time)
    scenario += mockToken.mint(address=admin.address,value=value).run(sender = admin, now = time)

    scenario.h1("Test staking in different times")

    scenario.h1("success in case of first staking")
    time = time.add_hours(1)
    successStakeCase(scenario, time, liquidity, mockToken, alice, sp.as_nat(ONE_MAG))

    scenario.h1("success in case of second staking")
    successStakeCase(scenario, time, liquidity, mockToken, alice, sp.as_nat(ONE_MAG))

    scenario.h1("success in case of staking after partial unstaking")
    time = time.add_hours(1)
    scenario += liquidity.unstake(value = ONE_MAG).run(
        sender = alice,
        now = time
    )
    successStakeCase(scenario, time, liquidity, mockToken, alice, sp.as_nat(10 * ONE_MAG))

    scenario.h1("success in case of staking after full unstaking")
    scenario += liquidity.unstake(value = 11 * ONE_MAG).run(
        sender = alice,
        now = time
    )
    time = time.add_hours(1)
    successStakeCase(scenario, time, liquidity, mockToken, alice, sp.as_nat(1 * ONE_MAG))

    scenario.h1("Test staking with different amounts")

    scenario.h1("success in case of 0 LPs staked")
    time = time.add_minutes(30)
    successStakeCase(scenario, time, liquidity, mockToken, alice, sp.as_nat(0))

    scenario.h1("success in case of 10 LPs staked")
    successStakeCase(scenario, time, liquidity, mockToken, bob, sp.as_nat(10 * ONE_MAG))

    scenario.h1("fail in case of too many LPs staked")
    time = time.add_hours(1)
    scenario += liquidity.stake(value=10000 * ONE_MAG).run(
        sender = bob,
        now = time,
        valid = False
    )

    scenario.h1("Test staking in different time")

    scenario.h1("success in case of staking before rewards is distributed")
    successStakeCase(scenario, time, liquidity, mockToken, alice, sp.as_nat(ONE_MAG))

    scenario.h1("success in case of staking after rewards is distributed")
    time = time.add_days(365)
    successStakeCase(scenario, time, liquidity, mockToken, alice, sp.as_nat(ONE_MAG))
    successStakeCase(scenario, time, liquidity, mockToken, alice, 0)
    successStakeCase(scenario, time, liquidity, mockToken, bob, 0)
    newAliceTokenRecord = scenario.compute(magToken.data.balances.get(alice.address, DEFAULT_TOKEN_LEDGER_RECORD))
    newBobTokenRecord = scenario.compute(magToken.data.balances.get(bob.address, DEFAULT_TOKEN_LEDGER_RECORD))
    scenario.show(newAliceTokenRecord.balance)
    scenario.show(newBobTokenRecord.balance)

@sp.add_test(name = "Test unstaking")
def testUnstaking():
    scenario = sp.test_scenario()
    scenario.add_flag("protocol", "florence")
    scenario.table_of_contents()

    time = sp.timestamp_from_utc_now()

    scenario.h1("Contract")
    magToken = MockToken()
    mockToken = MockToken()
    liquidity = Liquidity_core(qAddress =mockToken.address,tokenAddress = magToken.address, lastUpdateTime = sp.timestamp_from_utc_now(), now = time)

    scenario.h1("Preparations")
    scenario += liquidity
    scenario += mockToken
    scenario += magToken
    value = 100 * ACCURACY
    scenario += mockToken.mint(address=alice.address,value=value).run(sender = admin, now = time)
    scenario += mockToken.mint(address=bob.address,value=value).run(sender = admin, now = time)
    scenario += mockToken.mint(address=carol.address,value=value).run(sender = admin, now = time)
    scenario += mockToken.mint(address=admin.address,value=value).run(sender = admin, now = time)
    successStakeCase(scenario, time, liquidity, mockToken, alice, sp.as_nat(value))

    scenario.h1("Test unstaking with different amounts")

    scenario.h1("success in case of partial unstaking")
    successUnstakeCase(scenario, time, liquidity, mockToken, alice, sp.as_nat(ACCURACY))

    scenario.h1("success in case of 0 LPs unstaked")
    successUnstakeCase(scenario, time, liquidity, mockToken, alice, sp.as_nat(0))

    scenario.h1("success in case of full unstaking")
    successUnstakeCase(scenario, time, liquidity, mockToken, alice, sp.as_nat(29 * ACCURACY))

    scenario.h1("fail in case of too many LPs unstaking")
    scenario += liquidity.unstake(value=100 * ACCURACY).run(
        sender = bob,
        now = time,
        valid = False
    )

    scenario.h1("Test unstaking in emergency cases")

    scenario.h1("success in case of unstaking after distribution is stopped")
    scenario += liquidity.setPause().run(
        sender = admin,
        source = admin,
        now = time
    )
    successUnstakeCase(scenario, time, liquidity, mockToken, alice, sp.as_nat(ACCURACY))

    scenario.h1("success in case of unstaking after distribution")
    successUnstakeCase(scenario, time, liquidity, mockToken, alice, sp.as_nat(59 * ACCURACY))

@sp.add_test(name = "Test default method")
def testDefault():
    scenario = sp.test_scenario()
    scenario.add_flag("protocol", "florence")
    scenario.table_of_contents()

    time = sp.timestamp_from_utc_now()
    finishTime = time.add_hours(100)

    scenario.h1("Preparations")
    magToken = MockToken()
    mockToken = MockToken()
    liquidity = Liquidity_core(qAddress =mockToken.address,tokenAddress = magToken.address, lastUpdateTime = sp.timestamp_from_utc_now(), now = time)
    scenario += liquidity
    scenario += mockToken
    scenario += magToken

    scenario.h1("Test sending assets")

    scenario.h1("success in case of sending 0 tokens from liquidity address")
    time = time.add_hours(1)
    successDefaultCase(scenario, time, liquidity, bob)

    scenario.h1("success in case of sending some tokens from liquidity address")
    time = time.add_hours(1)
    successDefaultCase(scenario, time, liquidity, bob)

    scenario.h1("success in case of sending 0 tokens from the third party address")
    time = time.add_hours(1)
    successDefaultCase(scenario, time, liquidity, alice)

    scenario.h1("success in case of sending some tokens from the third party address")
    time = time.add_hours(1)
    successDefaultCase(scenario, time, liquidity, alice)
