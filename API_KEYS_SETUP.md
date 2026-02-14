# FluxRoute API Keys Setup Guide

FluxRoute requires 2 API keys to be fully functional (plus 1 optional key). This guide walks you through obtaining each key and configuring your environment files.

## Overview

| API Key | Purpose | Required? | Cost |
|---------|---------|-----------|------|
| Mapbox Token | Map display, geocoding, directions | **CRITICAL** | Free (50k loads/month) |
| Google Gemini API Key | Gemini AI chat assistant | **Yes** | Free (rate limited) / Pay-per-use |
| Metrolinx API Key | GO Transit real-time data | Optional | Free (registration required) |

## Required API Keys

### 1. Mapbox Token

**What it does:** Powers the interactive map, location search autocomplete, and driving/walking directions.

**How to get it:**

1. Go to [https://account.mapbox.com/auth/signup/](https://account.mapbox.com/auth/signup/)
2. Create a free account (no credit card required)
3. After signup, your default public token appears on the dashboard at [https://account.mapbox.com/access-tokens/](https://account.mapbox.com/access-tokens/)
4. Copy the token starting with `pk.`

**Free tier limits:**
- 50,000 map loads per month
- 100,000 directions requests per month

**Where to set it:**
- `backend/.env` → `MAPBOX_TOKEN=pk.xxxxx`
- `frontend/.env.local` → `NEXT_PUBLIC_MAPBOX_TOKEN=pk.xxxxx` (use the same token in both files)

---

### 2. Google Gemini API Key

**What it does:** Powers the Gemini AI chat assistant that helps users plan trips and answers transit questions.

**How to get it:**

1. Go to [https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)
2. Sign in with your Google account
3. Click **Create API key**
4. Copy the generated API key

**Pricing:**
- Free tier available (rate limited)
- Pay-as-you-go for higher limits

**Where to set it:**
- `backend/.env` → `GEMINI_API_KEY=your_key_here`

---

## Optional API Key

### 3. Metrolinx API Key

**What it does:** Fetches real-time GO Transit vehicle positions for more accurate regional transit routing.

**How to get it:**

1. Apply at [https://www.gotransit.com/en/open-data](https://www.gotransit.com/en/open-data)
2. Wait for approval (can take several days)

**Note:** The app uses mock GO Transit data as fallback, so it works fine without this key.

**Where to set it:**
- `backend/.env` → `METROLINX_API_KEY=xxxxx`

---

## Environment File Setup

### Backend — `backend/.env`

```
GEMINI_API_KEY=your-api-key-here
MAPBOX_TOKEN=pk.your-token-here
METROLINX_API_KEY=
```

### Frontend — `frontend/.env.local`

```
NEXT_PUBLIC_MAPBOX_TOKEN=pk.your-token-here
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## Activation Steps

1. **Fill in your API keys** in both environment files
2. **Restart both servers:**
   ```bash
   # Backend
   cd backend
   python3 -m uvicorn app.main:app --reload

   # Frontend (separate terminal)
   cd frontend
   npm run dev
   ```
3. **Verify** the map loads and AI chat responds

---

## Troubleshooting

**Map doesn't load:**
- Check that `MAPBOX_TOKEN` is set in **both** `backend/.env` and `frontend/.env.local`
- Ensure the token starts with `pk.`
- Verify you restarted both servers

**AI chat doesn't work:**
- Confirm `GEMINI_API_KEY` is set in `backend/.env`
- Check backend logs for authentication errors

---

## Security Notes

- **Never commit** `.env` or `.env.local` files to version control (both are already in `.gitignore`)
- The Mapbox token (`pk.`) is public-safe and can be exposed in frontend code
- The Gemini API key should be kept server-side only
