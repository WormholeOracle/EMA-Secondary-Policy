from brownie import Contract, accounts, EMAMonetaryPolicy, chain, SfrxusdRateCalc, SfrxusdRateCalc_test, BrokenCalculatorTest
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

	# Deploy Contracts
	calculator = SfrxusdRateCalc.deploy('0xcf62F905562626CfcDD2261162a51fd02Fc9c5b6', {'from': accounts[0]})

	monpol = EMAMonetaryPolicy.deploy(
		"0xeA6876DDE9e3467564acBeE1Ed5bac88783205E0", # FACTORY
		calculator.address, # RATE_CALCULATOR
		"0xf939E0A03FB07F59A73314E73794Be0E57ac1b4E", # BORROWED_TOKEN
		850000000000000000, # TARGET_U
		200000000000000000, # LOW_RATIO
		7200000000000000000, # HIGH_RATIO
		0, # RATE_SHIFT
		{'from': accounts[0]}
	)


	# Initial values read
	rate = vault.borrow_apr() / 1e16
	print(f"sfrxUSD-long rate in LlamaLend vault with old contract is {rate:.2f}%")

	controller.set_monetary_policy(monpol, {'from': admin})
	controller.save_rate({'from': accounts[0]})

	rate = vault.borrow_apr() / 1e16
	print(f"sfrxUSD-long rate in LlamaLend vault with new SecondaryMonPol contract is {rate:.2f}%")

	sfrxusd_apr()
	print(f"Rate in calculator is {calculator.rate()}")
	print(f'MonPol ma_rate() is {monpol.ma_rate()*86400*365/1e16:.2f}%')


	# Increase sfrxUSD rate
	whale = accounts.at('0x81A2612F6dEA269a6Dd1F6DeAb45C5424EE2c4b7', force = True)
	balance = frxusd.balanceOf(whale)

	sfrxusd.setMaxDistributionPerSecondPerAsset(7735623555, {'from': accounts.at('0xB1748C79709f4Ba2Dd82834B8c82D4a505003f27', force=True)})

	frxusd.transfer(SFRXUSD, balance, {'from': whale})

	sfrxusd.syncRewardsAndDistribution({'from': accounts[0]})

	sfrxusd_apr()

	print("AFTER MESS WITH RATES")
	print(f"Rate in calculator is {calculator.rate()}")
	
	counter = 0
	while counter < 5:
		controller.save_rate({'from': accounts[0]})
		print(f'MonPol ma_rate() is {monpol.ma_rate()*86400*365/1e16:.2f}%')
		rate = vault.borrow_apr() / 1e16
		print(f"sfrxUSD-long rate in LlamaLend vault {counter} days after apr rise is {rate:.2f}%")
		chain.sleep(86400)
		counter += 1

	# Increase market utilization
	borrowed = controller.total_debt()
	supplied = vault.totalAssets()
	print("INCREASE MARKET UTILIZATION TEST")
	print(f"market utilization initially is {borrowed/supplied*100:2f}%")

	borrower = accounts.at('0x70644a67a01971c28395327Ca9846E0247313bC9', force=True)
	borrower_bal = frxusd.balanceOf(borrower)

	rate = vault.borrow_apr() / 1e16
	print(f"sfrxUSD-long rate before increasing market utilization is {rate:.2f}%")
	print(f'MonPol ma_rate() is {monpol.ma_rate()*86400*365/1e16:.2f}%')

	sfrxusd.approve(controller, 10000000e18, {'from': borrower})
	
	controller.create_loan(2100000e18, 2000000e18, 4, {'from': borrower})

	borrowed = controller.total_debt()
	supplied = vault.totalAssets()
	print(f"market utilization after create loan is {borrowed/supplied*100:2f}%")

	rate = vault.borrow_apr() / 1e16
	print(f"sfrxUSD-long rate after increasing market utilization is {rate:.2f}%")

	
	# Decrease sfrxUSD APR
	print("TEST REDUCING SFRXUSD APR TO NEAR 0")
	sfrxusd.setMaxDistributionPerSecondPerAsset(1, {'from': accounts.at('0xB1748C79709f4Ba2Dd82834B8c82D4a505003f27', force=True)})
	sfrxusd.syncRewardsAndDistribution({'from': accounts[0]})
	sfrxusd_apr()

	counter = 0
	while counter < 9:
		controller.save_rate({'from': accounts[0]})
		print(f'MonPol ma_rate() is {monpol.ma_rate()*86400*365/1e16:.2f}%')
		rate = vault.borrow_apr() / 1e16
		print(f"sfrxUSD-long rate in LlamaLend vault {counter} days after apr decrease is {rate:.2f}%")
		chain.sleep(86400)
		counter += 1

