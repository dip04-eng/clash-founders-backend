"""
models/participant_model.py
---------------------------
Participant data access layer.
Handles all CRUD operations for the participants collection.
"""

import logging
from datetime import datetime, timezone
from bson import ObjectId
from database.mongodb import get_db

logger = logging.getLogger(__name__)


def create_participant(name: str, phone: str, socket_id: str = "") -> dict:
    """
    Create a new participant in the database.
    
    Args:
        name: Participant's full name
        phone: Participant's phone number (must be unique)
        socket_id: Socket.IO session ID
    
    Returns:
        The created participant document
    
    Raises:
        ValueError: If phone number already exists
    """
    db = get_db()

    participant = {
        "name": name,
        "phone": phone,
        "score": 0,
        "joined_at": datetime.now(timezone.utc),
        "socket_id": socket_id,
        "answers": []
    }

    result = db.participants.insert_one(participant)
    participant["_id"] = result.inserted_id
    logger.info(f"✅ Participant created: {name} ({phone})")
    return participant


def get_participant_by_id(participant_id: str) -> dict:
    """Fetch a participant by their ObjectId."""
    db = get_db()
    return db.participants.find_one({"_id": ObjectId(participant_id)})


def get_participant_by_phone(phone: str) -> dict:
    """Fetch a participant by their phone number."""
    db = get_db()
    return db.participants.find_one({"phone": phone})


def get_participant_by_socket(socket_id: str) -> dict:
    """Fetch a participant by their socket ID."""
    db = get_db()
    return db.participants.find_one({"socket_id": socket_id})


def update_socket_id(participant_id: str, socket_id: str):
    """Update the socket ID for a participant (on reconnect)."""
    db = get_db()
    db.participants.update_one(
        {"_id": ObjectId(participant_id)},
        {"$set": {"socket_id": socket_id}}
    )
    logger.info(f"Socket ID updated for participant {participant_id}")


def update_score(participant_id: str, points: int):
    """
    Increment a participant's total score.
    
    Args:
        participant_id: The participant's ObjectId string
        points: Points to add to the current score
    """
    db = get_db()
    db.participants.update_one(
        {"_id": ObjectId(participant_id)},
        {"$inc": {"score": points}}
    )
    logger.info(f"Score updated for {participant_id}: +{points} points")


def add_answer(participant_id: str, answer: dict):
    """
    Append an answer record to a participant's answers array.
    
    Args:
        participant_id: The participant's ObjectId string
        answer: Answer dict with questionId, selected, timeMs, correct, points
    """
    db = get_db()
    db.participants.update_one(
        {"_id": ObjectId(participant_id)},
        {"$push": {"answers": answer}}
    )


def get_all_participants() -> list:
    """Fetch all participants sorted by score descending."""
    db = get_db()
    return list(db.participants.find().sort("score", -1))


def get_leaderboard() -> list:
    """
    Get the leaderboard — all participants sorted by score (DESC),
    then by average response time (ASC) as tiebreaker.
    """
    db = get_db()
    participants = list(db.participants.find().sort("score", -1))

    leaderboard = []
    for rank, p in enumerate(participants, 1):
        # Calculate average response time from answers
        answers = p.get("answers", [])
        avg_time = 0
        if answers:
            total_time = sum(a.get("timeMs", 0) for a in answers)
            avg_time = round(total_time / len(answers) / 1000, 2)

        leaderboard.append({
            "rank": rank,
            "id": str(p["_id"]),
            "name": p["name"],
            "phone": p["phone"],
            "score": p["score"],
            "responseTime": avg_time,
            "answers": p.get("answers", [])
        })

    # Sort by score DESC, then responseTime ASC as tiebreaker
    leaderboard.sort(key=lambda x: (-x["score"], x["responseTime"]))

    # Re-assign ranks after sorting
    for i, entry in enumerate(leaderboard):
        entry["rank"] = i + 1

    return leaderboard


def reset_all_participants():
    """Reset all participants' scores and answers (for quiz reset)."""
    db = get_db()
    db.participants.update_many(
        {},
        {"$set": {"score": 0, "answers": []}}
    )
    logger.info("All participant scores and answers have been reset")


def delete_all_participants():
    """Delete all participants (for full quiz reset)."""
    db = get_db()
    result = db.participants.delete_many({})
    logger.info(f"Deleted {result.deleted_count} participants")


def serialize_participant(participant: dict) -> dict:
    """Convert a participant document to a JSON-safe dict."""
    if not participant:
        return None
    return {
        "id": str(participant["_id"]),
        "name": participant["name"],
        "phone": participant["phone"],
        "score": participant.get("score", 0),
        "joined_at": participant.get("joined_at", "").isoformat() if participant.get("joined_at") else "",
        "socket_id": participant.get("socket_id", ""),
        "answers": participant.get("answers", []),
        "responseTime": _calc_avg_time(participant.get("answers", []))
    }


def _calc_avg_time(answers: list) -> float:
    """Calculate average response time from answers list."""
    if not answers:
        return 0
    total_time = sum(a.get("timeMs", 0) for a in answers)
    return round(total_time / len(answers) / 1000, 2)
