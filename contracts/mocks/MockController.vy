# @version 0.3.10

"""
@title Mock Controller
@notice A simple mock of the Controller contract for testing
"""

_total_debt: uint256


@external
@view
def total_debt() -> uint256:
    return self._total_debt


@external
def set_total_debt(debt: uint256):
    self._total_debt = debt


@external
def save_rate():
    pass
