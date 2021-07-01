import smartpy as sp

ZERO_ADDRESS = "tz1burnburnburnburnburnburnburjAYjjX"
TOKEN_CONTRACT = sp.address("tz1burnburnburnburnburnburnburjAYjjX")

class Validator_core(sp.Contract):
    def __init__(self):
        self.init(
            validatedBakers = sp.set(t=sp.TKeyHash),
            tokenContract = TOKEN_CONTRACT
        )

    @sp.entry_point
    def validateNewBaker(self, address: sp.TKeyHash):
        sp.verify(sp.sender == self.data.tokenContract, message="Wrong permission")
        sp.if ~ self.data.validatedBakers.contains(address):
            sp.set_delegate(sp.some(address))
            self.data.validatedBakers.add(address)


if __name__ == "__main__":
    sp.add_compilation_target("Validator_core", Validator_core())
