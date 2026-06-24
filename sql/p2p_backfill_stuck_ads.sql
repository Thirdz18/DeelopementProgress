-- P2P Backfill Script for Stuck Ads
-- 
-- This script manually updates ads that are stuck at 'submitted' status.
-- Use this as a fallback if the backend /api/indexer/backfill endpoint is unavailable.
--
-- IMPORTANT: Only ads that have an ad_id_onchain value can be verified.
-- Ads without ad_id_onchain cannot be verified and should be manually reviewed.
--
-- Run this in Supabase SQL Editor

BEGIN;

-- 1. Check current status of stuck ads
SELECT 
    status,
    onchain_status,
    COUNT(*) as count
FROM public.p2p_orders
GROUP BY status, onchain_status
ORDER BY count DESC;

-- 2. Preview: Show stuck ads (submitted status but no ad_open_block)
SELECT 
    order_id,
    ad_id_onchain,
    seller_wallet,
    onchain_status,
    created_at,
    ad_open_tx
FROM public.p2p_orders
WHERE onchain_status = 'submitted'
  AND ad_id_onchain IS NOT NULL
LIMIT 50;

-- 3. IMPORTANT: Read the warnings above first!
-- 
-- To fix stuck ads that were successfully mined on-chain:
-- You need to verify the ad exists on-chain first using the ad_id_onchain value.
-- Then update manually like this:
--
-- UPDATE public.p2p_orders
-- SET 
--     onchain_status = 'open',
--     ad_open_block = <block_number>,
--     onchain_confirmed_at = NOW()
-- WHERE order_id = 'YOUR_ORDER_ID';

-- 4. If you want to mark ALL submitted ads as 'open' (use with caution!):
-- This assumes all submitted ads were successfully mined on-chain.
-- Only do this if you're sure the transactions were confirmed.
--
-- SELECT COUNT(*) as will_update FROM public.p2p_orders
-- WHERE onchain_status = 'submitted' AND ad_id_onchain IS NOT NULL;

COMMIT;
