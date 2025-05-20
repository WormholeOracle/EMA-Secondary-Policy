import os

import boa
import pytest

# Constants for mainnet contract addresses
FRXUSD_ADDRESS = "0xCAcd6fd266aF91b8AeD52aCCc382b4e165586E29"
SFRXUSD_ADDRESS = "0xcf62F905562626CfcDD2261162a51fd02Fc9c5b6"
CRVUSD_ADDRESS = "0xf939E0A03FB07F59A73314E73794Be0E57ac1b4E"
CONTROLLER_ADDRESS = "0xD961B0Da2B0Fb04439c96B552777720B5FC551A0"
VAULT_ADDRESS = "0xFf771E92DD2400b4F2D3E0aC3AfAe3aE1885877E"
FACTORY_ADDRESS = "0xeA6876DDE9e3467564acBeE1Ed5bac88783205E0"

# Etherscan API settings
ETHERSCAN_API = "https://api.etherscan.io/api"
ETHERSCAN_KEY = os.environ.get("ETHERSCAN_API_KEY", None)
ALCHEMY_API_KEY = os.environ.get("WEB3_ALCHEMY_PROJECT_ID", None)
if ALCHEMY_API_KEY is None:
    raise ValueError("WEB3_ALCHEMY_PROJECT_ID is not set")
RPC_URL = f"https://eth-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}"


def load_contract(addr, name="Contract"):
    return boa.from_etherscan(addr, name=name, uri=ETHERSCAN_API, api_key=ETHERSCAN_KEY)


@pytest.fixture(scope="session")
def fork_mainnet():
    """Create a mainnet fork for testing"""
    # Use environment variable or a default public RPC endpoint
    print(f"Forking from RPC: {RPC_URL}")
    boa.fork(RPC_URL)
    return True


@pytest.fixture
def deployer():
    """Generate an address for the deployer"""
    return boa.env.generate_address()


@pytest.fixture
def user():
    """Generate an address for a regular user"""
    return boa.env.generate_address()


@pytest.fixture
def controller(fork_mainnet):
    """Returns the Controller contract"""
    return load_contract(CONTROLLER_ADDRESS, "Controller")


@pytest.fixture
def vault(fork_mainnet):
    """Returns the Vault contract"""
    return load_contract(VAULT_ADDRESS, "Vault")


@pytest.fixture
def factory(fork_mainnet):
    """Returns the Factory contract"""
    return load_contract(FACTORY_ADDRESS, "Factory")


@pytest.fixture
def crvusd(fork_mainnet):
    """Returns the crvUSD token contract"""
    return load_contract(CRVUSD_ADDRESS, "crvUSD")


@pytest.fixture
def sfrxusd(fork_mainnet):
    """Returns the sfrxUSD token contract"""
    return load_contract(SFRXUSD_ADDRESS, "sfrxUSD")


@pytest.fixture
def admin(factory):
    """Admin account for controller and factory"""
    return factory.admin()


@pytest.fixture
def rate_calculator(deployer, sfrxusd):
    """Deploy the SfrxusdRateCalc contract"""
    calculator = boa.load_partial("contracts/SfrxusdRateCalc.vy")
    with boa.env.prank(deployer):
        return calculator.deploy(sfrxusd.address)


@pytest.fixture
def ema_policy(deployer, factory, rate_calculator, crvusd):
    """Deploy the EMA Monetary Policy contract"""
    policy = boa.load_partial("contracts/EMAMonetaryPolicy.vy")
    with boa.env.prank(deployer):
        return policy.deploy(
            factory.address,  # FACTORY
            rate_calculator.address,  # RATE_CALCULATOR
            crvusd.address,  # BORROWED_TOKEN
            850000000000000000,  # TARGET_U (85%)
            200000000000000000,  # LOW_RATIO (20%)
            7200000000000000000,  # HIGH_RATIO (720%)
            0,  # RATE_SHIFT
        )


@pytest.fixture
def setup_market(controller, admin, ema_policy):
    """Set up the market with our EMA policy"""
    with boa.env.prank(admin):
        controller.set_monetary_policy(ema_policy.address)

    # Save the initial rate
    controller.save_rate()
    return True


@pytest.fixture
def increase_sfrxusd_apr(sfrxusd):
    """Fixture to increase sfrxUSD APR for testing"""
    admin_role = "0xB1748C79709f4Ba2Dd82834B8c82D4a505003f27"
    with boa.env.prank(admin_role):
        # Set a relatively high distribution rate
        sfrxusd.setMaxDistributionPerSecondPerAsset(7735623555)

    # Trigger rewards sync
    sfrxusd.syncRewardsAndDistribution()
    return True


@pytest.fixture
def decrease_sfrxusd_apr(sfrxusd):
    """Fixture to decrease sfrxUSD APR to near zero for testing"""
    admin_role = "0xB1748C79709f4Ba2Dd82834B8c82D4a505003f27"
    with boa.env.prank(admin_role):
        # Set a minimal distribution rate
        sfrxusd.setMaxDistributionPerSecondPerAsset(1)

    # Trigger rewards sync
    sfrxusd.syncRewardsAndDistribution()
    return True
