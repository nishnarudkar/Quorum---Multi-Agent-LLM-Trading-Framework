"""
Quorum — LocusFounder Agent
Handles autonomous wallet registration, balance management, and business operations.
The agent registers itself with Locus, manages its USDC wallet, and operates
as an autonomous trading research business.
"""

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Optional

import httpx

logger = logging.getLogger("quorum.locus.founder")

LOCUS_BETA_API = "https://api.locusfounder.com/api"
CREDENTIALS_PATH = Path(__file__).parent.parent / "db" / "locus_credentials.json"


class LocusFounderAgent:
    """
    Autonomous business agent backed by a Locus USDC wallet.

    Responsibilities:
    - Self-register with Locus on first run
    - Maintain wallet credentials across restarts
    - Check balance before accepting orders
    - Track revenue from completed analyses
    """

    def __init__(self):
        self.api_key: Optional[str] = None
        self.wallet_id: Optional[str] = None
        self.wallet_address: Optional[str] = None
        self.owner_address: Optional[str] = None
        self._registered = False
        self._client: Optional[httpx.AsyncClient] = None

    # ─── Lifecycle ────────────────────────────────────────────

    async def initialize(self):
        """Load existing credentials or register a new wallet."""
        self._client = httpx.AsyncClient(timeout=30.0)

        # Try loading saved credentials first
        if CREDENTIALS_PATH.exists():
            try:
                creds = json.loads(CREDENTIALS_PATH.read_text())
                self.api_key = creds.get("api_key")
                self.wallet_id = creds.get("wallet_id")
                self.wallet_address = creds.get("wallet_address")
                self.owner_address = creds.get("owner_address")
                self._registered = True
                logger.info(
                    f"Locus credentials loaded — wallet: {self.wallet_address}"
                )
                return
            except Exception as e:
                logger.warning(f"Failed to load Locus credentials: {e}")

        # Fall back to env var API key (human-provisioned)
        env_key = os.getenv("LOCUS_API_KEY", "")
        if env_key:
            self.api_key = env_key
            self._registered = True
            logger.info("Locus API key loaded from environment")
            return

        # Auto-register as a new agent
        await self._register()

    async def _register(self):
        """Self-register with Locus beta — no human signup required."""
        logger.info("Registering Quorum as a LocusFounder agent...")
        try:
            resp = await self._client.post(
                f"{LOCUS_BETA_API}/register",
                json={"name": "Quorum Trading Intelligence"},
            )
            resp.raise_for_status()
            data = resp.json().get("data", {})

            self.api_key = data.get("apiKey")
            self.wallet_id = data.get("walletId")
            self.owner_address = data.get("ownerAddress")

            # Poll until wallet is deployed
            self.wallet_address = await self._wait_for_wallet()

            # Persist credentials
            CREDENTIALS_PATH.parent.mkdir(parents=True, exist_ok=True)
            CREDENTIALS_PATH.write_text(json.dumps({
                "api_key": self.api_key,
                "wallet_id": self.wallet_id,
                "wallet_address": self.wallet_address,
                "owner_address": self.owner_address,
                "claim_url": data.get("claimUrl"),
            }, indent=2))

            self._registered = True
            logger.info(
                f"Locus agent registered — wallet: {self.wallet_address} | "
                f"claim: {data.get('claimUrl')}"
            )

        except Exception as e:
            logger.error(f"Locus registration failed: {e}")
            logger.warning("Quorum will run without Locus payment integration")

    async def _wait_for_wallet(self, max_attempts: int = 20) -> Optional[str]:
        """Poll /api/status until wallet is deployed."""
        for attempt in range(max_attempts):
            try:
                resp = await self._client.get(
                    f"{LOCUS_BETA_API}/status",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
                data = resp.json().get("data", {})
                status = data.get("walletStatus") or data.get("status")
                if status == "deployed":
                    return data.get("walletAddress") or data.get("address")
                logger.info(f"Wallet deploying... ({attempt + 1}/{max_attempts})")
                await asyncio.sleep(3)
            except Exception as e:
                logger.warning(f"Status poll error: {e}")
                await asyncio.sleep(3)
        logger.warning("Wallet deployment timed out — proceeding without address")
        return None

    async def close(self):
        if self._client:
            await self._client.aclose()

    # ─── Wallet Operations ────────────────────────────────────

    @property
    def is_ready(self) -> bool:
        return self._registered and bool(self.api_key)

    def _auth_headers(self) -> dict:
        return {"Authorization": f"Bearer {self.api_key}"}

    async def get_balance(self) -> dict:
        """Get current USDC wallet balance."""
        if not self.is_ready:
            return {"error": "Locus not initialized", "balance_usdc": 0.0}
        try:
            resp = await self._client.get(
                f"{LOCUS_BETA_API}/pay/balance",
                headers=self._auth_headers(),
            )
            resp.raise_for_status()
            data = resp.json()
            return {
                "balance_usdc": float(data.get("balance", 0)),
                "wallet_address": self.wallet_address,
                "currency": "USDC",
                "chain": "Base",
            }
        except Exception as e:
            logger.error(f"Balance check failed: {e}")
            return {"error": str(e), "balance_usdc": 0.0}

    async def send_usdc(self, to_address: str, amount_usdc: float, memo: str = "") -> dict:
        """Send USDC to a wallet address."""
        if not self.is_ready:
            return {"success": False, "error": "Locus not initialized"}
        try:
            resp = await self._client.post(
                f"{LOCUS_BETA_API}/pay/send",
                headers=self._auth_headers(),
                json={
                    "to": to_address,
                    "amount": str(round(amount_usdc, 2)),
                    "currency": "USDC",
                    "memo": memo,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            logger.info(f"Sent {amount_usdc} USDC to {to_address} — tx: {data.get('txHash')}")
            return {"success": True, **data}
        except Exception as e:
            logger.error(f"USDC send failed: {e}")
            return {"success": False, "error": str(e)}

    # ─── Business Info ────────────────────────────────────────

    def get_business_info(self) -> dict:
        """Return public business information for the storefront."""
        return {
            "name": "Quorum Trading Intelligence",
            "description": (
                "Autonomous AI trading research firm. "
                "13 specialized agents analyze stocks and crypto through "
                "adversarial debates and risk committee review."
            ),
            "services": [
                {
                    "id": "analysis_single",
                    "name": "Single Analysis Report",
                    "description": (
                        "Full 13-agent analysis: technicals, sentiment, news, "
                        "fundamentals, bull/bear debate, and risk-adjusted trade signal."
                    ),
                    "price_usdc": 5.00,
                    "delivery": "~3 minutes",
                },
                {
                    "id": "analysis_priority",
                    "name": "Priority Analysis Report",
                    "description": "Same as single analysis with expedited processing.",
                    "price_usdc": 8.00,
                    "delivery": "~2 minutes",
                },
            ],
            "wallet_address": self.wallet_address,
            "payment_currency": "USDC",
            "payment_chain": "Base",
        }


# ─── Singleton ────────────────────────────────────────────────

founder_agent = LocusFounderAgent()
