# Referral Program Fix - Technical Proposal

## ✅ IMPLEMENTATION STATUS: ALL PHASES COMPLETED

### Phase 1: ✅ COMPLETED - Emergency Fix (Reconciliation)
- ✅ Created `reconcile_stuck_referrals()` function
- ✅ Created admin endpoint `/api/admin/referral/reconcile-stuck`
- ✅ Created standalone script `scripts/reconcile_stuck_referrals.py`
- ✅ Created SQL fix script `sql/fix_all_stuck_pending_face_verification_referrals.sql`

### Phase 2: ✅ COMPLETED - Auto-Trigger after UBI Claim
- ✅ Created `verify_and_disburse_referral()` function
- ✅ Integrated trigger in `/api/claims/v2/confirm` (after successful UBI claim)
- ✅ Added comprehensive verification logic (DB flag → GoodMarket attribution → On-chain check)

### Phase 3: ✅ COMPLETED - Relaxed Attribution Rules
- ✅ Extended `STRICT_ATTRIBUTION_WINDOW_SECONDS` from 30 min to 7 days
- ✅ Added env var `GOODMARKET_ATTRIBUTION_STRICT_WINDOW_SECONDS` for tuning
- ✅ Duplicate protection already implemented in Phase 1 fixes

---

## Bug Fixes Also Completed

### Duplicate Payment Bug (Critical!)
- ✅ `log_reward()` - now checks for existing completed rewards before inserting
- ✅ `increment_referrer_stats()` - now prevents double counting
- ✅ `process_referral_disbursement()` - now checks `_is_referral_already_disbursed()` before sending blockchain txs
- ✅ `process_pending_disbursements()` - now tracks processed referrals to avoid duplicates
- ✅ Admin endpoint now accepts `completed` status for re-processing

---

## Files Modified

| File | Changes |
|------|---------|
| `referral_program/referral_service.py` | Added `verify_and_disburse_referral()`, `reconcile_stuck_referrals()`, duplicate protection |
| `routes.py` | Added referral trigger in claim confirm, admin reconciliation endpoint |
| `goodmarket_attribution_backfill.py` | Extended attribution window to 7 days |
| `scripts/reconcile_stuck_referrals.py` | NEW - standalone reconciliation script |
| `sql/fix_all_stuck_pending_face_verification_referrals.sql` | NEW - SQL fix for existing data |

---

## How to Deploy

### Step 1: Fix Existing Stuck Data

Run in Supabase SQL Editor:
```sql
-- File: sql/fix_all_stuck_pending_face_verification_referrals.sql
```

### Step 2: Deploy Code

```bash
git add .
git commit -m "fix: complete referral program overhaul - phases 1,2,3 implemented"
git push
```

### Step 3: Trigger Reconciliation (Optional)

After deployment, call the admin endpoint:
```
POST /api/admin/referral/reconcile-stuck?hours=1
```

Or run the script manually:
```bash
python scripts/reconcile_stuck_referrals.py
```

### Step 4: Setup Cron Job (Optional)

For automatic reconciliation, setup a cron job to run hourly:
```bash
0 * * * * cd /path/to/project && python scripts/reconcile_stuck_referrals.py >> /var/log/referral_reconcile.log 2>&1
```

---

## New Features

### Admin Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/admin/referral/reconcile-stuck` | POST | Fix stuck referrals |
| `/api/admin/referral/disburse-by-code` | POST | Disburse specific referral (now works for completed status too) |
| `/api/admin/referral/process-pending` | POST | Process all pending disbursements |

### New Functions

| Function | Location | Description |
|----------|----------|-------------|
| `verify_and_disburse_referral()` | referral_service.py | Trigger disbursement after verification/claim |
| `reconcile_stuck_referrals()` | referral_service.py | Fix all stuck referrals |
| `_is_referral_already_disbursed()` | referral_service.py | Check if referral was already paid |

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GOODMARKET_ATTRIBUTION_STRICT_WINDOW_SECONDS` | 604800 (7 days) | Attribution window for verification |

To change back to 30 minutes:
```bash
vercel env add GOODMARKET_ATTRIBUTION_STRICT_WINDOW_SECONDS
# Enter: 1800
```

---

## Testing Checklist

After deployment, test these scenarios:

1. ✅ New user signs up with referral code → claims UBI → referral should auto-disburse
2. ✅ Existing user who already claimed UBI → trigger reconciliation → referral should fix
3. ✅ Click "Disburse" twice → should NOT send duplicate payments
4. ✅ Referral with verified user stuck in pending → should be auto-fixed

---

## Monitoring

Check these logs after deployment:
- `Referral disbursed after claim:` - shows successful auto-disbursement
- `No pending referral for claiming wallet:` - normal for users without referrals
- `Referral not disbursed yet:` - user not yet verified, normal
