"""
Deployment Script for GamesRewards Smart Contract
================================================

This script generates deployment parameters for Remix IDE.

How to use:
1. Open Remix IDE at https://remix.ethereum.org
2. Create a new file called GamesRewards.sol and paste the contract code
3. Compile the contract
4. Deploy using the parameters below

NETWORK: Celo Mainnet
RPC: https://forno.celo.org
Chain ID: 42220

CONTRACT PARAMETERS:
====================

1. _token (address):
   G$ Token Contract: 0x62B8B11039FcfE5aB0C56E502b1C372A3d2a9c7A

2. _owner (address):
   - YOUR ADMIN WALLET ADDRESS
   - This is who can manage the contract
   - Get from MetaMask or your wallet

3. _dailyLimit (uint256):
   - Daily limit per user in G$ (with 18 decimals)
   - Examples:
     * 1000 G$ = 1000 * 10^18 = 1000000000000000000000
     * 5000 G$ = 5000 * 10^18 = 5000000000000000000000
     * 10000 G$ = 10000 * 10^18 = 10000000000000000000000

DEPLOYMENT STEPS IN REMIX:
==========================

1. COMPILE:
   - Select "GamesRewards" as the contract
   - Click "Compile GamesRewards.sol"

2. DEPLOY:
   - Select "Injected Provider" as the environment (requires MetaMask)
   - Make sure MetaMask is connected to Celo Mainnet
   
3. CONSTRUCTOR ARGUMENTS:
   - _token: "0x62B8B11039FcfE5aB0C56E502b1C372A3d2a9c7A"
   - _owner: "YOUR_WALLET_ADDRESS" (e.g., "0x...")
   - _dailyLimit: "1000000000000000000000" (1000 G$ with 18 decimals)

4. TRANSACT:
   - Click "Deploy"
   - Confirm in MetaMask
   - Wait for transaction confirmation

5. AFTER DEPLOYMENT:
   - Copy the deployed contract address
   - Update your backend with the new contract address
   - Fund the contract with G$ tokens for rewards
   - Authorize your backend server address as disburser

FUNDING THE CONTRACT:
=====================

After deployment, you need to fund the contract with G$ tokens:

Option 1: Direct Transfer
- Send G$ from your GAMES_KEY wallet to the contract address

Option 2: Via Remix
- In "Deployed Contracts" section, expand the contract
- Use any function that requires tokens (will fail if not funded)

UPDATING BACKEND:
=================

1. Replace GAMES_KEY logic with contract calls

2. Example Web3.py update:
```python
from web3 import Web3

# Contract ABI (minimal for disbursement)
CONTRACT_ABI = [
    {
        "inputs": [
            {"name": "recipient", "type": "address"},
            {"name": "amount", "type": "uint256"},
            {"name": "sessionId", "type": "string"}
        ],
        "name": "disburseReward",
        "outputs": [{"name": "", "type": "bool"}],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"name": "user", "type": "address"}],
        "name": "getRemainingDailyLimit",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    }
]

# Initialize contract
contract_address = "YOUR_DEPLOYED_CONTRACT_ADDRESS"
contract = w3.eth.contract(address=contract_address, abi=CONTRACT_ABI)

# Call disbursement
tx_hash = contract.functions.disburseReward(
    wallet_address,
    amount_wei,
    session_id
).transact({'from': AUTHORIZED_SERVER_ADDRESS})

# Check remaining daily limit
remaining = contract.functions.getRemainingDailyLimit(wallet_address).call()
```

CONTRACT VERIFICATION (Optional):
=================================

After deployment on Celo Explorer:
1. Go to https://explorer.celo.org/
2. Find your contract transaction
3. Click "Verify & Publish"
4. Select compiler version matching Remix
5. Paste contract code
6. Set "optimization" to "No"

SECURITY CHECKLIST:
===================
[x] Owner is a secure hardware wallet or multisig
[x] Daily limits are appropriate
[x] Backend server is authorized
[x] Contract is funded
[x] Private keys are NOT stored in frontend

For GoodBuilder Program:
- Save your deployment tx hash
- Document contract address
- Show the events in explorer
"""

# Pre-calculated values for common daily limits (in wei)
DAILY_LIMIT_VALUES = {
    "100 G$": "100000000000000000000",
    "500 G$": "500000000000000000000",
    "1000 G$": "1000000000000000000000",
    "5000 G$": "5000000000000000000000",
    "10000 G$": "10000000000000000000000",
}

# Contract info
CONTRACT_INFO = {
    "name": "GamesRewards",
    "version": "1.0.0",
    "network": "Celo Mainnet",
    "chain_id": 42220,
    "rpc_url": "https://forno.celo.org",
    "token_address": "0x62B8B11039FcfE5aB0C56E502b1C372A3d2a9c7A",
    "explorer": "https://explorer.celo.org",
}

if __name__ == "__main__":
    print("=" * 60)
    print("GamesRewards Smart Contract Deployment Guide")
    print("=" * 60)
    print()
    print("CONTRACT INFO:")
    for key, value in CONTRACT_INFO.items():
        print(f"  {key}: {value}")
    print()
    print("DAILY LIMIT EXAMPLES (wei):")
    for display, wei in DAILY_LIMIT_VALUES.items():
        print(f"  {display} = {wei}")
    print()
    print("=" * 60)
    print("Follow the deployment steps in the docstring above")
    print("=" * 60)
