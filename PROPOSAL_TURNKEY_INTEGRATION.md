# PROPOSAL: Turnkey Wallet Integration for GoodMarket

## Overview
Add Turnkey wallet creation option alongside existing WalletConnect and Injected Wallet options in the homepage wallet modal. This allows users to create a new self-custodial wallet directly within GoodMarket.

---

## 📋 Requirements Summary

### Current State
- Homepage has "Get Started" button → opens wallet modal
- Modal currently contains:
  1. **WalletConnect** - External wallet QR/linking
  2. **Injected Wallet** - MetaMask/Trust/MiniPay detection

### Desired State
- Add **Turnkey Wallet** as third option in the same modal
- **DO NOT remove** existing WalletConnect and Injected Wallet integrations
- New users can create a new wallet via Turnkey MPC infrastructure

---

## 🔧 Implementation Plan

### Phase 1: Backend Setup

#### 1.1 Install Turnkey SDK
```
pip install turnkey
```

#### 1.2 Add Environment Variables (config.py)
```python
TURNKEY_API_PUBLIC_KEY = os.getenv('TURNKEY_API_PUBLIC_KEY', '')
TURNKEY_API_PRIVATE_KEY = os.getenv('TURNKEY_API_PRIVATE_KEY', '')
TURNKEY_ORGANIZATION_ID = os.getenv('TURNKEY_ORGANIZATION_ID', '')
```

#### 1.3 Create Turnkey Service Module
New file: `turnkey_service.py`
- Wallet creation via Turnkey API
- User registration with Turnkey
- Export wallet functionality (optional)

#### 1.4 Add API Routes
New endpoints in `routes.py`:
- `POST /api/turnkey/create-wallet` - Create new wallet for user
- `GET /api/turnkey/export-wallet` - Export wallet details (with auth)

---

### Phase 2: Frontend Changes

#### 2.1 Modify Homepage Modal (homepage.html)
Location: Lines 2117-2126 (walletOptions section)

**Add new button alongside WalletConnect:**
```html
<!-- Existing -->
<button class="wallet-option-card wc-option" onclick="showWalletConnectOptions()">
    ...
</button>

<!-- NEW: Turnkey Wallet Option -->
<button class="wallet-option-card turnkey-option" onclick="showTurnkeyOptions()">
    <div class="option-icon">🔐</div>
    <div class="option-text">
        <div class="option-title">Create New Wallet</div>
        <p class="option-desc">Generate a secure wallet with Turnkey</p>
    </div>
    <span class="option-arrow">→</span>
</button>
```

#### 2.2 Add Turnkey UI Flow
Add new modal section for Turnkey wallet creation:
- Email/username input
- Password input (for wallet encryption)
- Loading state during wallet creation
- Success state showing wallet address

#### 2.3 Add JavaScript Functions
```javascript
// New functions to add
function showTurnkeyOptions() { ... }
async function createTurnkeyWallet() { ... }
async function exportTurnkeyWallet() { ... }
```

---

### Phase 3: User Flow

```
┌─────────────────────────────────────────────────────────────┐
│                     WALLET MODAL                             │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────────┐  ┌─────────────────┐                  │
│  │ 🔗 WalletConnect │  │ 🔐 Create Wallet │                  │
│  │ (Link existing)  │  │  (Turnkey MPC)   │                  │
│  └─────────────────┘  └─────────────────┘                  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

#### Turnkey Wallet Creation Flow:
1. User clicks "Create New Wallet"
2. Modal shows email/password form
3. User enters details
4. Backend creates wallet via Turnkey API
5. Returns encrypted wallet credentials to frontend
6. User downloads/saves wallet backup
7. Wallet address stored for session/login

---

## 📁 Files to Modify/Create

| File | Action | Changes |
|------|--------|---------|
| `config.py` | Modify | Add Turnkey env vars |
| `routes.py` | Modify | Add Turnkey API routes |
| `homepage.html` | Modify | Add Turnkey UI option |
| `turnkey_service.py` | Create | Turnkey API wrapper |
| `.env.example` | Create | Document required env vars |

---

## 🔒 Security Considerations

1. **Never store private keys in plain text** - Turnkey MPC handles this
2. **User authentication** - Tie wallet creation to user account/session
3. **Rate limiting** - Prevent abuse of wallet creation endpoint
4. **HTTPS only** - Ensure all API calls are encrypted

---

## 📝 Environment Variables Required

```bash
# Turnkey Configuration
TURNKEY_API_PUBLIC_KEY=tk_live_xxxxx
TURNKEY_API_PRIVATE_KEY=tk_live_xxxxx
TURNKEY_ORGANIZATION_ID=org_xxxxx
```

---

## ⏱️ Estimated Timeline

| Phase | Task | Complexity |
|-------|------|------------|
| 1 | Backend setup (SDK, config, service) | Medium |
| 2 | API routes | Medium |
| 3 | Frontend UI integration | Low |
| 4 | Testing | Low |

**Total Estimated Time: 2-3 hours**

---

## ✅ Success Criteria

- [ ] Turnkey wallet option visible in modal (alongside WalletConnect)
- [ ] Users can create new wallet without external wallet
- [ ] Existing WalletConnect still works
- [ ] Existing Injected Wallet detection still works
- [ ] Wallet address stored and usable for login

---

## 🚫 NOT In Scope (for this task)

- Wallet export functionality
- Wallet backup/recovery flow
- Multi-chain support beyond Celo
- Mobile-specific optimizations
- Wallet recovery/forgot password

---

## Questions for User Review

1. Should the Turnkey wallet creation require email, or just generate anonymously?
2. Do you want wallet backup/download functionality included?
3. What should be the UX after successful wallet creation (auto-login or manual)?

---

**Status: ✅ IMPLEMENTED**

## Implementation Summary

### Files Created/Modified:

| File | Action | Changes |
|------|--------|---------|
| `config.py` | Modified | Added Turnkey config environment variables |
| `routes.py` | Modified | Added Turnkey API endpoints |
| `templates/homepage.html` | Modified | Added Turnkey UI buttons in wallet modal |
| `templates/wallet.html` | Modified | Added Export Wallet button in Settings |
| `turnkey_service.py` | **Created** | Turnkey SDK wrapper service |
| `requirements.txt` | Modified | Added Turnkey SDK packages |
| `.env.example` | Modified | Added Turnkey env vars documentation |

### API Endpoints Added:

- `POST /api/turnkey/create-wallet` - Create new wallet
- `POST /api/turnkey/export-wallet` - Export wallet bundle (auth required)
- `GET /api/turnkey/get-wallet` - Get wallet info (auth required)
- `GET /api/turnkey/status` - Check Turnkey configuration status

### UI Changes:

**Homepage Modal:**
- ✅ Added "Login with Email" button (for existing Turnkey users)
- ✅ Added "Create New Wallet" button (for new users)
- ✅ Existing WalletConnect option preserved

**Wallet Settings:**
- ✅ Added "Turnkey Wallet" section (only visible for Turnkey users)
- ✅ Added "Export Wallet Bundle" button

### Environment Variables Required:

```bash
TURNKEY_API_PUBLIC_KEY=tk_live_xxxxx
TURNKEY_API_PRIVATE_KEY=tk_live_xxxxx
TURNKEY_ORGANIZATION_ID=org_xxxxx
TURNKEY_API_BASE_URL=https://api.turnkey.com  # optional, default
```