def set_calc():
	# Deploy Contracts
	calc1 = SfrxusdRateCalc.deploy('0xcf62F905562626CfcDD2261162a51fd02Fc9c5b6', {'from': accounts[0]})
	calc2 = SfrxusdRateCalc_test.deploy('0xcf62F905562626CfcDD2261162a51fd02Fc9c5b6', {'from': accounts[0]})
	calc1_apr = calc1.rate() *86400*365/1e16
	calc2_apr = calc2.rate() *86400*365/1e16
	print(f"Calc1 rate is {calc1.rate()} and apr is {calc1_apr}")
	print(f"Calc2 rate is {calc2.rate()} and apr is {calc2_apr}")

	monpol = EMAMonetaryPolicy.deploy(
		"0xeA6876DDE9e3467564acBeE1Ed5bac88783205E0", # FACTORY
		calc1.address, # RATE_CALCULATOR
		"0xf939E0A03FB07F59A73314E73794Be0E57ac1b4E", # BORROWED_TOKEN
		850000000000000000, # TARGET_U
		200000000000000000, # LOW_RATIO
		7200000000000000000, # HIGH_RATIO
		0, # RATE_SHIFT
		{'from': accounts[0]}
	)

	# Initial values read
	rate = vault.borrow_apr() / 1e16
	print(f"sfrxUSD-long rate in LlamaLend vault with old contract is {rate:.2f}%")

	controller.set_monetary_policy(monpol, {'from': admin})
	controller.save_rate({'from': accounts[0]})

	rate = vault.borrow_apr() / 1e16
	print(f"sfrxUSD-long rate in LlamaLend vault with new SecondaryMonPol contract is {rate:.2f}%")
	print(f'MonPol ma_rate() is {monpol.ma_rate()*86400*365/1e16:.2f}%')

	monpol.set_rate_calculator(calc2, {'from': admin})

	counter = 0
	while counter < 10:
		controller.save_rate({'from': accounts[0]})
		print(f'MonPol ma_rate() is {monpol.ma_rate()*86400*365/1e16:.2f}%')
		rate = vault.borrow_apr() / 1e16
		print(f"sfrxUSD-long rate in LlamaLend vault {counter} days after setting new calc is {rate:.2f}%")
		chain.sleep(86400)
		counter += 1

