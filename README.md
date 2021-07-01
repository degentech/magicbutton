![image](https://user-images.githubusercontent.com/86714974/124090772-d37e1000-da5d-11eb-92e4-6e693ae7d6b9.png)

# Description

This project is an experiment with yield farming features. Users are able to participate in the lottery, vote for the chosen baker, provide liquidity, and stake tokens to receive dividends in XTZ.

The current token implementation is based on [FA1.2](https://gitlab.com/tzip/tzip/-/blob/master/proposals/tzip-7/tzip-7.md) standard

# Architecture

The current solution consists of the following contracts:

1. `Token` - Extended FA1.2 token implementation with the ability to bet in the game, staking to receive dividends and voting for the preferred baker;
2. `Liquidity` - contract for providing liquidity through the [Quipuswap](https://quipuswap.com/);
3. `BakerValidator` - baker validation contract.


# Project structure

```
.
.
├──  contracts/ # folder with contract code
├────────────── bakerValidator # baker validation contract
├────────────── liquidity # contract for provide liquidity through the Quipuswap
├────────────── liquidity.test # tests for liquidity contract
├────────────── mockQPToken # mock contract for Quipuswap share pool token
├────────────── token # extended FA 1.2 token implementation
├────────────── token.test # tests for token contract
├──  README.md # current file
└──  .gitignore
```
# Prerequisites

- Install `tezos-client`
- Install [SmartPy CLI](https://smartpy.io/cli/)

# Compilation of the contracts

To compile the contracts simply run the following command:

```
~/smartpy-cli/SmartPy.sh compile ./contracts/<contract_name>.py  output
```

# Deployment

```
tezos-client -E <network path> originate contract <contract_name> \
    transferring 0 from <an_implicit_account> \
    running <path_to_compiled_contract>.tz \
    --init  <path_to_compiled_initial_storage>.tz \
    --burn-cap 10
```


# Testing

Run:

```
~/smartpy-cli/SmartPy.sh test ./contracts/token.test.py output --purge
~/smartpy-cli/SmartPy.sh test ./contracts/liquidity.test.py output --purge
```
