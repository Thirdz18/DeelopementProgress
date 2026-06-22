#!/usr/bin/env python3
"""
GoodMarket Verification Audit Script
======================================

Cross-checks on-chain UBI claim records with GoodMarket login/session data
to find users who verified via GoodMarket but whose
``verified_after_goodmarket`` flag is still FALSE.

The script identifies wallets that:
  1. Have a record in ``goodmarket_claim_facts`` (i.e. they used GoodMarket to
     claim G$), AND
  2. Are face-verified on-chain (``Identity.isWhitelisted`` is TRUE), AND
  3. Their on-chain ``lastAuthenticated`` timestamp falls on the same date as
     (or within 24 hours of) a login/session record in ``user_sessions`` or
     ``user_data.first_login``.

This matches the user's criteria: "users who logged into GoodMarket and within
24 hours also have a UBI claim on-chain".

Usage
-----
Set the required environment variables, then run::

    python scripts/check_verified_via_goodmarket.py

Or load them from the repo-secrets .env file::

    source /run/repo_secrets/DeelopementProgress/.env.secrets 2>/dev/null
    python scripts/check_verified_via_goodmarket.py

Required env vars:
  SUPABASE_URL, SUPABASE_ANON_KEY (or SUPABASE_SERVICE_ROLE_KEY)
  CELO_RPC_URL (optional, defaults to https://forno.celo.org)
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Set

# ---------------------------------------------------------------------------
# Lazy imports so the script can print helpful messages before failing
# ---------------------------------------------------------------------------

def _get_supabase():
    """Return a Supabase client using env vars."""
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_ANON_KEY")
    if not url or not key:
        print("ERROR: SUPABASE_URL and SUPABASE_ANON_KEY (or SUPABASE_SERVICE_ROLE_KEY) must be set.")
        sys.exit(1)
    try:
        from supabase import create_client
        return create_client(url, key)
    except ImportError:
        print("ERROR: 'supabase' package not installed.  pip install supabase")
        sys.exit(1)


def _get_web3():
    """Return a Web3 instance connected to Celo."""
    rpc = os.environ.get("CELO_RPC_URL", "https://forno.celo.org")
    try:
        from web3 import Web3
        w3 = Web3(Web3.HTTPProvider(rpc, request_kwargs={"timeout": 15}))
        if not w3.is_connected():
            print(f"WARNING: Web3 not connected to {rpc}")
        return w3
    except ImportError:
        print("ERROR: 'web3' package not installed.  pip install web3")
        sys.exit(1)


# GoodDollar Identity contract on Celo
IDENTITY_ADDRESS = "0x76e76e10Ac308A1D54a00f9df27EdCE4801F288b"
IDENTITY_ABI_FRAGMENT = [
    {
        "inputs": [{"internalType": "address", "name": "account", "type": "address"}],
        "name": "isWhitelisted",
        "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "address", "name": "account", "type": "address"}],
        "name": "lastAuthenticated",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
]


def _parse_iso(val: Any) -> Optional[datetime]:
    """Parse an ISO timestamp string to a tz-aware datetime."""
    if not val or not isinstance(val, str):
        return None
    try:
        normalised = val.replace("Z", "+00:00")
        dt = datetime.fromisoformat(normalised)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Main audit logic
# ---------------------------------------------------------------------------

def run_audit(fix: bool = False) -> Dict[str, Any]:
    """Run the verification audit.

    Args:
        fix: When True, update ``verified_after_goodmarket = True`` for
             wallets that pass the check. When False (default), only report.
    """
    sb = _get_supabase()
    w3 = _get_web3()

    identity = w3.eth.contract(
        address=w3.to_checksum_address(IDENTITY_ADDRESS),
        abi=IDENTITY_ABI_FRAGMENT,
    )

    # 1. Collect all wallets from goodmarket_claim_facts
    print("\n=== Step 1: Collecting wallets from goodmarket_claim_facts ===")
    claim_wallets: Dict[str, Dict] = {}  # wallet -> earliest claim info
    page_size = 1000
    offset = 0
    while True:
        resp = sb.table("goodmarket_claim_facts")\
            .select("wallet_address, status, created_at, confirmed_at")\
            .range(offset, offset + page_size - 1)\
            .execute()
        rows = resp.data or []
        if not rows:
            break
        for row in rows:
            addr = (row.get("wallet_address") or "").strip().lower()
            if not addr:
                continue
            ts = _parse_iso(row.get("confirmed_at") or row.get("created_at"))
            if addr not in claim_wallets or (ts and (claim_wallets[addr].get("earliest_claim") is None or ts < claim_wallets[addr]["earliest_claim"])):
                claim_wallets[addr] = {
                    "earliest_claim": ts,
                    "status": row.get("status"),
                }
        if len(rows) < page_size:
            break
        offset += page_size

    print(f"  Found {len(claim_wallets)} unique wallets with claim records.")

    # 2. Fetch user_data for these wallets
    print("\n=== Step 2: Fetching user_data for claim wallets ===")
    user_data: Dict[str, Dict] = {}
    for wallet_lower in claim_wallets:
        try:
            resp = sb.table("user_data")\
                .select("wallet_address, verified_after_goodmarket, face_verified, "
                        "face_verified_at, first_login, first_seen_unverified, "
                        "created_at, ubi_verified")\
                .ilike("wallet_address", wallet_lower)\
                .limit(1)\
                .execute()
            if resp.data:
                user_data[wallet_lower] = resp.data[0]
        except Exception as e:
            print(f"  WARNING: Could not fetch user_data for {wallet_lower[:10]}...: {e}")
        time.sleep(0.05)  # rate-limit

    print(f"  Fetched user_data for {len(user_data)}/{len(claim_wallets)} wallets.")

    # 3. Fetch user_sessions for date cross-reference
    print("\n=== Step 3: Collecting session timestamps ===")
    session_dates: Dict[str, List[datetime]] = {}
    for wallet_lower in claim_wallets:
        try:
            resp = sb.table("user_sessions")\
                .select("wallet_address, timestamp")\
                .ilike("wallet_address", wallet_lower)\
                .order("timestamp", desc=False)\
                .limit(50)\
                .execute()
            if resp.data:
                dates = []
                for row in resp.data:
                    ts = _parse_iso(row.get("timestamp"))
                    if ts:
                        dates.append(ts)
                if dates:
                    session_dates[wallet_lower] = dates
        except Exception:
            pass
        time.sleep(0.05)

    print(f"  Found session records for {len(session_dates)}/{len(claim_wallets)} wallets.")

    # 4. On-chain checks + cross-reference
    print("\n=== Step 4: On-chain verification + cross-reference ===")

    results = {
        "already_attributed": [],
        "newly_attributable": [],
        "not_face_verified": [],
        "no_user_data": [],
        "no_date_match": [],
        "rpc_error": [],
    }

    for wallet_lower, claim_info in claim_wallets.items():
        ud = user_data.get(wallet_lower)
        if not ud:
            results["no_user_data"].append(wallet_lower)
            continue

        if ud.get("verified_after_goodmarket") is True:
            results["already_attributed"].append(wallet_lower)
            continue

        # On-chain check
        try:
            checksum = w3.to_checksum_address(wallet_lower)
        except Exception:
            results["rpc_error"].append(wallet_lower)
            continue

        try:
            is_whitelisted = identity.functions.isWhitelisted(checksum).call()
        except Exception as e:
            results["rpc_error"].append(wallet_lower)
            time.sleep(0.1)
            continue

        if not is_whitelisted:
            results["not_face_verified"].append(wallet_lower)
            continue

        try:
            last_auth_unix = identity.functions.lastAuthenticated(checksum).call()
        except Exception:
            last_auth_unix = 0

        if last_auth_unix <= 0:
            results["not_face_verified"].append(wallet_lower)
            continue

        last_auth_dt = datetime.fromtimestamp(last_auth_unix, tz=timezone.utc)

        # Cross-reference: check if lastAuthenticated is within 24 hours of
        # any session timestamp or first_login/first_seen_unverified
        reference_dates: List[datetime] = []

        first_login = _parse_iso(ud.get("first_login"))
        if first_login:
            reference_dates.append(first_login)
        first_seen = _parse_iso(ud.get("first_seen_unverified"))
        if first_seen:
            reference_dates.append(first_seen)
        created = _parse_iso(ud.get("created_at"))
        if created:
            reference_dates.append(created)

        if wallet_lower in session_dates:
            reference_dates.extend(session_dates[wallet_lower])

        # Also consider the claim date itself
        if claim_info.get("earliest_claim"):
            reference_dates.append(claim_info["earliest_claim"])

        if not reference_dates:
            results["no_date_match"].append({
                "wallet": wallet_lower,
                "last_auth": last_auth_dt.isoformat(),
                "reason": "no_reference_dates",
            })
            continue

        match_found = False
        closest_delta = None
        closest_ref = None
        for ref_dt in reference_dates:
            delta = abs((last_auth_dt - ref_dt).total_seconds())
            if closest_delta is None or delta < closest_delta:
                closest_delta = delta
                closest_ref = ref_dt
            if delta <= 86400:  # 24 hours
                match_found = True

        if match_found:
            entry = {
                "wallet": wallet_lower,
                "last_auth": last_auth_dt.isoformat(),
                "closest_ref": closest_ref.isoformat() if closest_ref else None,
                "delta_hours": round(closest_delta / 3600, 2) if closest_delta else None,
                "face_verified": ud.get("face_verified"),
                "current_attributed": ud.get("verified_after_goodmarket"),
                "claim_status": claim_info.get("status"),
            }
            results["newly_attributable"].append(entry)

            if fix:
                try:
                    update_payload = {"verified_after_goodmarket": True}
                    if not ud.get("face_verified"):
                        update_payload["face_verified"] = True
                        update_payload["face_verified_at"] = datetime.now(timezone.utc).isoformat()
                    if not ud.get("ubi_verified"):
                        update_payload["ubi_verified"] = True
                        update_payload["verification_timestamp"] = datetime.now(timezone.utc).isoformat()
                    sb.table("user_data")\
                        .update(update_payload)\
                        .ilike("wallet_address", wallet_lower)\
                        .execute()
                    print(f"  FIXED: {wallet_lower[:12]}... -> verified_after_goodmarket=TRUE")
                except Exception as e:
                    print(f"  ERROR fixing {wallet_lower[:12]}...: {e}")
        else:
            results["no_date_match"].append({
                "wallet": wallet_lower,
                "last_auth": last_auth_dt.isoformat(),
                "closest_ref": closest_ref.isoformat() if closest_ref else None,
                "delta_hours": round(closest_delta / 3600, 2) if closest_delta else None,
                "reason": "outside_24h_window",
            })

        time.sleep(0.05)

    # 5. Print summary
    print("\n" + "=" * 60)
    print("AUDIT SUMMARY")
    print("=" * 60)
    print(f"Total wallets with claims:        {len(claim_wallets)}")
    print(f"Already attributed:               {len(results['already_attributed'])}")
    print(f"Newly attributable (within 24h):  {len(results['newly_attributable'])}")
    print(f"Not face-verified on-chain:       {len(results['not_face_verified'])}")
    print(f"No user_data record:              {len(results['no_user_data'])}")
    print(f"No date match (>24h gap):         {len(results['no_date_match'])}")
    print(f"RPC errors:                       {len(results['rpc_error'])}")

    if results["newly_attributable"]:
        print(f"\n--- Newly Attributable Wallets {'(FIXED)' if fix else '(DRY RUN)'} ---")
        for entry in results["newly_attributable"]:
            print(f"  {entry['wallet'][:16]}...  last_auth={entry['last_auth']}  "
                  f"closest_ref={entry.get('closest_ref', 'N/A')}  "
                  f"delta={entry.get('delta_hours', '?')}h  "
                  f"claim_status={entry.get('claim_status')}")

    if results["no_date_match"]:
        print(f"\n--- No Date Match (for investigation) ---")
        for entry in results["no_date_match"][:20]:
            if isinstance(entry, dict):
                print(f"  {entry['wallet'][:16]}...  last_auth={entry.get('last_auth', '?')}  "
                      f"closest={entry.get('closest_ref', 'N/A')}  "
                      f"delta={entry.get('delta_hours', '?')}h  "
                      f"reason={entry.get('reason')}")

    return results


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Audit GoodMarket verified-via-goodmarket attribution")
    parser.add_argument("--fix", action="store_true",
                        help="Actually update verified_after_goodmarket in the DB (default: dry-run only)")
    args = parser.parse_args()

    print("GoodMarket Verification Audit")
    print(f"Mode: {'FIX (will update DB)' if args.fix else 'DRY RUN (read-only)'}")
    print(f"Time: {datetime.now(timezone.utc).isoformat()}")

    results = run_audit(fix=args.fix)

    # Write results to JSON for further analysis
    output_path = os.path.join(os.path.dirname(__file__), "..", "audit_results.json")
    try:
        with open(output_path, "w") as f:
            json.dump({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "mode": "fix" if args.fix else "dry_run",
                "summary": {
                    "total_claim_wallets": (
                        len(results["already_attributed"]) +
                        len(results["newly_attributable"]) +
                        len(results["not_face_verified"]) +
                        len(results["no_user_data"]) +
                        len(results["no_date_match"]) +
                        len(results["rpc_error"])
                    ),
                    "already_attributed": len(results["already_attributed"]),
                    "newly_attributable": len(results["newly_attributable"]),
                    "not_face_verified": len(results["not_face_verified"]),
                    "no_user_data": len(results["no_user_data"]),
                    "no_date_match": len(results["no_date_match"]),
                    "rpc_error": len(results["rpc_error"]),
                },
                "newly_attributable": results["newly_attributable"],
                "no_date_match": results["no_date_match"][:50],
            }, f, indent=2, default=str)
        print(f"\nResults written to: {output_path}")
    except Exception as e:
        print(f"\nCould not write results file: {e}")
