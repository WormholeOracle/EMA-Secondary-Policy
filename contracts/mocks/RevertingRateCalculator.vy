# @version 0.3.10

"""
@title Reverting Rate Calculator
@notice A mock rate calculator that can be set to revert on demand
"""

should_revert: public(bool)
_rate: public(uint256)

@external
def __init__():
    self.should_revert = False
    self._rate = 1000000000  # Default rate similar to normal calculator

@external
def set_should_revert(revert: bool):
    self.should_revert = revert

@external
def set_rate(rate: uint256):
    self._rate = rate

@external
@view
def rate() -> uint256:
    assert not self.should_revert, "Rate calculation reverted"
    return self._rate 