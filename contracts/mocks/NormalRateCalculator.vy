# @version 0.3.10

"""
@title Normal Rate Calculator
@notice A mock rate calculator that always returns a fixed rate
"""

_rate: public(uint256)


@external
def __init__(rate: uint256):
    self._rate = rate


@external
@view
def rate() -> uint256:
    return self._rate
