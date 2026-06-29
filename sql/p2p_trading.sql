-- ============================================================================
-- P2P G$ Trading — offchain tables (Supabase / PostgreSQL)
--
-- On-chain (P2PEscrow.sol) is the source of truth for G$ custody and the
-- listing/order amounts. These tables hold everything that lives OFF-chain:
-- price, payment methods, chat, proof of payment, and dispute/review state.
--
-- Safe to re-run: every table uses CREATE TABLE IF NOT EXISTS *and* an explicit
-- ADD COLUMN IF NOT EXISTS block, so a pre-existing/partial table (e.g. from an
-- earlier run) is upgraded in place instead of failing on a missing column.
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
-- Upgrade a pre-existing table to the full column set.
ALTER TABLE p2p_listings ADD COLUMN IF NOT EXISTS onchain_id     BIGINT;
ALTER TABLE p2p_listings ADD COLUMN IF NOT EXISTS seller_wallet  VARCHAR(42);
ALTER TABLE p2p_listings ADD COLUMN IF NOT EXISTS total_gd       NUMERIC;
ALTER TABLE p2p_listings ADD COLUMN IF NOT EXISTS min_order_gd   NUMERIC DEFAULT 1000;
ALTER TABLE p2p_listings ADD COLUMN IF NOT EXISTS price_usdt     NUMERIC;
ALTER TABLE p2p_listings ADD COLUMN IF NOT EXISTS fiat_currency  VARCHAR(8);
ALTER TABLE p2p_listings ADD COLUMN IF NOT EXISTS fiat_rate      NUMERIC;
ALTER TABLE p2p_listings ADD COLUMN IF NOT EXISTS terms          TEXT;
ALTER TABLE p2p_listings ADD COLUMN IF NOT EXISTS status         VARCHAR(16) DEFAULT 'active';
ALTER TABLE p2p_listings ADD COLUMN IF NOT EXISTS create_tx_hash VARCHAR(66);
ALTER TABLE p2p_listings ADD COLUMN IF NOT EXISTS created_at     TIMESTAMPTZ DEFAULT now();
ALTER TABLE p2p_listings ADD COLUMN IF NOT EXISTS updated_at     TIMESTAMPTZ DEFAULT now();
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
ALTER TABLE p2p_payment_methods ADD COLUMN IF NOT EXISTS seller_wallet VARCHAR(42);
ALTER TABLE p2p_payment_methods ADD COLUMN IF NOT EXISTS kind          VARCHAR(24);
ALTER TABLE p2p_payment_methods ADD COLUMN IF NOT EXISTS label         VARCHAR(64);
ALTER TABLE p2p_payment_methods ADD COLUMN IF NOT EXISTS details       JSONB DEFAULT '{}'::jsonb;
ALTER TABLE p2p_payment_methods ADD COLUMN IF NOT EXISTS active        BOOLEAN DEFAULT TRUE;
ALTER TABLE p2p_payment_methods ADD COLUMN IF NOT EXISTS created_at    TIMESTAMPTZ DEFAULT now();
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
ALTER TABLE p2p_orders ADD COLUMN IF NOT EXISTS onchain_id         BIGINT;
ALTER TABLE p2p_orders ADD COLUMN IF NOT EXISTS listing_id         BIGINT;
ALTER TABLE p2p_orders ADD COLUMN IF NOT EXISTS listing_onchain_id BIGINT;
ALTER TABLE p2p_orders ADD COLUMN IF NOT EXISTS buyer_wallet       VARCHAR(42);
ALTER TABLE p2p_orders ADD COLUMN IF NOT EXISTS seller_wallet      VARCHAR(42);
ALTER TABLE p2p_orders ADD COLUMN IF NOT EXISTS amount_gd          NUMERIC;
ALTER TABLE p2p_orders ADD COLUMN IF NOT EXISTS g_dollar_amount    NUMERIC; -- legacy alias used by early deployments
ALTER TABLE p2p_orders ADD COLUMN IF NOT EXISTS pay_amount         NUMERIC;
ALTER TABLE p2p_orders ADD COLUMN IF NOT EXISTS pay_currency       VARCHAR(8);
ALTER TABLE p2p_orders ADD COLUMN IF NOT EXISTS payment_method_id  BIGINT;
ALTER TABLE p2p_orders ADD COLUMN IF NOT EXISTS status             VARCHAR(20) DEFAULT 'open';
ALTER TABLE p2p_orders ADD COLUMN IF NOT EXISTS reject_reason      TEXT;
ALTER TABLE p2p_orders ADD COLUMN IF NOT EXISTS reviewed_by        VARCHAR(42);
ALTER TABLE p2p_orders ADD COLUMN IF NOT EXISTS deadline           TIMESTAMPTZ;
ALTER TABLE p2p_orders ADD COLUMN IF NOT EXISTS open_tx_hash       VARCHAR(66);
ALTER TABLE p2p_orders ADD COLUMN IF NOT EXISTS paid_tx_hash       VARCHAR(66);
ALTER TABLE p2p_orders ADD COLUMN IF NOT EXISTS release_tx_hash    VARCHAR(66);
ALTER TABLE p2p_orders ADD COLUMN IF NOT EXISTS created_at         TIMESTAMPTZ DEFAULT now();
ALTER TABLE p2p_orders ADD COLUMN IF NOT EXISTS updated_at         TIMESTAMPTZ DEFAULT now();

