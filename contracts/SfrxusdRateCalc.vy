# @version 0.3.10
"""
@title SfrxUSD Rate Calculator
@notice Provides a per-second yield rate for sfrxUSD, based on current cycle data and stored assets
@author Curve.fi
"""

interface IFraxVault:
    def rewardsCycleData() -> (uint256, uint256, uint256): view
    def storedTotalAssets() -> uint256: view
    def maxDistributionPerSecondPerAsset() -> uint256: view


SFRXUSD: public(immutable(IFraxVault))


@external
def __init__(_sfrxusd: address):
    """
    @param _sfrxusd Address of the sfrxUSD vault contract
    @notice Initializes the rate calculator with the sfrxUSD contract address
    """
    SFRXUSD = IFraxVault(_sfrxusd)


@external
@view
def rate() -> uint256:
    """
    @notice Calculates the current per-second rate for sfrxUSD
    @return rate Yield per second, scaled by 1e18
    """
    cycle_end: uint256 = 0
    last_sync: uint256 = 0
    reward_amt: uint256 = 0
    cycle_end, last_sync, reward_amt = SFRXUSD.rewardsCycleData()

    # Prevent division by zero
    if cycle_end <= last_sync:
        return 0

    assets: uint256 = SFRXUSD.storedTotalAssets()
    if assets == 0:
        assets = 1

    max_distro: uint256 = SFRXUSD.maxDistributionPerSecondPerAsset()
    duration: uint256 = cycle_end - last_sync

    frax_per_second: uint256 = reward_amt / duration
    frax_per_second = frax_per_second * 10**18 / assets

    return min(frax_per_second, max_distro)
