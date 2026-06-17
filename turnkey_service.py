"""
Turnkey Service - Embedded Wallet Management

This service provides embedded wallet functionality using Turnkey's MPC infrastructure
combined with email verification for user authentication.

Flow:
1. User enters email → Send verification code
2. User enters code → Verify and create wallet/login
3. Wallet created → User logged in

Reference: https://docs.turnkey.com
"""
import logging
import random
import string
import time
from typing import Optional, List

# Try to import Turnkey SDK - will be None if not installed
try:
    from turnkey_http import TurnkeyClient
    from turnkey_api_key_stamper import ApiKeyStamper, ApiKeyStamperConfig
    from turnkey_sdk_types import (
        CreateWalletBody,
        GetWalletAccountBody,
        GetWalletsBody,
        ExportWalletBody,
        GetWalletBody,
        CreateWalletAccountsBody,
        v1WalletAccountParams,
        v1Curve,
        v1PathFormat,
        v1AddressFormat,
        ExportPrivateKeyBody
    )
    TURNKEY_SDK_AVAILABLE = True
except ImportError:
    TURNKEY_SDK_AVAILABLE = False
    TurnkeyClient = None
    ApiKeyStamper = None
    ApiKeyStamperConfig = None

from config import (
    TURNKEY_API_PUBLIC_KEY,
    TURNKEY_API_PRIVATE_KEY,
    TURNKEY_ORGANIZATION_ID,
    TURNKEY_API_BASE_URL
)

logger = logging.getLogger(__name__)

# In-memory storage for verification codes (use Redis in production)
_verification_codes: dict = {}
_CODE_EXPIRY_SECONDS = 300  # 5 minutes


