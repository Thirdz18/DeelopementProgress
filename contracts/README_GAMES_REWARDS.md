# GamesRewards Smart Contract Guide

## Overview

This folder contains the smart contract for minigames G$ rewards disbursement, designed for the GoodBuilder Season 4 program.

## Files

| File | Description |
|------|-------------|
| `GamesRewards.sol` | Main smart contract |
| `deploy_games_rewards.py` | Deployment guide for Remix IDE |
| `games_rewards_service.py` | Python service for contract interaction |

## Smart Contract Features

### Security Features
- ✅ **Owner-only management** - Only owner can manage settings
- ✅ **Authorized disbursers** - Backend server must be authorized
- ✅ **Daily limits** - Per-user daily claim limits
- ✅ **Emergency pause** - Owner can pause all operations
- ✅ **Event logging** - All disbursements are logged on-chain

### Benefits over Direct Transfer

| Aspect | Direct Transfer (Old) | Smart Contract (New) |
|--------|----------------------|----------------------|
| Private Key | Stored on server | Not needed for disbursement |
| Access Control | None | Role-based |
| Daily Limits | Database only | Enforced on-chain |
| Audit Trail | Database logs | On-chain events |
| Pause Ability | None | Owner can pause |

## Deployment Steps

### 1. Prepare in Remix IDE

1. Go to https://remix.ethereum.org
2. Create new file: `GamesRewards.sol`
3. Copy contents from `GamesRewards.sol` in this folder
4. Compile with Solidity ^0.8.19

### 2. Deploy Contract

**Environment:** Injected Provider (MetaMask)  
**Network:** Celo Mainnet (Chain ID: 42220)

**Constructor Arguments:**
```
_token:        0x62B8B11039FcfE5aB0C56E502b1C372A3d2a9c7A
_owner:        YOUR_ADMIN_WALLET_ADDRESS
_dailyLimit:   1000000000000000000000 (1000 G$ with 18 decimals)
```

### 3. Configure After Deployment

1. **Copy Contract Address** - Save the deployed address
2. **Fund Contract** - Transfer G$ to contract address
3. **Authorize Server** - Call `setAuthorizedDisburser(your_server_address, true)`
4. **Update Backend** - Replace GAMES_KEY with contract address

## Daily Limit Values (with 18 decimals)

```
100 G$   = 100000000000000000000
500 G$   = 500000000000000000000
1000 G$  = 1000000000000000000000
5000 G$  = 5000000000000000000000
10000 G$ = 10000000000000000000000
```

## Contract Functions

### For Backend (Authorized Disbursers)

```solidity
// Disburse reward to user
disburseReward(address recipient, uint256 amount, string sessionId)

// Batch disburse (gas efficient)
batchDisburse(address[] recipients, uint256[] amounts, string[] sessionIds)
```

### View Functions

```solidity
// Get remaining daily limit for user
getRemainingDailyLimit(address user) → uint256

// Get user statistics
getUserStats(address user) → (total, dailyToday, lastClaim)

// Get contract balance
getContractBalance() → uint256
```

### Owner Functions

```solidity
// Manage authorized disbursers
setAuthorizedDisburser(address disburser, bool authorized)

// Update daily limit
updateDailyLimit(uint256 newLimit)

// Emergency pause
setPaused(bool paused)

// Withdraw tokens (emergency only)
withdrawTokens(address recipient, uint256 amount)
```

## Backend Integration

### Replace Old Code

**Before (Direct Transfer):**
```python
# Old: Uses GAMES_KEY directly
result = await blockchain_service.disburse_game_reward(...)
```

**After (Contract):**
```python
# New: Uses smart contract
from contracts.games_rewards_service import GamesRewardsContractService

service = GamesRewardsContractService()
result = await service.disburse_reward(wallet, amount, game_type, session_id)
```

### Environment Variables

```bash
# Add these to your .env
GAMES_REWARDS_CONTRACT=0x... (deployed contract address)
SERVER_WALLET_ADDRESS=0x... (your server's wallet)
SERVER_PRIVATE_KEY=0x... (server's private key)
```

## Security Checklist

- [ ] Owner is a secure wallet (hardware wallet recommended)
- [ ] Daily limit set appropriately (1000-10000 G$ recommended)
- [ ] Server wallet authorized as disburser
- [ ] Contract funded with sufficient G$
- [ ] Private keys secured (not in code/repository)
- [ ] Events monitored for suspicious activity

## For GoodBuilder Submission

### Documentation to Prepare

1. **Contract Address** - Deployed contract on Celo mainnet
2. **Transaction Hash** - Deployment transaction
3. **Contract Code** - Verified on Celo Explorer
4. **Test Results** - Screenshots of successful disbursements
5. **Architecture Diagram** - Show the flow

### What to Highlight

1. Security improvements over direct transfer
2. On-chain transparency (events)
3. Access control mechanisms
4. Gas efficiency (batch disbursement)
5. Emergency pause functionality

## Support

For questions about this contract:
- Review the contract code comments
- Check deployment guide in `deploy_games_rewards.py`
- Monitor events on Celo Explorer

---

**GoodBuilder Season 4** 🚀
