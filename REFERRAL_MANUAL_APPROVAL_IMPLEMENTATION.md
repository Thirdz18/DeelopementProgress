# Referral Program - Manual Approval Implementation

## Summary

This implementation converts the referral program from an auto-disbursement model to a **fully manual approval workflow**. Admin must verify on-chain claims via CeloScan before approving and disbursing rewards.

---

## Changes Made

### 1. Removed Auto-Disbursement Triggers

**File: `routes.py`**

- **Line ~276-280**: Disabled auto-disbursement trigger in `/api/claims/v2/confirm`
- **Line ~1661-1701**: Disabled auto-disbursement in `/verify-ubi` route
  - Removed all calls to `_disburse_referral_rewards()`
  - Removed all calls to `claim_pending_referral_for_disbursement()`
  - Now only logs referral as "PENDING MANUAL APPROVAL"

### 2. New Database Columns

**File: `sql/add_onchain_verified_to_referrals.sql`**

New columns in `referrals` table:
- `onchain_verified` (BOOLEAN) - Tracks if admin verified on-chain claim
- `admin_verified_at` (TIMESTAMPTZ) - When admin approved
- `approved_by_wallet` (TEXT) - Admin wallet address
- `approved_by_ip` (TEXT) - Admin IP address

Run this SQL to apply:
```bash
psql -f sql/add_onchain_verified_to_referrals.sql
```

### 3. New API Endpoints

**File: `routes.py`**

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/admin/referral/pending` | GET | Get all pending referrals awaiting approval |
| `/api/admin/referral/<code>` | GET | Get detailed info for a specific referral |
| `/api/admin/referral/completed` | GET | Get all completed/verified referrals |
| `/api/admin/referral/approve` | POST | **MAIN APPROVAL ENDPOINT** - Mark verified + disburse |

### 4. Admin Dashboard UI Updates

**File: `templates/admin_dashboard.html`**

New "Referral Management" section with:

#### Pending Referrals Panel (Yellow border)
- List of all referrals awaiting admin action
- Shows: Referral Code, Referee Wallet, Referrer Wallet, Status, Created Date
- "👁️ View" button to open detail modal

#### Verification Instructions Box
```
1. Look at PENDING REFERRALS below
2. Click 👁️ View to see referral details
3. Check referee's wallet on CeloScan to verify G$ claim
4. If verified, click ✅ Approve & Disburse
5. Rewards sent: Referrer 1,000 G$ | Referee 500 G$
```

#### Completed Referrals Panel (Green border)
- List of all approved and disbursed referrals
- Shows: Referral Code, Referee, Referrer, Status, Completed Date, TX Link

#### Detail Modal (when clicking "👁️ View")
- Full referral details with wallet addresses
- Direct links to CeloScan for referee's wallet
- Rewards breakdown (Referrer: 1000 G$, Referee: 500 G$)
- "✅ Approve & Disburse Rewards" button (green, prominent)

### 5. New JavaScript Functions

**File: `templates/admin_dashboard.html`**

| Function | Description |
|----------|-------------|
| `loadPendingReferrals()` | Fetches and displays pending referrals list |
| `loadCompletedReferrals()` | Fetches and displays completed referrals |
| `viewReferralDetail(code)` | Opens modal with full referral details |
| `approveReferral(code)` | Calls API to approve and disburse rewards |
| `closeReferralModal()` | Closes the detail modal |

---

## New Workflow

```
┌─────────────────────────────────────────────────────────────────────┐
│                        REFERRAL WORKFLOW                            │
└─────────────────────────────────────────────────────────────────────┘

1. USER SIGNUP
   ├── User A (Referrer) generates referral code
   └── User B (Referee) signs up using referral code
       └── Referral created with status: "pending_face_verification"

2. ADMIN VERIFICATION (via Admin Dashboard)
   ├── Admin sees pending referral in list
   ├── Admin clicks "👁️ View"
   ├── Modal opens showing referee's wallet address
   ├── Admin opens CeloScan to check wallet
   └── Admin verifies if G$ tokens were claimed

3. ADMIN APPROVAL
   ├── If verified on CeloScan → Admin clicks "✅ Approve & Disburse"
   └── If NOT verified → Admin does nothing (waits)

4. DISBURSEMENT (automatic after approval)
   ├── Referrer wallet: +1,000 G$
   ├── Referee wallet: +500 G$
   └── Status changes to: "completed"

5. REFERRAL MOVES TO COMPLETED LIST
   └── Admin can see verified/disbursed referral in completed tab
```

---

## API Details

### POST /api/admin/referral/approve

**Request:**
```json
{
  "referral_code": "ABC12345"
}
```

**Success Response (200):**
```json
{
  "success": true,
  "referral_code": "ABC12345",
  "referrer_wallet": "0x...",
  "referee_wallet": "0x...",
  "referrer_reward": 1000.0,
  "referee_reward": 500.0,
  "result": {
    "success": true,
    "referrer_status": "completed",
    "referee_status": "completed"
  }
}
```

**Error Response (400):**
```json
{
  "success": false,
  "error": "No pending referral found for code ABC12345",
  "status": "completed"
}
```

---

## Files Modified

| File | Changes |
|------|---------|
| `routes.py` | Disabled auto-triggers, added new API endpoints |
| `templates/admin_dashboard.html` | New UI section, modal, JavaScript functions |
| `sql/add_onchain_verified_to_referrals.sql` | **NEW** - Database migration |

---

## Files Created

| File | Purpose |
|------|---------|
| `sql/add_onchain_verified_to_referrals.sql` | SQL migration for new columns |

---

## Deployment Steps

1. **Run the SQL migration:**
   ```bash
   # Connect to Supabase/PostgreSQL and run:
   psql -f sql/add_onchain_verified_to_referrals.sql
   ```

2. **Deploy the code changes:**
   ```bash
   git add .
   git commit -m "feat: implement manual referral approval workflow"
   git push
   ```

3. **Test the workflow:**
   - Go to Admin Dashboard → Referral Management
   - Verify the new UI appears correctly
   - Test the approval flow with a test referral

---

## Security Notes

- All approval endpoints require admin authentication (`@admin_required`)
- Admin wallet and IP are logged for every approval action
- Duplicate disbursement is prevented by the existing logic in `process_referral_disbursement()`
- No automatic triggers means full control over when rewards are disbursed

---

## Future Improvements (Optional)

1. Add "Reject" button for referrals that cannot be verified
2. Add notes/comments field for admin to document verification decisions
3. Add email/Slack notification when new pending referrals appear
4. Add bulk approval feature for multiple referrals at once
