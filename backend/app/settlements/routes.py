from flask import Blueprint, jsonify

bp = Blueprint("settlements", __name__, url_prefix="/settlements")


@bp.route("/finalize/<event_id>", methods=["POST"])
def finalize(event_id):
    return jsonify({"event_id": event_id, "status": "settling"})