def broken_calc():
	# Deploy Contracts
	calc1 = SfrxusdRateCalc.deploy('0xcf62F905562626CfcDD2261162a51fd02Fc9c5b6', {'from': accounts[0]})
	calc2 = BrokenCalculatorTest.deploy(calc1.rate(), {'from': accounts[0]})
	calc1_apr = calc1.rate() *86400*365/1e16
	calc2_apr = calc2.rate() *86400*365/1e16
	print(f"Calc1 rate is {calc1.rate()} and apr is {calc1_apr}")
	print(f"Calc2 rate is {calc2.rate()} and apr is {calc2_apr}")

	monpol = EMAMonetaryPolicy.deploy(
		"0xeA6876DDE9e3467564acBeE1Ed5bac88783205E0", # FACTORY
		calc2.address, # RATE_CALCULATOR
		"0xf939E0A03FB07F59A73314E73794Be0E57ac1b4E", # BORROWED_TOKEN
		850000000000000000, # TARGET_U
		200000000000000000, # LOW_RATIO
		7200000000000000000, # HIGH_RATIO
		0, # RATE_SHIFT
		{'from': accounts[0]}
	)

	# Initial values read
	rate = vault.borrow_apr() / 1e16
	print(f"sfrxUSD-long rate in LlamaLend vault with old contract is {rate:.2f}%")

	controller.set_monetary_policy(monpol, {'from': admin})
	controller.save_rate({'from': accounts[0]})

	rate = vault.borrow_apr() / 1e16
	print(f"sfrxUSD-long rate in LlamaLend vault with new SecondaryMonPol contract is {rate:.2f}%")
	print(f'MonPol ma_rate() is {monpol.ma_rate()*86400*365/1e16:.2f}%')

	monpol.set_rate_calculator(calc2, {'from': admin})

	controller.save_rate({'from': accounts[0]})
	print(f'MonPol ma_rate() is {monpol.ma_rate()*86400*365/1e16:.2f}%')
	rate = vault.borrow_apr() / 1e16
	print(f"sfrxUSD-long rate in LlamaLend vault after setting new calc is {rate:.2f}%")

	print("BREAK THE CALCULATOR")
	calc2.break_calculator({'from': accounts[0]})
	controller.save_rate({'from': accounts[0]})

	# Increase market utilization
	borrowed = controller.total_debt()
	supplied = vault.totalAssets()
	print("TEST MARKET INTERACTION")
	print(f"market utilization initially is {borrowed/supplied*100:2f}%")

	borrower = accounts.at('0x70644a67a01971c28395327Ca9846E0247313bC9', force=True)
	borrower_bal = frxusd.balanceOf(borrower)

	rate = vault.borrow_apr() / 1e16
	print(f"sfrxUSD-long rate before increasing market utilization is {rate:.2f}%")
	print(f'MonPol ma_rate() is {monpol.ma_rate()*86400*365/1e16:.2f}%')

	sfrxusd.approve(controller, 10000000e18, {'from': borrower})
	
	controller.create_loan(2100000e18, 2000000e18, 4, {'from': borrower})

	borrowed = controller.total_debt()
	supplied = vault.totalAssets()
	print(f"market utilization after create loan is {borrowed/supplied*100:2f}%")

	rate = vault.borrow_apr() / 1e16
	print(f"sfrxUSD-long rate after increasing market utilization is {rate:.2f}%")



	print("REPLACING THE CALCULATOR")
	monpol.set_rate_calculator(calc1, {'from': admin})

	counter = 0
	while counter < 10:
		controller.save_rate({'from': accounts[0]})
		print(f'MonPol ma_rate() is {monpol.ma_rate()*86400*365/1e16:.2f}%')
		rate = vault.borrow_apr() / 1e16
		print(f"sfrxUSD-long rate in LlamaLend vault {counter} days after setting new calc is {rate:.2f}%")
		chain.sleep(86400)
		counter += 1