-- Backward compatibility for early P2P deployments that created separate/old
-- P2P order columns. The app now uses p2p_orders.id as the local DB primary key,
-- p2p_orders.onchain_id for the escrow contract order id, and amount_gd for the
-- reserved G$ amount. Legacy NOT NULL constraints on old columns prevent new
-- orders from being saved, so relax them and keep the legacy amount populated.
UPDATE p2p_orders
SET amount_gd = COALESCE(amount_gd, g_dollar_amount),
    g_dollar_amount = COALESCE(g_dollar_amount, amount_gd)
WHERE amount_gd IS NULL OR g_dollar_amount IS NULL;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'p2p_orders'
          AND column_name = 'order_id'
    ) THEN
        ALTER TABLE p2p_orders ALTER COLUMN order_id DROP NOT NULL;
    END IF;

    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'p2p_orders'
          AND column_name = 'g_dollar_amount'
    ) THEN
        ALTER TABLE p2p_orders ALTER COLUMN g_dollar_amount DROP NOT NULL;
    END IF;
END $$;
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
ALTER TABLE p2p_messages ADD COLUMN IF NOT EXISTS order_id      BIGINT;
ALTER TABLE p2p_messages ADD COLUMN IF NOT EXISTS sender_wallet VARCHAR(42);
ALTER TABLE p2p_messages ADD COLUMN IF NOT EXISTS body          TEXT;
ALTER TABLE p2p_messages ADD COLUMN IF NOT EXISTS created_at    TIMESTAMPTZ DEFAULT now();
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
ALTER TABLE p2p_proofs ADD COLUMN IF NOT EXISTS order_id        BIGINT;
ALTER TABLE p2p_proofs ADD COLUMN IF NOT EXISTS uploader_wallet VARCHAR(42);
ALTER TABLE p2p_proofs ADD COLUMN IF NOT EXISTS image_url       TEXT;
ALTER TABLE p2p_proofs ADD COLUMN IF NOT EXISTS reference       TEXT;
ALTER TABLE p2p_proofs ADD COLUMN IF NOT EXISTS created_at      TIMESTAMPTZ DEFAULT now();
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
ALTER TABLE p2p_disputes ADD COLUMN IF NOT EXISTS order_id        BIGINT;
ALTER TABLE p2p_disputes ADD COLUMN IF NOT EXISTS raised_by       VARCHAR(42);
ALTER TABLE p2p_disputes ADD COLUMN IF NOT EXISTS reason          TEXT;
ALTER TABLE p2p_disputes ADD COLUMN IF NOT EXISTS status          VARCHAR(20) DEFAULT 'open';
ALTER TABLE p2p_disputes ADD COLUMN IF NOT EXISTS resolved_by     VARCHAR(42);
ALTER TABLE p2p_disputes ADD COLUMN IF NOT EXISTS resolve_tx_hash VARCHAR(66);
ALTER TABLE p2p_disputes ADD COLUMN IF NOT EXISTS created_at      TIMESTAMPTZ DEFAULT now();
ALTER TABLE p2p_disputes ADD COLUMN IF NOT EXISTS resolved_at     TIMESTAMPTZ;
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
