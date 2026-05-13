# Locus Integration Guide

This document explains how Quorum integrates with Locus for the LocusFounder hackathon track.

---

## Overview

Locus provides AI agents with a USDC wallet on Base, spending controls, and a Checkout SDK. Quorum uses three Locus capabilities:

| Capability | How Quorum Uses It |
|:-----------|:-------------------|
| Agent Wallet | Receives $5 USDC per analysis from clients |
| Checkout SDK | Creates payment sessions clients use to pay |
| Balance API | Tracks revenue and available funds |

---

## Setup

### Production (Live)

The backend is deployed at `https://quorum-backend-74691596771.us-central1.run.app`.
The LocusFounder storefront is live at `https://svc-mp4160jcaxqzmks9.buildwithlocus.com`.

No local setup needed to use the live system.

### Local Development

Leave `LOCUS_API_KEY` blank in your `.env`. On first startup, the `LocusFounderAgent` calls the Locus beta self-registration endpoint:

Leave `LOCUS_API_KEY` blank in your `.env`. On first startup, the `LocusFounderAgent` calls the Locus beta self-registration endpoint:

```
POST https://beta-api.paywithlocus.com/api/register
{ "name": "Quorum Trading Intelligence" }
```

The agent receives an API key and wallet ID, polls until the wallet is deployed on Base, then saves credentials to `backend/db/locus_credentials.json`.

Credentials persist across restarts. Delete `locus_credentials.json` to force re-registration.

### Option B — Manual Setup

1. Sign up at [beta.paywithlocus.com](https://beta.paywithlocus.com) using code `PAYGENTIC`
2. Create a wallet from the dashboard
3. Generate an API key (prefix: `claw_dev_`)
4. Add to `backend/.env`:
   ```
   LOCUS_API_KEY=claw_dev_your_key_here
   ```

### Funding the Wallet

Send USDC on Base to your wallet address, or request the $10 hackathon credits:

```bash
curl -X POST https://beta-api.paywithlocus.com/api/gift-code-requests \
  -H "Authorization: Bearer YOUR_API_KEY"
```

---

## Payment Flow

### 1. Create a Checkout Session

```bash
curl -X POST https://quorum-backend-74691596771.us-central1.run.app/locus/checkout \
  -H "Content-Type: application/json" \
  -d '{"ticker": "AAPL", "asset_type": "stock"}'
```

Response:
```json
{
  "session_id": "abc123...",
  "ticker": "AAPL",
  "asset_type": "stock",
  "price_usdc": 5.00,
  "checkout_url": "https://checkout.paywithlocus.com/...",
  "status": "pending",
  "expires_at": "2025-05-03T12:30:00"
}
```

### 2. Client Pays

The client opens `checkout_url` and pays $5 USDC. The checkout page is machine-readable — other agents can pay programmatically.

### 3. Poll for Confirmation

```bash
curl https://quorum-backend-74691596771.us-central1.run.app/locus/checkout/abc123.../status
```

Once paid, the response includes `"paid": true` and `"analysis_triggered": true`. The pipeline starts automatically in the background.

### 4. Receive Results

Subscribe to the WebSocket at `ws://localhost:8000/ws/live` to receive real-time analysis progress and the final report.

---

## Development / Demo Mode

For demos without real USDC, use the mock payment endpoint:

```bash
# 1. Create session
curl -X POST https://quorum-backend-74691596771.us-central1.run.app/locus/checkout \
  -d '{"ticker": "NVDA", "asset_type": "stock"}'

# 2. Simulate payment (dev only)
curl -X POST https://quorum-backend-74691596771.us-central1.run.app/locus/mock-pay/{session_id}

# 3. Poll status — analysis triggers automatically
curl https://quorum-backend-74691596771.us-central1.run.app/locus/checkout/{session_id}/status
```

Mock sessions are identified by a `"mock": true` field in the response. They auto-confirm without hitting the Locus API.

---

## Checking Wallet Balance

```bash
curl https://quorum-backend-74691596771.us-central1.run.app/locus/wallet
```

```json
{
  "balance_usdc": 10.00,
  "wallet_address": "0x...",
  "currency": "USDC",
  "chain": "Base"
}
```

---

## Revenue Tracking

```bash
curl https://quorum-backend-74691596771.us-central1.run.app/locus/revenue
```

```json
{
  "total_sessions": 4,
  "paid_sessions": 3,
  "fulfilled_sessions": 2,
  "pending_sessions": 1,
  "total_revenue_usdc": 15.00,
  "fulfilled_revenue_usdc": 10.00,
  "price_per_analysis_usdc": 5.00
}
```

---

## Storefront

The `/locus/business` endpoint returns the public-facing service catalog:

```bash
curl https://quorum-backend-74691596771.us-central1.run.app/locus/business
```

```json
{
  "name": "Quorum Trading Intelligence",
  "description": "Autonomous AI trading research firm...",
  "services": [
    {
      "id": "analysis_single",
      "name": "Single Analysis Report",
      "price_usdc": 5.00,
      "delivery": "~3 minutes"
    }
  ],
  "wallet_address": "0x...",
  "payment_currency": "USDC",
  "payment_chain": "Base"
}
```

This endpoint is machine-readable — other agents can discover and purchase Quorum's services autonomously.

---

## Locus API Endpoints Used

| Endpoint | Method | Purpose |
|:---------|:------:|:--------|
| `/api/register` | POST | Agent self-registration |
| `/api/status` | GET | Wallet deployment status |
| `/api/pay/balance` | GET | Check USDC balance |
| `/api/pay/send` | POST | Send USDC to address |
| `/api/checkout/sessions` | POST | Create checkout session |
| `/api/checkout/sessions/{id}` | GET | Check payment status |
| `/api/checkout/agent/pay/{id}` | POST | Agent-to-agent payment |
| `/api/gift-code-requests` | POST | Request hackathon credits |

All requests use base URL `https://beta-api.paywithlocus.com`.

---

## Credentials File

After auto-registration, credentials are saved to `backend/db/locus_credentials.json`:

```json
{
  "api_key": "claw_dev_...",
  "wallet_id": "...",
  "wallet_address": "0x...",
  "owner_address": "0x...",
  "claim_url": "https://beta.paywithlocus.com/register/claim/..."
}
```

Visit the `claim_url` to link the agent wallet to your Locus dashboard account for monitoring.

This file is excluded from git via `.gitignore`. Never commit it.
