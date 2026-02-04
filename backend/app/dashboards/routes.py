from flask import Blueprint, jsonify

bp = Blueprint("dashboards", __name__, url_prefix="/dashboards")


@bp.route("/summary/<user_id>", methods=["GET"])
def summary(user_id):
    return jsonify({"user_id": user_id, "summary": {}})
