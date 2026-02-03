# 🚀 Hackathon Starter Kit

Full-stack React + Flask + MongoDB boilerplate with authentication ready to go.


git commands.

## Quick Start (5 minutes)

### Prerequisites
- Node.js 18+ & pnpm
- Python 3.10+
- MongoDB running locally

### 1. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env
# Edit .env with your settings

# Run server
python run.py
```

Backend runs at `http://localhost:5000`

### 2. Frontend Setup

```bash
cd frontend

# Install dependencies
pnpm install

# Copy environment file
cp .env.example .env

# Run dev server
pnpm dev
```

Frontend runs at `http://localhost:5173`

---

## 📁 Project Structure

```
├── backend/
│   ├── app/
│   │   ├── auth/       # Login, logout, session
│   │   ├── users/      # User CRUD operations
│   │   ├── search/     # Search functionality
│   │   ├── config.py   # App configuration
│   │   └── extensions.py
│   └── run.py
│
├── frontend/
│   ├── src/
│   │   ├── api/        # Axios API calls
│   │   ├── components/ # Reusable UI components
│   │   ├── context/    # Auth state management
│   │   ├── hooks/      # Custom React hooks
│   │   ├── pages/      # Route pages
│   │   └── utils/      # Helper functions
│   └── index.html
```

---

## 🔌 API Endpoints

### Auth
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/login` | Login with email/password |
| POST | `/api/auth/logout` | Logout current user |
| GET | `/api/auth/me` | Get current user |

### Users
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/users` | Register new user |
| GET | `/api/users/all` | Get all users |
| GET | `/api/users/<id>` | Get user by ID |

---

## 🧩 Using Components

```jsx
import { Button, Input, Card } from "./components/ui";

// Button variants: primary, secondary, danger, ghost
<Button variant="primary" loading={isLoading}>
  Submit
</Button>

// Input with label and error
<Input 
  label="Email" 
  type="email" 
  error={errors.email} 
/>

// Card with sections
<Card>
  <Card.Header>
    <Card.Title>Title</Card.Title>
  </Card.Header>
  <Card.Body>Content</Card.Body>
  <Card.Footer>Actions</Card.Footer>
</Card>
```

---

## 🔒 Protected Routes

```jsx
import ProtectedRoute from "./components/ProtectedRoute";

<Route 
  path="/dashboard" 
  element={
    <ProtectedRoute>
      <Dashboard />
    </ProtectedRoute>
  } 
/>
```

---

## 🎯 Auth Context

```jsx
import { useAuth } from "./context/AuthContext";

function MyComponent() {
  const { user, login, logout, isAuthenticated, loading } = useAuth();
  
  // Use these anywhere in your app!
}
```

---

## 🛠️ Adding New Features

### New Backend Route
1. Create folder in `backend/app/your_feature/`
2. Add `__init__.py` and `routes.py`
3. Register blueprint in `app/__init__.py`

### New Frontend Page
1. Create component in `frontend/src/pages/`
2. Add route in `App.jsx`

---

## 📦 Tech Stack

| Frontend | Backend |
|----------|---------|
| React 18 | Flask |
| Vite | MongoDB |
| Tailwind CSS | Flask-Login |
| React Router | Flask-CORS |
| Axios | Bcrypt |

---

**Good luck at the hackathon! 🏆**
