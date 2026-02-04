import { Link } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";

export default function HomePage() {
  const { user } = useAuth();

  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="text-center">
        <h1 className="text-4xl font-bold mb-4">🚀 Hackathon Starter</h1>
        <p className="text-muted-foreground mb-8">
          Ready to build something amazing
        </p>

        {user ? (
          <div>
            <p className="mb-4">Welcome, {user.email}!</p>
            <Link
              to="/dashboard"
              className="inline-block px-6 py-3 bg-primary text-primary-foreground rounded-lg hover:opacity-90"
            >
              Go to Dashboard
            </Link>
          </div>
        ) : (
          <div className="flex gap-4 justify-center">
            <Link
              to="/login"
              className="px-6 py-3 bg-primary text-primary-foreground rounded-lg hover:opacity-90"
            >
              Login
            </Link>
            <Link
              to="/register"
              className="px-6 py-3 border border-border rounded-lg hover:bg-secondary"
            >
              Register
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}
