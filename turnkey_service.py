"""
Turnkey Service - Embedded Wallet Management

This module provides functionality for creating and managing embedded wallets
using Turnkey's MPC-based infrastructure.

Reference: https://docs.turnkey.com/solutions/company-wallets/integration-guide/python
"""
import logging
from typing import Optional
from turnkey_http import TurnkeyClient
from turnkey_api_key_stamper import ApiKeyStamper, ApiKeyStamperConfig
from turnkey_sdk_types import (
    CreateUsersBody,
    CreateWalletBody,
    GetWalletAccountBody,
    GetWalletsBody,
    ExportWalletBody,
    CreatePrivateKeysBody,
    PrivateKeyExportFormat,
    CurveType,
    WalletType
)
from config import (
    TURNKEY_API_PUBLIC_KEY,
    TURNKEY_API_PRIVATE_KEY,
    TURNKEY_ORGANIZATION_ID,
    TURNKEY_API_BASE_URL
)

logger = logging.getLogger(__name__)


class TurnkeyService:
    """Service for interacting with Turnkey API for embedded wallet management."""

    def __init__(self):
        """Initialize Turnkey client with API credentials."""
        self._client = None
        self._configured = bool(
            TURNKEY_API_PUBLIC_KEY and
            TURNKEY_API_PRIVATE_KEY and
            TURNKEY_ORGANIZATION_ID
        )

    @property
    def is_configured(self) -> bool:
        """Check if Turnkey is properly configured."""
        return self._configured

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

    def create_user_and_wallet(
        self,
        user_email: str,
        user_name: str = "GoodMarket User",
        wallet_name: str = "GoodMarket Wallet"
    ) -> dict:
        """
        Create a new user and associated wallet in Turnkey.

        This method creates both a user and a wallet in a single flow.
        For embedded wallets, we use Turnkey's sub-organization feature.

        Args:
            user_email: User's email address for authentication
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
            # Step 1: Create user
            user_body = CreateUsersBody(
                user_email=user_email,
                user_name=user_name
            )
            user_response = client.create_users(user_body)
            
            # Extract user ID from response
            user_id = None
            if hasattr(user_response, 'users') and user_response.users:
                user_id = user_response.users[0].user_id
            
            if not user_id:
                return {
                    "success": False,
                    "error": "Failed to create user - no user ID returned"
                }

            logger.info(f"Created Turnkey user: {user_id}")

            # Step 2: Create wallet for the user
            wallet_body = CreateWalletBody(
                wallet_name=wallet_name,
                wallet_type=WalletType.WALLET_TYPE_DEFAULT,
                account_types=["ACCOUNT_TYPE_ETHEREUM"]
            )
            wallet_response = client.create_wallet(wallet_body)

            # Extract wallet info from response
            wallet_id = None
            wallet_address = None
            if hasattr(wallet_response, 'wallet') and wallet_response.wallet:
                wallet_id = wallet_response.wallet.wallet_id
                # Get the address from wallet accounts
                if hasattr(wallet_response.wallet, 'accounts') and wallet_response.wallet.accounts:
                    # Get first account address
                    first_account_id = wallet_response.wallet.accounts[0]
                    # Fetch the account details to get address
                    account_body = GetWalletAccountBody(walletAccountId=first_account_id)
                    account_response = client.get_wallet_account(account_body)
                    if hasattr(account_response, 'wallet_account') and account_response.wallet_account:
                        wallet_address = account_response.wallet_account.address

            if not wallet_id:
                return {
                    "success": False,
                    "error": "Failed to create wallet - no wallet ID returned"
                }

            logger.info(f"Created Turnkey wallet: {wallet_id} at {wallet_address}")

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
            from turnkey_sdk_types import GetWalletBody
            wallet_body = GetWalletBody(walletId=wallet_id)
            response = client.get_wallet(wallet_body)

            if hasattr(response, 'wallet') and response.wallet:
                wallet = response.wallet
                return {
                    "success": True,
                    "wallet_id": wallet.wallet_id,
                    "wallet_name": wallet.wallet_name if hasattr(wallet, 'wallet_name') else None,
                    "accounts": wallet.accounts if hasattr(wallet, 'accounts') else []
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

    def export_wallet(self, wallet_id: str, private_key_ids: list = None) -> dict:
        """
        Export wallet credentials (Turnkey bundle format).

        Note: Turnkey uses MPC, so this exports an encrypted bundle, not raw private keys.
        The bundle can only be imported back into Turnkey.

        Args:
            wallet_id: The wallet ID to export
            private_key_ids: Optional list of private key IDs to export (exports all if None)

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
            export_body = ExportWalletBody(
                wallet_id=wallet_id,
                export_format=PrivateKeyExportFormat.PRIVATE_KEY_EXPORT_FORMAT_PEM,
                private_key_ids=private_key_ids
            )
            response = client.export_wallet(export_body)

            # Extract export bundle from response
            export_bundle = None
            if hasattr(response, 'exported_private_key_bundle'):
                bundle = response.exported_private_key_bundle
                if hasattr(bundle, 'encrypted_private_key'):
                    export_bundle = {
                        "encrypted_private_key": bundle.encrypted_private_key,
                        "public_key": bundle.public_key if hasattr(bundle, 'public_key') else None
                    }

            return {
                "success": True,
                "export_bundle": export_bundle,
                "wallet_id": wallet_id
            }

        except Exception as e:
            logger.error(f"Error exporting Turnkey wallet: {e}")
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
