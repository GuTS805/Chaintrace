# Frontend (Next.js 14)

Dark, dense, terminal-adjacent investigator UI for the VASP attribution platform.

## Run

```bash
cd frontend
npm install
cp .env.example .env.local   # point NEXT_PUBLIC_API_BASE at the backend
npm run dev                  # http://localhost:3000
```

The backend must be running (`make dev`) and seeded (`make seed-demo`).

## Pages

- `/` — wallet search + offline demo wallets
- `/wallets/{address}` — attribution panel (probability bars + expandable
  evidence), risk panel, React Flow transaction graph (click a node to trace it),
  attach-to-case
- `/cases`, `/cases/{id}` — create cases, attach wallets, add findings/notes

## Checks

```bash
npm run typecheck   # tsc --noEmit
npm run build       # production build
```
