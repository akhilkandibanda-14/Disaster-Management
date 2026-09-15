# Disaster Management Frontend

React and Vite dashboard for the AI-based disaster management and safe evacuation system.

## Prerequisites

- Node.js 20 or newer
- The FastAPI backend running locally

## Install and run

```powershell
npm install
npm run dev
```

Open the local URL shown by Vite, usually `http://localhost:5173`.

## Available commands

```powershell
npm run dev      # Start the Vite development server
npm run build    # Create a production build
npm run preview  # Preview the production build locally
```

## API configuration

The dashboard connects to `http://127.0.0.1:8000` by default. To use another backend URL, create `frontend/.env` with:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

The frontend calls the backend health, weather, risk map, shelter, alert, road-condition, and evacuation-route endpoints. Start the backend from the repository root with:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
```

When the backend is using its default demo mode, the dashboard labels simulated data clearly. Demo data is for development only and must not be treated as an official emergency warning or authoritative evacuation instruction.
