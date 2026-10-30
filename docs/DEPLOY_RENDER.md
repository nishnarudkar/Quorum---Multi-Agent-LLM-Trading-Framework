# Deploying Quorum on Render

This guide walks you through deploying both the **Quorum Backend** (FastAPI) and **Quorum Frontend** (Next.js) on [Render](https://render.com).

---

## Method 1: 1-Click Blueprint Deploy (Recommended)

Quorum includes a [`render.yaml`](../render.yaml) blueprint file that can automatically spin up both the backend and frontend web services.

1. **Push your code to GitHub** (if not already pushed).
2. Go to the [Render Dashboard](https://dashboard.render.com).
3. Click **New +** > **Blueprint**.
4. Connect your Quorum repository.
5. Render will detect `render.yaml` and prompt you for the required environment variables:
   - `GROQ_API_KEY`: Enter your Groq API key (from [console.groq.com](https://console.groq.com)).
   - `NEXT_PUBLIC_API_URL`: Initially, leave blank or put a placeholder. Once Render assigns your backend URL (e.g., `https://quorum-backend.onrender.com`), set this to that URL and trigger a frontend redeploy.
   - `NEXT_PUBLIC_WS_URL`: Set to `wss://quorum-backend.onrender.com/ws/live` (match your backend domain).
6. Click **Apply**. Render will build and deploy both services.

---

## Method 2: Manual Dashboard Deploy

If you prefer to configure the services manually in the Render dashboard:

### 1. Deploy the Backend Service

1. In Render Dashboard, click **New +** > **Web Service**.
2. Connect your Quorum repository.
3. Configure the service:
   - **Name**: `quorum-backend`
   - **Region**: Any (e.g. `Oregon (US West)`)
   - **Branch**: `main`
   - **Runtime**: **Docker**
   - **Dockerfile Path**: `./backend/Dockerfile`
   - **Docker Context**: `./backend`
   - **Instance Type**: `Free` (or `Starter`)
4. Add **Environment Variables**:
   | Variable | Value | Notes |
   |---|---|---|
   | `GROQ_API_KEY` | `gsk_...` | **Required** for agent execution |
   | `CORS_ORIGINS` | `http://localhost:3000,https://<your-frontend-name>.onrender.com` | Comma-separated allowed origins |
   | `SCANNER_ENABLED` | `false` | Set `true` if you want continuous background scans |
   | `PRICE_POLL_INTERVAL` | `15` | Seconds between price ticker updates |
   | `ALPACA_API_KEY` | `...` | *(Optional)* For paper trading |
   | `ALPACA_SECRET_KEY` | `...` | *(Optional)* For paper trading |
   | `ALPACA_PAPER` | `true` | *(Optional)* Always test in paper mode first |
5. Set Health Check Path: `/health`
6. Click **Create Web Service**.
7. Note down your backend URL (e.g., `https://quorum-backend-xyz.onrender.com`).

---

### 2. Deploy the Frontend Service

Next.js embeds `NEXT_PUBLIC_*` environment variables into the bundle **at build time**, so deploy the backend first to obtain its URL.

1. In Render Dashboard, click **New +** > **Web Service**.
2. Connect your Quorum repository.
3. Configure the service:
   - **Name**: `quorum-frontend`
   - **Region**: Same as backend
   - **Branch**: `main`
   - **Root Directory**: `frontend`
   - **Runtime**: **Node**
   - **Build Command**: `npm ci && npm run build`
   - **Start Command**: `npm start`
   - **Instance Type**: `Free` (or `Starter`)
4. Add **Environment Variables**:
   | Variable | Value |
   |---|---|
   | `NODE_VERSION` | `20.18.0` |
   | `NEXT_PUBLIC_API_URL` | `https://quorum-backend-xyz.onrender.com` |
   | `NEXT_PUBLIC_WS_URL` | `wss://quorum-backend-xyz.onrender.com/ws/live` |
5. Click **Create Web Service**.

---

### 3. Update Backend CORS

Once your frontend is deployed, copy its Render URL (e.g., `https://quorum-frontend-xyz.onrender.com`):
1. Navigate to `quorum-backend` in the Render dashboard.
2. Go to **Environment**.
3. Update `CORS_ORIGINS`:
   ```env
   http://localhost:3000,https://quorum-frontend-xyz.onrender.com
   ```
4. Click **Save Changes** (this will trigger a quick redeploy of the backend).

---

## Important Render Tips

- **Free Tier Cold Starts**: Render's free web services spin down after 15 minutes of inactivity. The first request after a sleep period may take ~45–60 seconds to respond while the container wakes up.
- **WebSockets on Render**: Render supports persistent HTTP/1.1 WebSockets natively on both Free and Paid tiers.
- **Port Handling**: Render automatically injects the `$PORT` environment variable (default 10000). The Quorum backend Dockerfile dynamically binds to `${PORT:-8000}`, so no manual port configuration is needed.
- **Persistence**: SQLite databases (`quorum.db`) and cache files in container storage are ephemeral on the free tier. If you require persistent trade logs across container restarts, attach a **Render Persistent Disk** mounted at `/app/db`.
