"""
Turnkey Service - Organization Wallet Management

NOTE: This is the SERVER-SIDE SDK for Turnkey. This is designed for:
- Company/organizational wallet management
- Administrative operations
- Backend transaction signing

For TRUE EMBEDDED WALLETS with email authentication for end users,
Turnkey recommends their frontend SDK (@turnkey/react-wallet-kit).

Reference: https://docs.turnkey.com/solutions/company-wallets/integration-guide/python
"""
import logging
from typing import Optional, List
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
from config import (
    TURNKEY_API_PUBLIC_KEY,
    TURNKEY_API_PRIVATE_KEY,
    TURNKEY_ORGANIZATION_ID,
    TURNKEY_API_BASE_URL
)

logger = logging.getLogger(__name__)


class TurnkeyService:
    """Service for interacting with Turnkey API for organization wallet management."""

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


# Singleton instance
_turnkey_service: Optional[TurnkeyService] = None


def get_turnkey_service() -> TurnkeyService:
    """Get the Turnkey service singleton instance."""
    global _turnkey_service
    if _turnkey_service is None:
        _turnkey_service = TurnkeyService()
    return _turnkey_service