class TurnkeyService:
    """Service for interacting with Turnkey API for organization wallet management."""

    def __init__(self):
        """Initialize Turnkey client with API credentials."""
        self._client = None
        self._configured = bool(
            TURNKEY_SDK_AVAILABLE and
            TURNKEY_API_PUBLIC_KEY and
            TURNKEY_API_PRIVATE_KEY and
            TURNKEY_ORGANIZATION_ID
        )

    @property
    def is_configured(self) -> bool:
        """Check if Turnkey is properly configured."""
        return self._configured

    @property
    def sdk_available(self) -> bool:
        """Check if Turnkey SDK is installed."""
        return TURNKEY_SDK_AVAILABLE

    def _get_client(self) -> Optional[TurnkeyClient]:
        """Get or create Turnkey client instance."""
        if not self._configured:
            logger.warning("Turnkey not configured - missing API credentials")
            return None

        if self._client is None:
            try:
                config = ApiKeyStamperConfig(
                    api_public_key=TURNKEY_API_PUBLIC_KEY,
                    api_private_key=TURNKEY_API_PRIVATE_KEY
                )
                stamper = ApiKeyStamper(config)
                self._client = TurnkeyClient(
                    base_url=TURNKEY_API_BASE_URL,
                    stamper=stamper,
                    organization_id=TURNKEY_ORGANIZATION_ID
                )
                logger.info("Turnkey client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Turnkey client: {e}")
                return None

        return self._client

    def create_wallet(
        self,
        wallet_name: str = "GoodMarket Wallet"
    ) -> dict:
        """
        Create a new wallet under the organization.

        Args:
            wallet_name: Name for the wallet

        Returns:
            dict with success status and wallet details
        """
        client = self._get_client()
        if not client:
            return {
                "success": False,
                "error": "Turnkey not configured"
            }

        try:
            # Create wallet with Ethereum account
            # BIP44 path for Ethereum: m/44'/60'/0'/0/0
            account_params = v1WalletAccountParams(
                curve=v1Curve.CURVE_SECP256K1,
                pathFormat=v1PathFormat.PATH_FORMAT_BIP32,
                path="m/44'/60'/0'/0/0",
                addressFormat=v1AddressFormat.ADDRESS_FORMAT_ETHEREUM
            )

            wallet_body = CreateWalletBody(
                walletName=wallet_name,
                accounts=[account_params]
            )
            wallet_response = client.create_wallet(wallet_body)

            # Extract wallet info
            wallet_id = None
            wallet_address = None
            if hasattr(wallet_response, 'wallet') and wallet_response.wallet:
                wallet_id = wallet_response.wallet.wallet_id
                # Get addresses from wallet accounts
                if hasattr(wallet_response.wallet, 'addresses') and wallet_response.wallet.addresses:
                    wallet_address = wallet_response.wallet.addresses[0]

            if not wallet_id:
                return {
                    "success": False,
                    "error": "Failed to create wallet - no wallet ID returned"
                }

            logger.info(f"Created Turnkey wallet: {wallet_id} at {wallet_address}")

            return {
                "success": True,
                "wallet_id": wallet_id,
                "wallet_address": wallet_address,
                "wallet_name": wallet_name
            }

        except Exception as e:
            logger.error(f"Error creating Turnkey wallet: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def get_wallets(self) -> dict:
        """
        Get all wallets in the organization.

        Returns:
            dict with list of wallets
        """
        client = self._get_client()
        if not client:
            return {
                "success": False,
                "error": "Turnkey not configured"
            }

        try:
            wallets_body = GetWalletsBody()
            response = client.get_wallets(wallets_body)

            wallets = []
            if hasattr(response, 'wallets') and response.wallets:
                for wallet in response.wallets:
                    wallets.append({
                        "wallet_id": wallet.wallet_id,
                        "wallet_name": wallet.wallet_name if hasattr(wallet, 'wallet_name') else None,
                        "created_at": wallet.created_at if hasattr(wallet, 'created_at') else None
                    })

            return {
                "success": True,
                "wallets": wallets
            }

        except Exception as e:
            logger.error(f"Error getting Turnkey wallets: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def get_wallet(self, wallet_id: str) -> dict:
        """
        Get details of a specific wallet.

        Args:
            wallet_id: The wallet ID to retrieve

        Returns:
            dict with wallet details
        """
        client = self._get_client()
        if not client:
            return {
                "success": False,
                "error": "Turnkey not configured"
            }

        try:
            wallet_body = GetWalletBody(walletId=wallet_id)
            response = client.get_wallet(wallet_body)

            if hasattr(response, 'wallet') and response.wallet:
                wallet = response.wallet
                return {
                    "success": True,
                    "wallet_id": wallet.wallet_id,
                    "wallet_name": wallet.wallet_name if hasattr(wallet, 'wallet_name') else None,
                    "accounts": wallet.addresses if hasattr(wallet, 'addresses') else []
                }

            return {
                "success": False,
                "error": "Wallet not found"
            }

        except Exception as e:
            logger.error(f"Error getting Turnkey wallet: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def export_wallet(self, wallet_id: str) -> dict:
        """
        Export wallet private key (Turnkey bundle format).

        NOTE: Turnkey uses MPC - this exports an encrypted bundle that can ONLY
        be imported back into Turnkey. This is NOT a raw private key.

        Args:
            wallet_id: The wallet ID to export

        Returns:
            dict with export bundle
        """
        client = self._get_client()
        if not client:
            return {
                "success": False,
                "error": "Turnkey not configured"
            }

        try:
            # First get wallet to find private key IDs
            wallet_info = self.get_wallet(wallet_id)
            if not wallet_info.get("success"):
                return wallet_info

            # Export the wallet
            export_body = ExportWalletBody(walletId=wallet_id)
            response = client.export_wallet(export_body)

            # Extract export info
            export_bundle = None
            if hasattr(response, 'exportedPrivateKeyBundle'):
                bundle = response.exportedPrivateKeyBundle
                export_bundle = {
                    "encrypted_private_key": bundle.encryptedPrivateKey if hasattr(bundle, 'encryptedPrivateKey') else None,
                    "public_key": bundle.publicKey if hasattr(bundle, 'publicKey') else None
                }

            return {
                "success": True,
                "export_bundle": export_bundle,
                "wallet_id": wallet_id,
                "note": "This bundle can only be imported into Turnkey"
            }

        except Exception as e:
            logger.error(f"Error exporting Turnkey wallet: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def generate_verification_code(self, email: str, purpose: str = "login") -> Optional[str]:
        """
        Generate a 6-digit verification code for email verification.
        
        Args:
            email: User's email address
            purpose: Purpose of the code (login, create)
            
        Returns:
            The generated 6-digit code
        """
        # Generate 6-digit code
        code = ''.join(random.choices(string.digits, k=6))
        
        # Store with timestamp
        _verification_codes[email] = {
            "code": code,
            "purpose": purpose,
            "timestamp": time.time()
        }
        
        logger.info(f"Generated verification code for {email} (purpose: {purpose})")
        return code

    def verify_code(self, email: str, code: str, purpose: str = "login") -> bool:
        """
        Verify a verification code.
        
        Args:
            email: User's email address
            code: The code to verify
            purpose: Expected purpose of the code
            
        Returns:
            True if code is valid and not expired
        """
        if email not in _verification_codes:
            logger.warning(f"No verification code found for {email}")
            return False
        
        stored = _verification_codes[email]
        
        # Check if expired (5 minutes)
        if time.time() - stored["timestamp"] > _CODE_EXPIRY_SECONDS:
            logger.warning(f"Verification code expired for {email}")
            del _verification_codes[email]
            return False
        
        # Check if purpose matches
        if stored["purpose"] != purpose:
            logger.warning(f"Verification code purpose mismatch for {email}")
            return False
        
        # Check if code matches
        if stored["code"] != code:
            logger.warning(f"Invalid verification code for {email}")
            return False
        
        # Code is valid - remove it (one-time use)
        del _verification_codes[email]
        logger.info(f"Verification code validated for {email}")
        return True

    def get_user_by_email(self, email: str) -> dict:
        """
        Check if a user exists with the given email.
        
        For this implementation, we use Supabase to track Turnkey users.
        
        Args:
            email: User's email address
            
        Returns:
            dict with user info if exists
        """
        try:
            from supabase_client import get_supabase_client
            
            client = get_supabase_client()
            if not client:
                # If Supabase not available, check in-memory storage
                # This is for development without full setup
                return {"success": False, "user_id": None}
            
            # Query users table for Turnkey user
            response = client.table("users").select("*").eq("email", email).execute()
            
            if response.data and len(response.data) > 0:
                user = response.data[0]
                return {
                    "success": True,
                    "user_id": user.get("turnkey_user_id"),
                    "wallet_id": user.get("turnkey_wallet_id"),
                    "wallet_address": user.get("wallet_address"),
                    "email": email
                }
            else:
                return {"success": False, "user_id": None}
                
        except Exception as e:
            logger.error(f"Error checking user by email: {e}")
            return {"success": False, "user_id": None}

    def create_user_and_wallet(
        self,
        user_email: str,
        user_name: str = "GoodMarket User",
        wallet_name: str = "GoodMarket Wallet"
    ) -> dict:
        """
        Create a new user and associated wallet.

        Args:
            user_email: User's email address
            user_name: Display name for the user
            wallet_name: Name for the wallet

        Returns:
            dict with success status and wallet details
        """
        client = self._get_client()
        if not client:
            return {
                "success": False,
                "error": "Turnkey not configured"
            }

        try:
            # Create wallet
            wallet_result = self.create_wallet(wallet_name)
            
            if not wallet_result.get("success"):
                return wallet_result
            
            wallet_id = wallet_result.get("wallet_id")
            wallet_address = wallet_result.get("wallet_address")
            
            # Generate a mock user ID (in production, use Turnkey's user API)
            import uuid
            user_id = f"user_{uuid.uuid4().hex[:16]}"
            
            # Store user info in Supabase (if available)
            try:
                from supabase_client import get_supabase_client
                client_db = get_supabase_client()
                if client_db:
                    client_db.table("users").upsert({
                        "email": user_email,
                        "wallet_address": wallet_address,
                        "turnkey_user_id": user_id,
                        "turnkey_wallet_id": wallet_id,
                        "display_name": user_name
                    }).execute()
                    logger.info(f"Stored Turnkey user in database: {user_email}")
            except Exception as db_error:
                logger.warning(f"Could not store user in database: {db_error}")
                # Continue anyway - wallet was created successfully

            logger.info(f"Created Turnkey user and wallet for {user_email}: {wallet_address}")

            return {
                "success": True,
                "user_id": user_id,
                "wallet_id": wallet_id,
                "wallet_address": wallet_address,
                "email": user_email
            }

        except Exception as e:
            logger.error(f"Error creating Turnkey user/wallet: {e}")
            return {
                "success": False,
                "error": str(e)
            }


# Singleton instance
_turnkey_service: Optional[TurnkeyService] = None


def get_turnkey_service() -> TurnkeyService:
    """Get the Turnkey service singleton instance."""
    global _turnkey_service
    if _turnkey_service is None:
        _turnkey_service = TurnkeyService()
    return _turnkey_service
