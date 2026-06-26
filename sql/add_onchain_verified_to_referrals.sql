-- Add onchain_verified column to referrals table for manual approval tracking
-- This column tracks whether admin has manually verified on-chain claim via CeloScan

ALTER TABLE referrals 
ADD COLUMN IF NOT EXISTS onchain_verified BOOLEAN DEFAULT NULL;

-- Add admin_verified_at timestamp to track when admin approved
ALTER TABLE referrals 
ADD COLUMN IF NOT EXISTS admin_verified_at TIMESTAMPTZ DEFAULT NULL;

-- Add approved_by_wallet to track which admin approved
ALTER TABLE referrals 
ADD COLUMN IF NOT EXISTS approved_by_wallet TEXT DEFAULT NULL;

-- Add approved_by_ip for additional tracking
ALTER TABLE referrals 
ADD COLUMN IF NOT EXISTS approved_by_ip TEXT DEFAULT NULL;

-- Create index for faster queries on pending referrals
CREATE INDEX IF NOT EXISTS idx_referrals_pending_approval 
ON referrals(status, onchain_verified) 
WHERE status = 'pending_face_verification' AND onchain_verified IS NULL;

-- Comments
COMMENT ON COLUMN referrals.onchain_verified IS 'TRUE = admin confirmed on-chain G$ claim via CeloScan. NULL = still pending admin verification.';
COMMENT ON COLUMN referrals.admin_verified_at IS 'Timestamp when admin verified on-chain claim and approved disbursement.';
COMMENT ON COLUMN referrals.approved_by_wallet IS 'Wallet address of admin who approved the referral.';
