"""Notification routes for fetching and managing user notifications."""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from bson import ObjectId
from datetime import datetime

from app.extensions import db as mongo
from app.core import NotificationService

bp = Blueprint("notifications", __name__)


@bp.route("/", methods=["GET"])
@jwt_required()
def get_notifications():
    """
    Get user's notifications with pagination.
    
    Query params:
    - page: Page number (default: 1)
    - per_page: Items per page (default: 20)
    - unread_only: If true, only unread notifications (default: false)
    """
    user_id = get_jwt_identity()
    
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 20))
    unread_only = request.args.get("unread_only", "false").lower() == "true"
    
    skip = (page - 1) * per_page
    
    # Build query
    query = {"user_id": ObjectId(user_id)}
    if unread_only:
        query["read"] = False
    
    # Get notifications
    notifications = list(
        mongo.notifications.find(query)
        .sort("created_at", -1)
        .skip(skip)
        .limit(per_page)
    )
    
    # Count total and unread
    total = mongo.notifications.count_documents(query)
    unread_count = mongo.notifications.count_documents({
        "user_id": ObjectId(user_id),
        "read": False
    })
    
    # Format response
    for notif in notifications:
        notif["_id"] = str(notif["_id"])
        notif["user_id"] = str(notif["user_id"])
        if notif.get("created_at"):
            notif["created_at"] = notif["created_at"].isoformat()
    
    return jsonify({
        "notifications": notifications,
        "page": page,
        "per_page": per_page,
        "total": total,
        "pages": (total + per_page - 1) // per_page,
        "unread_count": unread_count
    })


@bp.route("/unread-count", methods=["GET"])
@jwt_required()
def get_unread_count():
    """Get count of unread notifications."""
    user_id = get_jwt_identity()
    
    count = mongo.notifications.count_documents({
        "user_id": ObjectId(user_id),
        "read": False
    })
    
    return jsonify({"unread_count": count})


@bp.route("/<notification_id>/read", methods=["POST"])
@jwt_required()
def mark_as_read(notification_id):
    """Mark a notification as read."""
    user_id = get_jwt_identity()
    
    try:
        notif_oid = ObjectId(notification_id)
    except:
        return jsonify({"error": "Invalid notification ID"}), 400
    
    result = mongo.notifications.update_one(
        {"_id": notif_oid, "user_id": ObjectId(user_id)},
        {"$set": {"read": True, "read_at": datetime.utcnow()}}
    )
    
    if result.matched_count == 0:
        return jsonify({"error": "Notification not found"}), 404
    
    return jsonify({"status": "ok", "message": "Marked as read"})


@bp.route("/read-all", methods=["POST"])
@jwt_required()
def mark_all_as_read():
    """Mark all notifications as read."""
    user_id = get_jwt_identity()
    
    result = mongo.notifications.update_many(
        {"user_id": ObjectId(user_id), "read": False},
        {"$set": {"read": True, "read_at": datetime.utcnow()}}
    )
    
    return jsonify({
        "status": "ok",
        "message": f"Marked {result.modified_count} notifications as read"
    })


@bp.route("/<notification_id>", methods=["DELETE"])
@jwt_required()
def delete_notification(notification_id):
    """Delete a notification."""
    user_id = get_jwt_identity()
    
    try:
        notif_oid = ObjectId(notification_id)
    except:
        return jsonify({"error": "Invalid notification ID"}), 400
    
    result = mongo.notifications.delete_one({
        "_id": notif_oid,
        "user_id": ObjectId(user_id)
    })
    
    if result.deleted_count == 0:
        return jsonify({"error": "Notification not found"}), 404
    
    return jsonify({"status": "ok", "message": "Notification deleted"})


@bp.route("/clear", methods=["DELETE"])
@jwt_required()
def clear_all_notifications():
    """Clear all notifications for the user."""
    user_id = get_jwt_identity()
    
    result = mongo.notifications.delete_many({
        "user_id": ObjectId(user_id)
    })
    
    return jsonify({
        "status": "ok",
        "message": f"Cleared {result.deleted_count} notifications"
    })


@bp.route("/poll", methods=["GET"])
@jwt_required()
def poll_notifications():
    """
    Poll for new notifications (for real-time updates without WebSocket).
    
    Query params:
    - since: ISO timestamp to get notifications since (optional)
    """
    user_id = get_jwt_identity()
    
    since = request.args.get("since")
    
    query = {
        "user_id": ObjectId(user_id),
        "read": False
    }
    
    if since:
        try:
            since_dt = datetime.fromisoformat(since.replace("Z", "+00:00"))
            query["created_at"] = {"$gt": since_dt}
        except:
            pass
    
    notifications = list(
        mongo.notifications.find(query)
        .sort("created_at", -1)
        .limit(50)
    )
    
    for notif in notifications:
        notif["_id"] = str(notif["_id"])
        notif["user_id"] = str(notif["user_id"])
        if notif.get("created_at"):
            notif["created_at"] = notif["created_at"].isoformat()
    
    return jsonify({
        "notifications": notifications,
        "timestamp": datetime.utcnow().isoformat()
    })
