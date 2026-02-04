from flask_login import UserMixin
from bson.objectid import ObjectId
from app.extensions import db

class User(UserMixin):
    def __init__(self, user_dict):
        self.id = str(user_dict["_id"])   # REQUIRED by Flask-Login
        self.email = user_dict.get("email")

    @staticmethod
    def find_by_id(user_id):
        try:
            print(f"[User.find_by_id] Looking for user_id: {user_id}")
            print(f"[User.find_by_id] db object: {db}")
            oid = ObjectId(user_id)
            print(f"[User.find_by_id] ObjectId: {oid}")
            result = db.users.find_one({"_id": oid})
            print(f"[User.find_by_id] Result: {result}")
            return result
        except Exception as e:
            print(f"[User.find_by_id] ERROR: {e}")
            return None