# @version 0.3.10

"""
@title Mock Factory
@notice A simple mock of the Factory contract for testing
"""

admin: public(address)


@external
def __init__(_admin: address):
    self.admin = _admin
