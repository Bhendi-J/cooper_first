from pymongo import MongoClient

_client = None
_db = None

def init_mongo(app):
    global _client, _db
    mongo_uri = app.config["MONGO_URI"]
    _client = MongoClient(mongo_uri)
    
    # get_default_database() extracts DB name from URI (e.g., /prepify?)
    # If that fails, use a fallback
    _db = _client.get_default_database()
    if _db is None:
        # Fallback: extract database name from URI or use default
        _db = _client["prepify"]
    
    print(f"[MongoDB] Connected to database: {_db.name}")

def get_db():
    """Get the database instance. Must be called after init_mongo."""
    return _db

def get_client():
    """Get the MongoDB client instance. Must be called after init_mongo."""
    return _client

# For backward compatibility, create a proxy that always returns current db
class _DBProxy:
    def __getattr__(self, name):
        if _db is None:
            raise RuntimeError("Database not initialized. Call init_mongo first.")
        return getattr(_db, name)
    
    def __getitem__(self, name):
        if _db is None:
            raise RuntimeError("Database not initialized. Call init_mongo first.")
        return _db[name]
    
    def __bool__(self):
        return _db is not None

db = _DBProxy()