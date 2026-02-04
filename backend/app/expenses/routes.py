from flask import Blueprint, request, jsonify

bp = Blueprint("expenses", __name__, url_prefix="/expenses")


@bp.route("/", methods=["POST"])
def add():
    data = request.get_json() or {}
    return jsonify({"status": "created", "data": data}), 201


@bp.route("/", methods=["GET"])
def list_expenses():
    return jsonify([])
