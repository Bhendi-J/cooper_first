from flask import Blueprint, request, jsonify

bp = Blueprint("payments", __name__, url_prefix="/payments")


@bp.route("/intent", methods=["POST"])
def create_intent():
    data = request.get_json() or {}
    return jsonify({"status": "created", "data": data}), 201


@bp.route("/intent/<intent_id>", methods=["GET"])
def get_intent(intent_id):
    return jsonify({"id": intent_id, "status": "pending"})
