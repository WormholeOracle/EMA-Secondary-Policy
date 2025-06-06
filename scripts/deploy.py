from brownie import Contract, accounts, SfrxusdMonetaryPolicy, chain
import json

with open("abis/frxusd.json") as f:
    frxusd_abi = json.load(f)

with open("abis/sfrxusd.json") as f:
    sfrxusd_abi = json.load(f)

FRXUSD = "0xCAcd6fd266aF91b8AeD52aCCc382b4e165586E29"
SFRXUSD = "0xcf62F905562626CfcDD2261162a51fd02Fc9c5b6"

frxusd = Contract.from_abi("frxusd", FRXUSD, frxusd_abi)
sfrxusd = Contract.from_abi("sfrxusd", SFRXUSD, sfrxusd_abi)

controller = Contract('0x3DE37c38739dFb83b7A902842bF5393040f7BF50')
vault = Contract('0x8E3009b59200668e1efda0a2F2Ac42b24baa2982')
admin = accounts.at('0x40907540d8a6C65c637785e8f8B742ae6b0b9968', force=True)

def sfrxusd_apr():
    cycle_end: uint256 = 0
    last_sync: uint256 = 0
    reward_amt: uint256 = 0
    cycle_end, last_sync, reward_amt = sfrxusd.rewardsCycleData()
    print(f"{cycle_end}, {last_sync}, {reward_amt}")
    print(f"duration: {cycle_end - last_sync}")
    if cycle_end <= last_sync:
        return 0

    assets: uint256 = sfrxusd.storedTotalAssets()
    print(f"Assets: {assets}")
    if assets == 0:
        assets = 1

    max_distro: uint256 = sfrxusd.maxDistributionPerSecondPerAsset()
    print(f"Max Distro: {max_distro}")
    duration: uint256 = cycle_end - last_sync
    frax_per_second: uint256 = reward_amt / duration
    frax_per_second = frax_per_second * 10**18 / assets
    print(f"Frax per second: {frax_per_second}")
    rate = min(frax_per_second, max_distro)
    apr = rate * 365 * 86400 / 1e16
    print(f"frxUSD apr is {apr}%")

def deploy():

	monpol = SfrxusdMonetaryPolicy.deploy(
		"0xeA6876DDE9e3467564acBeE1Ed5bac88783205E0", # FACTORY
		"0xcf62F905562626CfcDD2261162a51fd02Fc9c5b6", # SFRXUSD
		"0xf939E0A03FB07F59A73314E73794Be0E57ac1b4E", # BORROWED_TOKEN
		850000000000000000, # TARGET_U
		200000000000000000, # LOW_RATIO
		7200000000000000000, # HIGH_RATIO
		0, # RATE_SHIFT
		{'from': accounts[0]}
	)

	rate = vault.borrow_apr() / 1e16
	print(f"sfrxUSD-long rate with old contract is {rate:.2f}%")

	controller.set_monetary_policy(monpol, {'from': admin})
	controller.save_rate({'from': accounts[0]})

	rate = vault.borrow_apr() / 1e16
	print(f"sfrxUSD-long rate with new contract is {rate:.2f}%")

	sfrxusd.setMaxDistributionPerSecondPerAsset(7735623555, {'from': accounts.at('0xB1748C79709f4Ba2Dd82834B8c82D4a505003f27', force=True)})
	sfrxusd_apr()
	controller.save_rate({'from': accounts[0]})
	print(f'MonPol rate read is {monpol.ma_sfrxusd_rate()*86400*365/1e16:.2f}%')

	print("AFTER MESS WITH RATES")
	# mess with sfrxUSD rate
	whale = accounts.at('0x81A2612F6dEA269a6Dd1F6DeAb45C5424EE2c4b7', force = True)
	balance = frxusd.balanceOf(whale)
	frxusd.transfer(SFRXUSD, balance, {'from': whale})
	# chain.sleep(86400*7)
	sfrxusd.syncRewardsAndDistribution({'from': accounts[0]})
	
	sfrxusd_apr()
	
	controller.save_rate({'from': accounts[0]})
	print(f'MonPol rate read is {monpol.ma_sfrxusd_rate()*86400*365/1e16:.2f}%')
	rate = vault.borrow_apr() / 1e16
	print(f"sfrxUSD-long rate right after apr rise is {rate:.2f}%")
	
	chain.sleep(86400)
	controller.save_rate({'from': accounts[0]})
	print(f'MonPol rate read is {monpol.ma_sfrxusd_rate()*86400*365/1e16:.2f}%')
	rate = vault.borrow_apr() / 1e16
	print(f"sfrxUSD-long rate a day after apr rise is {rate:.2f}%")

	
	chain.sleep(86400)
	controller.save_rate({'from': accounts[0]})
	print(f'MonPol rate read is {monpol.ma_sfrxusd_rate()*86400*365/1e16:.2f}%')
	rate = vault.borrow_apr() / 1e16
	print(f"sfrxUSD-long rate 2 days after apr rise is {rate:.2f}%")

	chain.sleep(86400)
	controller.save_rate({'from': accounts[0]})
	print(f'MonPol rate read is {monpol.ma_sfrxusd_rate()*86400*365/1e16:.2f}%')
	rate = vault.borrow_apr() / 1e16
	print(f"sfrxUSD-long rate 3 days after apr rise is {rate:.2f}%")

	chain.sleep(86400)
	controller.save_rate({'from': accounts[0]})
	print(f'MonPol rate read is {monpol.ma_sfrxusd_rate()*86400*365/1e16:.2f}%')
	rate = vault.borrow_apr() / 1e16
	print(f"sfrxUSD-long rate 4 days after apr rise is {rate:.2f}%")

	chain.sleep(86400)
	controller.save_rate({'from': accounts[0]})
	print(f'MonPol rate read is {monpol.ma_sfrxusd_rate()*86400*365/1e16:.2f}%')
	rate = vault.borrow_apr() / 1e16
	print(f"sfrxUSD-long rate 5 days after apr rise is {rate:.2f}%")

	borrowed = controller.total_debt()
	supplied = vault.totalAssets()
	print(f"market utilization is {borrowed/supplied*100:2f}%")

	# borrower
	borrower = accounts.at('0x70644a67a01971c28395327Ca9846E0247313bC9', force=True)
	borrower_bal = frxusd.balanceOf(borrower)
	sfrxusd.approve(controller, 10000000e18, {'from': borrower})
	controller.create_loan(2100000e18, 2000000e18, 4, {'from': borrower})
	print(f'MonPol rate read is {monpol.ma_sfrxusd_rate()*86400*365/1e16:.2f}%')
	rate = vault.borrow_apr() / 1e16
	print(f"sfrxUSD-long rate 5 days after apr rise is {rate:.2f}%")

	borrowed = controller.total_debt()
	supplied = vault.totalAssets()
	print(f"market utilization is {borrowed/supplied*100:2f}%")


