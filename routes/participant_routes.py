"""
routes/participant_routes.py
-----------------------------
REST API routes for participant operations.
Handles join, leaderboard, and quiz state endpoints.
"""

import logging
from flask import Blueprint, request, jsonify
from models.participant_model import (
    create_participant,
    get_participant_by_phone,
    get_leaderboard,
    serialize_participant,
    get_all_participants,
)
from services.quiz_service import get_quiz_state
from models.question_model import get_question_count

logger = logging.getLogger(__name__)

# Create blueprint for participant routes
participant_bp = Blueprint("participant", __name__, url_prefix="/api")


@participant_bp.route("/participant/join", methods=["POST"])
def join_quiz():
    """
    POST /api/participant/join
    
    Join the quiz as a participant.
    
    Request Body:
        {
            "name": "Md Asif",
            "phone": "9876543210"
        }
    
    Validation:
        - Name is required
        - Phone is required
        - Phone must be unique
        - Quiz must allow joining (allow_join=true)
    
    Response:
        {
            "success": true,
            "message": "Joined successfully",
            "participant": { ... }
        }
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({
                "success": False,
                "message": "Request body is required"
            }), 400

        name = data.get("name", "").strip()
        phone = data.get("phone", "").strip()

        # Validate name
        if not name:
            return jsonify({
                "success": False,
                "message": "Name is required"
            }), 400

        if len(name) < 3:
            return jsonify({
                "success": False,
                "message": "Name must be at least 3 characters"
            }), 400

        # Validate phone
        if not phone:
            return jsonify({
                "success": False,
                "message": "Phone number is required"
            }), 400

        if not phone.isdigit() or len(phone) != 10:
            return jsonify({
                "success": False,
                "message": "Phone must be exactly 10 digits"
            }), 400

        # Check if quiz allows joining
        quiz_state = get_quiz_state()
        if not quiz_state.get("allow_join", True):
            return jsonify({
                "success": False,
                "message": "Quiz has already started. New participants cannot join."
            }), 403

        # Always create a new participant document (allow multiple participants with same phone)
        participant = create_participant(name=name, phone=phone)
        serialized = serialize_participant(participant)

        logger.info(f"✅ New participant joined: {name} ({phone})")

        return jsonify({
            "success": True,
            "message": "Joined successfully",
            "participant": serialized
        }), 201

    except ValueError as e:
        logger.warning(f"Join validation error: {e}")
        return jsonify({
            "success": False,
            "message": str(e)
        }), 400

    except Exception as e:
        logger.error(f"Join error: {e}")
        return jsonify({
            "success": False,
            "message": "Internal server error"
        }), 500


@participant_bp.route("/leaderboard", methods=["GET"])
def get_leaderboard_route():
    """
    GET /api/leaderboard
    
    Get the current leaderboard sorted by score descending.
    
    Response:
        {
            "success": true,
            "leaderboard": [
                { "rank": 1, "name": "...", "score": 350, ... }
            ]
        }
    """
    try:
        leaderboard = get_leaderboard()
        return jsonify({
            "success": True,
            "leaderboard": leaderboard
        }), 200

    except Exception as e:
        logger.error(f"Leaderboard error: {e}")
        return jsonify({
            "success": False,
            "message": "Failed to fetch leaderboard"
        }), 500


@participant_bp.route("/quiz-state", methods=["GET"])
def get_quiz_state_route():
    """
    GET /api/quiz-state
    
    Get the current quiz state.
    
    Response:
        {
            "success": true,
            "state": {
                "status": "waiting",
                "current_question_index": 0,
                "allow_join": true,
                "total_questions": 20,
                "participant_count": 5
            }
        }
    """
    try:
        state = get_quiz_state()
        participants = get_all_participants()

        return jsonify({
            "success": True,
            "state": {
                "status": state.get("status", "waiting"),
                "current_question_index": state.get("current_question_index", 0),
                "allow_join": state.get("allow_join", True),
                "total_questions": get_question_count(),
                "participant_count": len(participants)
            }
        }), 200

    except Exception as e:
        logger.error(f"Quiz state error: {e}")
        return jsonify({
            "success": False,
            "message": "Failed to fetch quiz state"
        }), 500


@participant_bp.route("/participants", methods=["GET"])
def get_participants_route():
    """
    GET /api/participants
    
    Get all participants.
    
    Response:
        {
            "success": true,
            "participants": [ ... ]
        }
    """
    try:
        participants = get_all_participants()
        serialized = [serialize_participant(p) for p in participants]

        return jsonify({
            "success": True,
            "participants": serialized
        }), 200

    except Exception as e:
        logger.error(f"Participants error: {e}")
        return jsonify({
            "success": False,
            "message": "Failed to fetch participants"
        }), 500
