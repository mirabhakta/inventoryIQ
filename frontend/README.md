# InventoryIQ Frontend

React 19 + Vite dashboard for the InventoryIQ forecasting API.

## Run Locally

The backend must be running at `http://localhost:8000` (see the root README).

```bash
npm ci
npm run dev
```

The app is served at `http://localhost:5173`.

## Environment

The API URL defaults to `http://localhost:8000`. To use a different backend,
copy `.env.example` to `.env.local` and set:

```env
VITE_API_BASE_URL=https://your-api.example.com
```

## Scripts

| Command | Description |
|---|---|
| `npm run dev` | Start the Vite dev server |
| `npm run build` | Production build to `dist/` |
| `npm run preview` | Preview the production build |
| `npm run lint` | Run ESLint |
