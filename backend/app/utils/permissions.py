"""Permission helpers."""

def is_creator(user, obj):
    return getattr(obj, "creator_id", None) == getattr(user, "id", None)
