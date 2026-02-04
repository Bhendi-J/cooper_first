from flask import Blueprint, request, jsonify

bp = Blueprint("wallets", __name__, url_prefix="/wallets")


@bp.route("/balance/<user_id>", methods=["GET"])
def balance(user_id):
    return jsonify({"user_id": user_id, "balance": 0})


@bp.route("/deposit", methods=["POST"])
def deposit():
    data = request.get_json() or {}
    return jsonify({"status": "ok", "data": data}), 201