def replace_monpol():
	# Deploy Contracts
	calc1 = SfrxusdRateCalc.deploy('0xcf62F905562626CfcDD2261162a51fd02Fc9c5b6', {'from': accounts[0]})
	calc2 = BrokenCalculatorTest.deploy(calc1.rate(), {'from': accounts[0]})
	calc1_apr = calc1.rate() *86400*365/1e16
	calc2_apr = calc2.rate() *86400*365/1e16
	print(f"Calc1 rate is {calc1.rate()} and apr is {calc1_apr}")
	print(f"Calc2 rate is {calc2.rate()} and apr is {calc2_apr}")

	monpol_broken = EMAMonetaryPolicy.deploy(
		"0xeA6876DDE9e3467564acBeE1Ed5bac88783205E0", # FACTORY
		calc2.address, # RATE_CALCULATOR
		"0xf939E0A03FB07F59A73314E73794Be0E57ac1b4E", # BORROWED_TOKEN
		850000000000000000, # TARGET_U
		200000000000000000, # LOW_RATIO
		7200000000000000000, # HIGH_RATIO
		0, # RATE_SHIFT
		{'from': accounts[0]}
	)

	monpol_fixed = EMAMonetaryPolicy.deploy(
		"0xeA6876DDE9e3467564acBeE1Ed5bac88783205E0", # FACTORY
		calc1.address, # RATE_CALCULATOR
		"0xf939E0A03FB07F59A73314E73794Be0E57ac1b4E", # BORROWED_TOKEN
		850000000000000000, # TARGET_U
		200000000000000000, # LOW_RATIO
		7200000000000000000, # HIGH_RATIO
		0, # RATE_SHIFT
		{'from': accounts[0]}
	)

	# Initial values read
	rate = vault.borrow_apr() / 1e16
	print(f"sfrxUSD-long rate in LlamaLend vault with old contract is {rate:.2f}%")

	controller.set_monetary_policy(monpol_broken, {'from': admin})
	controller.save_rate({'from': accounts[0]})

	rate = vault.borrow_apr() / 1e16
	print(f"sfrxUSD-long rate in LlamaLend vault with new SecondaryMonPol contract is {rate:.2f}%")
	print(f'MonPol ma_rate() is {monpol_broken.ma_rate()*86400*365/1e16:.2f}%')

	print("BREAK THE CALCULATOR")
	calc2.break_calculator({'from': accounts[0]})
	controller.save_rate({'from': accounts[0]})
	print(f'MonPol ma_rate() in broken monpol is {monpol_broken.ma_rate()*86400*365/1e16:.2f}%')
	
	counter = 0
	while counter < 10:
		controller.save_rate({'from': accounts[0]})
		print(f'MonPol ma_rate() is {monpol_broken.ma_rate()*86400*365/1e16:.2f}%')
		rate = vault.borrow_apr() / 1e16
		print(f"sfrxUSD-long rate in LlamaLend vault {counter} days after Monpol breaks is {rate:.2f}%")
		chain.sleep(86400)
		counter += 1

	# Increase market utilization
	borrowed = controller.total_debt()
	supplied = vault.totalAssets()
	print("TEST MARKET INTERACTION")
	print(f"market utilization initially is {borrowed/supplied*100:2f}%")

	borrower = accounts.at('0x70644a67a01971c28395327Ca9846E0247313bC9', force=True)
	borrower_bal = frxusd.balanceOf(borrower)

	rate = vault.borrow_apr() / 1e16
	print(f"sfrxUSD-long rate before increasing market utilization is {rate:.2f}%")
	print(f'MonPol ma_rate() is {monpol_broken.ma_rate()*86400*365/1e16:.2f}%')

	sfrxusd.approve(controller, 10000000e18, {'from': borrower})
	
	controller.create_loan(2100000e18, 2000000e18, 4, {'from': borrower})

	borrowed = controller.total_debt()
	supplied = vault.totalAssets()
	print(f"market utilization after create loan is {borrowed/supplied*100:2f}%")

	rate = vault.borrow_apr() / 1e16
	print(f"sfrxUSD-long rate after increasing market utilization is {rate:.2f}%")

	print("REPLACING THE MONPOL")

	controller.set_monetary_policy(monpol_fixed, {'from': admin})
	controller.save_rate({'from': accounts[0]})

	crvusd = Contract('0xf939E0A03FB07F59A73314E73794Be0E57ac1b4E')
	vault_account = accounts.at("0x9E7641A394859860210203e6D9cb82044712421C", force=True)
	balance = vault.maxWithdraw("0x9E7641A394859860210203e6D9cb82044712421C")
	vault.withdraw(balance/2, {'from': vault_account})
	controller.save_rate({'from': accounts[0]})

	borrowed = controller.total_debt()
	supplied = vault.totalAssets()
	print(f'MonPol ma_rate() is {monpol_fixed.ma_rate()*86400*365/1e16:.2f}%')
	print(f"market utilization after transfer half balcne from vault is {borrowed/supplied*100:2f}%")

	rate = vault.borrow_apr() / 1e16
	print(f"sfrxUSD-long rate after increasing market utilization is {rate:.2f}%")

	balance = vault.maxWithdraw("0x9E7641A394859860210203e6D9cb82044712421C") * .96
	vault.withdraw(balance, {'from': vault_account})
	controller.save_rate({'from': accounts[0]})

	borrowed = controller.total_debt()
	supplied = vault.totalAssets()
	print(f"market utilization after transfer remaining balcne from vault is {borrowed/supplied*100:2f}%")

	rate = vault.borrow_apr() / 1e16
	print(f"sfrxUSD-long rate after increasing market utilization is {rate:.2f}%")

	crvusd_whale = accounts.at('0xA920De414eA4Ab66b97dA1bFE9e6EcA7d4219635', force=True)
	crvusd.approve(vault, 10000000000000e18, {'from': crvusd_whale})
	balance = crvusd.balanceOf(crvusd_whale)
	vault.deposit(balance, {'from': crvusd_whale})

	borrowed = controller.total_debt()
	supplied = vault.totalAssets()
	print(f"market utilization after supplied hugely to vault is {borrowed/supplied*100:2f}%")

	rate = vault.borrow_apr() / 1e16
	print(f"sfrxUSD-long rate after reducing market utilization is {rate:.2f}%")