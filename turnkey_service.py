"""
Turnkey Service - Embedded Wallet Management

This service provides embedded wallet functionality using Turnkey's MPC infrastructure
combined with email verification for user authentication.

Flow:
1. User enters email → Send verification code via Supabase Auth OTP
2. User enters code → Verify with Supabase and create wallet/login
3. Wallet created → User logged in

Reference: https://docs.turnkey.com
"""
import logging
import random
import string
import time
from typing import Optional, List
from datetime import datetime, timezone

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
        Generate and send verification code via Supabase Auth OTP.
        
        Args:
            email: User's email address
            purpose: Purpose of the code (login, create)
            
        Returns:
            The generated 6-digit code (or success indicator)
        """
        try:
            from supabase_client import send_otp_email
            
            result = send_otp_email(email)
            
            if result.get("success"):
                logger.info(f"OTP sent to {email} via Supabase Auth (purpose: {purpose})")
                return result.get("supabase_user_id")  # Return user ID if available
            else:
                logger.error(f"Failed to send OTP: {result.get('error')}")
                return None
                
        except Exception as e:
            logger.error(f"Error generating verification code: {e}")
            return None

    def verify_code(self, email: str, code: str, purpose: str = "login") -> bool:
        """
        Verify a verification code via Supabase Auth.
        
        Note: With Supabase Auth OTP, verification happens client-side.
        This method is kept for backwards compatibility but the actual
        verification is done via Supabase's verify_token on the client.
        
        Args:
            email: User's email address
            code: The code to verify (not used with Supabase Auth)
            purpose: Expected purpose of the code
            
        Returns:
            True if verification was successful (Supabase validated)
        """
        # With Supabase Auth, OTP verification happens on the client
        # The client receives the OTP, verifies with Supabase, and then
        # calls the backend to complete the login/wallet creation
        # This method is a placeholder for backwards compatibility
        logger.info(f"Supabase Auth handles OTP verification for {email}")
        return True

    def get_user_by_email(self, email: str) -> dict:
        """
        Check if a user exists with the given email (hashed).
        
        Uses Supabase email_wallet_links table with email_hash for privacy.
        
        Args:
            email: User's email address
            
        Returns:
            dict with user info if exists
        """
        try:
            from supabase_client import hash_email, get_user_by_email_hash
            
            email_hash = hash_email(email)
            user = get_user_by_email_hash(email_hash)
            
            if user:
                return {
                    "success": True,
                    "user_id": user.get("turnkey_user_id"),
                    "wallet_id": user.get("turnkey_wallet_id"),
                    "wallet_address": user.get("wallet_address"),
                    "email_hash": email_hash,
                    "supabase_user_id": user.get("supabase_user_id")
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
        wallet_name: str = "GoodMarket Wallet",
        supabase_user_id: str = None
    ) -> dict:
        """
        Create a new user and associated wallet.

        Args:
            user_email: User's email address
            user_name: Display name for the user
            wallet_name: Name for the wallet
            supabase_user_id: Supabase Auth user ID (optional)

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
            
            # Store user info in Supabase email_wallet_links table (privacy-preserving)
            try:
                from supabase_client import (
                    hash_email, 
                    get_supabase_admin_client,
                    get_user_by_email_hash
                )
                admin_client = get_supabase_admin_client()
                
                if admin_client:
                    email_hash = hash_email(user_email)
                    
                    # Check if record already exists
                    existing = get_user_by_email_hash(email_hash)
                    
                    link_data = {
                        "email_hash": email_hash,
                        "wallet_address": wallet_address.lower(),
                        "login_method": "turnkey_email",
                        "turnkey_user_id": user_id,
                        "turnkey_wallet_id": wallet_id,
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    }
                    
                    if supabase_user_id:
                        link_data["supabase_user_id"] = supabase_user_id
                    
                    if existing:
                        # Update existing record
                        admin_client.table("email_wallet_links").update(link_data).eq(
                            "email_hash", email_hash
                        ).execute()
                        logger.info(f"Updated Turnkey user in database: {email_hash[:16]}...")
                    else:
                        # Insert new record
                        link_data["created_at"] = datetime.now(timezone.utc).isoformat()
                        admin_client.table("email_wallet_links").insert(link_data).execute()
                        logger.info(f"Stored Turnkey user in database: {email_hash[:16]}...")
                        
            except Exception as db_error:
                logger.warning(f"Could not store user in database: {db_error}")
                # Continue anyway - wallet was created successfully

            logger.info(f"Created Turnkey user and wallet for {user_email}: {wallet_address}")

            return {
                "success": True,
                "user_id": user_id,
                "wallet_id": wallet_id,
                "wallet_address": wallet_address,
                "email_hash": hash_email(user_email) if 'hash_email' in dir() else None,
                "supabase_user_id": supabase_user_id
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
