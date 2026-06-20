---
name: Turnkey API key corruption fix
description: TURNKEY_API_PUBLIC_KEY and TURNKEY_API_PRIVATE_KEY were split across env vars; code reconstructs correct values at runtime.
---

## Rule
In `turnkey_service.py`, the startup block checks if `TURNKEY_API_PRIVATE_KEY` contains a space. If so, the part before the space is the missing suffix of the public key, and the part after is the actual private key. This is a persistent copy-paste corruption in the Replit env vars.

**Actual values (reconstructed):**
- Public key = stored pub + priv_raw.split(" ")[0] → 66 hex chars
- Private key = priv_raw.split(" ")[1] → 64 hex chars

**Why:** The env vars were pasted incorrectly — the tail of the compressed P-256 public key ended up prepended to the private key value with a space separator.

**How to apply:** The fix is already in `turnkey_service.py` lines ~27-37. For Vercel, the user must manually fix both env vars in the Vercel dashboard.

## Also fixed
- `_turnkey_post` used to pass the `TStamp` object directly as the X-Stamp header value; now uses `stamp.stamp_header_value`.

## Turnkey email OTP — blocked at plan level
`ACTIVITY_TYPE_INIT_OTP_AUTH` returns 403 with `policyEvaluations: []` regardless of policies created. This means OTP auth is feature-gated at the Turnkey org/plan level — not available for this account. Auth proxy also returns 404 (config `bc370a86...` does not exist). Two policies were created in the org (policy IDs logged in Turnkey dashboard).

Two Turnkey policies exist in the org:
1. "Allow OTP Auth" — condition: INIT_OTP_AUTH || OTP_AUTH
2. "Allow All Root Activities" — condition: true

Google login via createSubOrganization DOES work (returns 400 on bad token, not 403).
