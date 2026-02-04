import { Link } from "react-router-dom";

export default function NotFound() {
  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="text-center">
        <h1 className="text-6xl font-bold mb-4">404</h1>
        <p className="text-muted-foreground mb-6">Page not found</p>
        <Link
          to="/"
          className="px-6 py-3 bg-primary text-primary-foreground rounded-lg hover:opacity-90"
        >
          Go Home
        </Link>
      </div>
    </div>
  );
}
