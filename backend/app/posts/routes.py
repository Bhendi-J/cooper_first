from flask import Blueprint, request, jsonify
from bson.objectid import ObjectId
from bson.errors import InvalidId
from app.extensions import db

posts = Blueprint("posts", __name__)

