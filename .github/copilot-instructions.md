# Copilot Instructions for This Codebase

## Architecture Overview
- **Monorepo** with `backend/` (Flask, MongoDB) and `frontend/` (Vite, React, TypeScript, Tailwind, shadcn-ui)
- **Backend**: Modular Flask app with blueprints for `auth`, `users`, `events`, `expenses`, etc. MongoDB is used for persistence (see `app/extensions.py`).
- **Frontend**: Modern React app using Vite, shadcn-ui, and Tailwind. UI components are in `src/components/ui/`. State is managed with Zustand (`store/`).

## Key Workflows
- **Backend**
  - Start: `python run.py` (runs Flask app in debug mode)
  - Dependencies: `pip install -r requirements.txt`
  - Environment: Configured via `.env` (see `app/config.py` for required keys)
  - Blueprints: Register new API modules in `app/__init__.py`
- **Frontend**
  - Start: `npm run dev` (Vite dev server)
  - Build: `npm run build`
  - Test: `npm run test` or `npm run test:watch`
  - Lint: `npm run lint`

## Project Conventions
- **API URLs**: All backend APIs are prefixed with `/api/v1/{module}` (e.g., `/api/v1/events`).
- **CORS**: Only allows requests from `http://localhost:5173` and `http://localhost:8080` (see `app/__init__.py`).
- **JWT Auth**: Uses `Authorization: Bearer <token>` header (see `app/config.py`).
- **MongoDB**: Connection and models are managed in `app/extensions.py` and respective `models.py` files per module.
- **Frontend Routing**: Uses React Router (`src/pages/` for main views).
- **UI Components**: Use shadcn-ui patterns; extend from `src/components/ui/` when possible.
- **State Management**: Use Zustand stores in `src/store/` for global state.

## Integration Points
- **Auth**: JWT-based, endpoints in `app/auth/routes.py` and `app/users/routes.py`.
- **Events/Expenses**: Modularized, each with its own models, routes, and services.
- **Mail**: Configured via Flask-Mail, credentials in `.env`.
- **Frontend-Backend**: Communicate via REST, see `src/lib/api.ts` for API helpers.

## Examples
- To add a new backend module:
  1. Create a folder in `app/`, add `routes.py`, `models.py`, etc.
  2. Register its blueprint in `app/__init__.py`.
- To add a new frontend page:
  1. Add a file to `src/pages/`.
  2. Add a route in the main router (see `App.tsx`).

## References
- Backend entry: `backend/run.py`, config: `backend/app/config.py`
- Frontend entry: `frontend/src/main.tsx`, config: `frontend/package.json`
- API helpers: `frontend/src/lib/api.ts`

---
For more details, see the respective `README.md` files or ask for specific module guidance.
