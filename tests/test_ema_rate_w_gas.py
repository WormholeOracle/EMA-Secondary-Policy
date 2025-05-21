import boa
import pytest

from boa.profiling import global_profile


# Mock contracts for local testing without forking
@pytest.fixture
def mock_borrowed_token():
    """Deploy a mock ERC20 token to represent crvUSD"""
    token = boa.load_partial("contracts/mocks/MockERC20.vy")
    return token.deploy("Mock crvUSD", "mcrvUSD", 18)


@pytest.fixture
def mock_factory(deployer):
    """Deploy a mock factory contract"""
    factory = boa.load_partial("contracts/mocks/MockFactory.vy")
    return factory.deploy(deployer)


@pytest.fixture
def mock_controller(deployer):
    """Deploy a mock controller contract"""
    controller = boa.load_partial("contracts/mocks/MockController.vy")
    return controller.deploy()


@pytest.fixture
def reverting_rate_calculator():
    """Deploy a mock rate calculator that reverts on demand"""
    calculator = boa.load_partial("contracts/mocks/RevertingRateCalculator.vy")
    return calculator.deploy()


@pytest.fixture
def ema_policy_reverting(
    deployer, mock_factory, reverting_rate_calculator, mock_borrowed_token
):
    """Deploy the EMA Monetary Policy contract with reverting calculator"""
    policy = boa.load_partial("contracts/EMAMonetaryPolicy.vy")
    with boa.env.prank(deployer):
        return policy.deploy(
            mock_factory.address,  # FACTORY
            reverting_rate_calculator.address,  # RATE_CALCULATOR
            mock_borrowed_token.address,  # BORROWED_TOKEN
            850000000000000000,  # TARGET_U (85%)
            200000000000000000,  # LOW_RATIO (20%)
            7200000000000000000,  # HIGH_RATIO (720%)
            0,  # RATE_SHIFT
        )


@pytest.mark.gas_profile
def test_try_catch_safety_mechanism(
    mock_controller, ema_policy_reverting, reverting_rate_calculator
):
    """Test that the try/catch safety mechanism prevents reverts"""
    # First establish a baseline with no reverts
    initial_rate = ema_policy_reverting.rate_write(mock_controller.address)
    print(f"Initial rate with working calculator: {initial_rate}")
    assert initial_rate > 0, "Initial rate should be positive"

    # Now set the calculator to revert
    reverting_rate_calculator.set_should_revert(True)

    try:
        new_rate = ema_policy_reverting.rate_write(mock_controller.address)
        print(f"Rate with reverting calculator: {new_rate}")

        # Still should return a valid rate
        assert new_rate > 0, "Rate should be positive even when calculator reverts"
        print("✅ PASSED: rate_write() did not revert when calculator reverted")
    except Exception as e:
        pytest.fail(
            f"❌ FAILED: rate_write() reverted when it shouldn't have: {str(e)}"
        )

    try:
        reverting_rate_calculator.rate()
        pytest.fail("❌ FAILED: Direct calculator call should have reverted but didn't")
    except Exception as e:
        print(f"✅ Confirmed calculator is reverting with: {str(e)}")
