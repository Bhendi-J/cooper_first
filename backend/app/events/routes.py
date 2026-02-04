from flask import Blueprint, request, jsonify

bp = Blueprint("events", __name__, url_prefix="/events")


@bp.route("/", methods=["POST"])
def create():
    data = request.get_json() or {}
    return jsonify({"status": "created", "data": data}), 201


@bp.route("/<event_id>", methods=["GET"])
def get_event(event_id):
    return jsonify({"id": event_id})
