import boa
import pytest


def test_ema_responds_to_sfrxusd_rate_increase(
    fork_mainnet,
    controller,
    rate_calculator,
    ema_policy,
    setup_market,
    increase_sfrxusd_apr,
):
    """Test that EMA rate increases when sfrxUSD APR increases"""
    # Get initial rate
    initial_ma_rate = ema_policy.ma_rate()
    initial_apr = initial_ma_rate * 365 * 86400 / 10**18

    # Fast forward time and check rates increase
    for i in range(5):
        # Advance 1 day
        boa.env.time_travel(seconds=86400)

        # Update the rate
        controller.save_rate()

        # Check the new rate
        new_ma_rate = ema_policy.ma_rate()
        new_apr = new_ma_rate * 365 * 86400 / 10**18

        # Print for debugging
        print(f"Day {i+1}: MA rate APR = {new_apr / 10**16:.2f}%")

        # Rate should be increasing
        if i > 0:  # Allow first day for the rate to start changing
            assert (
                new_ma_rate > initial_ma_rate
            ), f"EMA rate should increase after sfrxUSD APR increase"


def test_ema_floor_when_sfrxusd_apr_near_zero(
    fork_mainnet, controller, vault, ema_policy, setup_market, decrease_sfrxusd_apr
):
    """Test that EMA rate decreases to floor when sfrxUSD APR drops to near zero"""
    # Initial values
    initial_ma_rate = ema_policy.ma_rate()
    initial_apr = initial_ma_rate * 365 * 86400 / 10**18

    print(f"Initial MA rate APR: {initial_apr / 10**16:.2f}%")

    # Fast forward time and observe rate floor
    min_ema_rate = None
    min_borrow_rate = None

    for i in range(9):  # Test for 9 days as mentioned in user's scenario
        # Advance 1 day
        boa.env.time_travel(seconds=86400)

        # Update the rate
        controller.save_rate()

        # Check values
        ma_rate = ema_policy.ma_rate()
        borrow_rate = vault.borrow_apr()

        # Record the minimum values
        if min_ema_rate is None or ma_rate < min_ema_rate:
            min_ema_rate = ma_rate

        if min_borrow_rate is None or borrow_rate < min_borrow_rate:
            min_borrow_rate = borrow_rate

        # Print for debugging
        print(
            f"Day {i+1}: MA rate APR = {ma_rate * 365 * 86400 / 10**16:.2f}%, Borrow APR = {borrow_rate / 10**16:.2f}%"
        )

    # Verify rate floor - hardcoded MIN_EMA_RATE is 317097920 (1% APR)
    floor_apr = int(0.01 * 10**18)  # 1% in annual terms
    floor_per_second = floor_apr // (365 * 86400)

    # Convert to annual for easier comparison (with small tolerance for rounding)
    min_ema_apr = min_ema_rate * 365 * 86400

    # Check floor is respected
    assert min_ema_rate >= 3.17 * 10**8, "EMA rate should not go below 1% APR floor"

    # Test that the borrow rate isn't zero (as mentioned by user)
    assert min_borrow_rate > 0, "Borrow rate should not reach zero"
    print(f"Minimum observed borrow APR: {min_borrow_rate / 10**16:.2f}%")


def test_utilization_impact_on_floor_rate(
    fork_mainnet, controller, vault, ema_policy, setup_market, decrease_sfrxusd_apr
):
    """Test how the 1% floor translates to different borrow rates at different utilizations"""
    # Set sfrxUSD APR to near zero and wait for EMA to reach floor
    for _ in range(5):
        boa.env.time_travel(seconds=86400)
        controller.save_rate()

    # Check current utilization and rate
    debt = controller.total_debt()
    assets = vault.totalAssets()
    util = debt * 10**18 / assets if assets > 0 else 0

    borrow_rate = vault.borrow_apr()
    ma_rate = ema_policy.ma_rate()

    print(f"Utilization: {util / 10**16:.2f}%")
    print(f"MA rate APR: {ma_rate * 365 * 86400 / 10**16:.2f}%")
    print(f"Borrow APR: {borrow_rate / 10**16:.2f}%")

    # Try to calculate what the rate should be at 85% utilization
    # We need the policy parameters for this calculation
    params = ema_policy.parameters()
    r_minf = params[2]  # r_minf parameter
    A = params[1]  # A parameter
    u_inf = params[0]  # u_inf parameter
    shift = params[3]  # shift parameter

    # Manually calculate what the rate would be at 85% utilization with the floor MA rate
    target_util = 850000000000000000  # 85%
    floor_rate = ma_rate

    # Using the formula from calculate_rate function:
    # r0 * r_minf / 10**18 + A * r0 / (u_inf - u) + shift
    expected_rate_at_target = (floor_rate * r_minf) // 10**18
    expected_rate_at_target += (A * floor_rate) // (u_inf - target_util)
    expected_rate_at_target += shift

    target_pct = expected_rate_at_target * 365 * 86400 / 10**16
    print(f"Calculated rate at 85% utilization: {target_pct:.2f}%")

    # To a few significant digits, the rate should be 1%
    assert target_pct > 0.99 and target_pct < 1.01
