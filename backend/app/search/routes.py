from flask import Blueprint, request, jsonify
from bson.objectid import ObjectId
from bson.errors import InvalidId

from app import bcrypt
from app.extensions import db

search = Blueprint("search", __name__)