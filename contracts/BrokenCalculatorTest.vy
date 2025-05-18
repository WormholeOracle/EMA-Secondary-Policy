# @version 0.3.10
"""
@title TestRateCalculator
@notice Simulates a rate calculator that starts working, then breaks (reverts)
"""

broken: public(bool)
rate_value: public(uint256)

@external
def __init__(_initial_rate: uint256):
    """
    @param _initial_rate Starting rate to return
    """
    self.rate_value = _initial_rate
    self.broken = False

@external
def break_calculator():
    """
    @notice Simulates the calculator breaking
    """
    self.broken = True

@external
@view
def rate() -> uint256:
    """
    @return The rate, or revert if calculator is broken
    """
    assert not self.broken, "Calculator is broken"
    return self.rate_value
