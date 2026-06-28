-- ============================================================================
-- P2P G$ Trading — offchain tables (Supabase / PostgreSQL)
--
-- On-chain (P2PEscrow.sol) is the source of truth for G$ custody and the
-- listing/order amounts. These tables hold everything that lives OFF-chain:
-- price, payment methods, chat, proof of payment, and dispute/review state.
--
-- Run this in the Supabase SQL editor before enabling the P2P feature.
-- All tables mirror their on-chain counterpart via `onchain_id`.
-- ============================================================================

-- ── Sell ads (mirror of an on-chain listing; price + terms live here) ───────
CREATE TABLE IF NOT EXISTS p2p_listings (
    id              BIGSERIAL PRIMARY KEY,
    onchain_id      BIGINT,                       -- listingId in P2PEscrow
    seller_wallet   VARCHAR(42) NOT NULL,
    total_gd        NUMERIC NOT NULL,             -- G$ locked (human units)
    min_order_gd    NUMERIC NOT NULL DEFAULT 1000,
    price_usdt      NUMERIC NOT NULL,             -- seller's price per 1 G$, in USDT
    fiat_currency   VARCHAR(8),                   -- optional, e.g. PHP, NGN
    fiat_rate       NUMERIC,                      -- optional USDT->fiat rate the seller quotes
    terms           TEXT,
    status          VARCHAR(16) NOT NULL DEFAULT 'active', -- active|cancelled|sold_out
    create_tx_hash  VARCHAR(66),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_p2p_listings_seller ON p2p_listings(seller_wallet);
CREATE INDEX IF NOT EXISTS idx_p2p_listings_status ON p2p_listings(status);
CREATE INDEX IF NOT EXISTS idx_p2p_listings_onchain ON p2p_listings(onchain_id);

-- ── Seller payment methods (visible to buyers) ──────────────────────────────
CREATE TABLE IF NOT EXISTS p2p_payment_methods (
    id            BIGSERIAL PRIMARY KEY,
    seller_wallet VARCHAR(42) NOT NULL,
    kind          VARCHAR(24) NOT NULL,  -- fiat_bank|mobile_ewallet|minipay|usdt|tron|btc|other
    label         VARCHAR(64),           -- e.g. "GCash", "Maya", "USDT (TRC20)"
    details       JSONB NOT NULL DEFAULT '{}'::jsonb, -- acct no / address / notes (no secrets)
    active        BOOLEAN NOT NULL DEFAULT TRUE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_p2p_pm_seller ON p2p_payment_methods(seller_wallet);

-- ── Orders (mirror of an on-chain order) ────────────────────────────────────
CREATE TABLE IF NOT EXISTS p2p_orders (
    id                BIGSERIAL PRIMARY KEY,
    onchain_id        BIGINT,                       -- orderId in P2PEscrow
    listing_id        BIGINT REFERENCES p2p_listings(id),
    listing_onchain_id BIGINT,
    buyer_wallet      VARCHAR(42) NOT NULL,
    seller_wallet     VARCHAR(42) NOT NULL,
    amount_gd         NUMERIC NOT NULL,             -- G$ reserved (human units)
    pay_amount        NUMERIC NOT NULL,             -- computed at order time
    pay_currency      VARCHAR(8) NOT NULL,          -- USDT or fiat code
    payment_method_id BIGINT REFERENCES p2p_payment_methods(id),
    -- open|paid|released|cancelled|disputed|seller_rejected|owner_released|owner_refunded
    status            VARCHAR(20) NOT NULL DEFAULT 'open',
    reject_reason     TEXT,                         -- why the seller rejected
    reviewed_by       VARCHAR(42),                  -- owner wallet (P2P_KEY) that reviewed
    deadline          TIMESTAMPTZ,                  -- payment window end
    open_tx_hash      VARCHAR(66),
    paid_tx_hash      VARCHAR(66),
    release_tx_hash   VARCHAR(66),
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_p2p_orders_buyer ON p2p_orders(buyer_wallet);
CREATE INDEX IF NOT EXISTS idx_p2p_orders_seller ON p2p_orders(seller_wallet);
CREATE INDEX IF NOT EXISTS idx_p2p_orders_status ON p2p_orders(status);
CREATE INDEX IF NOT EXISTS idx_p2p_orders_onchain ON p2p_orders(onchain_id);

-- ── Chat (offchain, realtime) ───────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS p2p_messages (
    id            BIGSERIAL PRIMARY KEY,
    order_id      BIGINT REFERENCES p2p_orders(id),
    sender_wallet VARCHAR(42) NOT NULL,
    body          TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_p2p_messages_order ON p2p_messages(order_id);

-- ── Proof of payment (image converted via backend ImgBB key) ────────────────
CREATE TABLE IF NOT EXISTS p2p_proofs (
    id              BIGSERIAL PRIMARY KEY,
    order_id        BIGINT REFERENCES p2p_orders(id),
    uploader_wallet VARCHAR(42) NOT NULL,
    image_url       TEXT,        -- ImgBB URL (backend-managed key)
    reference       TEXT,        -- txid / reference number
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_p2p_proofs_order ON p2p_proofs(order_id);

-- ── Disputes / admin review ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS p2p_disputes (
    id              BIGSERIAL PRIMARY KEY,
    order_id        BIGINT REFERENCES p2p_orders(id),
    raised_by       VARCHAR(42) NOT NULL,  -- buyer/seller wallet, or 'seller_rejected'
    reason          TEXT,
    status          VARCHAR(20) NOT NULL DEFAULT 'open', -- open|resolved_buyer|resolved_seller
    resolved_by     VARCHAR(42),           -- owner wallet (P2P_KEY)
    resolve_tx_hash VARCHAR(66),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    resolved_at     TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_p2p_disputes_order ON p2p_disputes(order_id);
CREATE INDEX IF NOT EXISTS idx_p2p_disputes_status ON p2p_disputes(status);

-- ── Row Level Security ──────────────────────────────────────────────────────
-- The backend uses the service-role key for writes; enable RLS so the anon key
-- cannot tamper with rows directly. Adjust policies to your auth model.
ALTER TABLE p2p_listings        ENABLE ROW LEVEL SECURITY;
ALTER TABLE p2p_payment_methods ENABLE ROW LEVEL SECURITY;
ALTER TABLE p2p_orders          ENABLE ROW LEVEL SECURITY;
ALTER TABLE p2p_messages        ENABLE ROW LEVEL SECURITY;
ALTER TABLE p2p_proofs          ENABLE ROW LEVEL SECURITY;
ALTER TABLE p2p_disputes        ENABLE ROW LEVEL SECURITY;

-- Public can read active listings + payment methods (the "Available ads" feed).
DROP POLICY IF EXISTS p2p_listings_read ON p2p_listings;
CREATE POLICY p2p_listings_read ON p2p_listings FOR SELECT USING (true);
DROP POLICY IF EXISTS p2p_pm_read ON p2p_payment_methods;
CREATE POLICY p2p_pm_read ON p2p_payment_methods FOR SELECT USING (true);
