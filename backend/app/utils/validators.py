"""Request validators (placeholders)."""

def require_keys(payload, *keys):
    missing = [k for k in keys if k not in (payload or {})]
    if missing:
        raise ValueError(f"missing keys: {missing}")
    return True
