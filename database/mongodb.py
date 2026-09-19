"""
database/mongodb.py
-------------------
MongoDB Atlas connection manager.
Provides a singleton connection to the quiz database and
handles initialization of collections and indexes.
"""

import logging
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from config import Config

logger = logging.getLogger(__name__)

# Module-level client and database references
_client = None
_db = None


def get_client():
    """Get or create the MongoDB client singleton."""
    global _client
    if _client is None:
        try:
            logger.info("Connecting to MongoDB Atlas...")
            _client = MongoClient(
                Config.MONGO_URI,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=5000,
            )
            # Verify connection
            _client.admin.command("ping")
            logger.info("✅ Successfully connected to MongoDB Atlas")
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.error(f"❌ Failed to connect to MongoDB Atlas: {e}")
            raise
    return _client


def get_db():
    """Get the quiz database instance."""
    global _db
    if _db is None:
        client = get_client()
        _db = client[Config.DB_NAME]
        logger.info(f"Using database: {Config.DB_NAME}")
    return _db


def init_db():
    """
    Initialize database collections and create indexes.
    Called once at application startup.
    """
    db = get_db()

    # Participants: non-unique phone number index
    try:
        db.participants.drop_index("unique_phone")
        logger.info("Dropped unique_phone index to allow same phone numbers")
    except Exception:
        pass

    db.participants.create_index(
        [("phone", ASCENDING)],
        name="phone_asc"
    )

    # Responses: compound index for quick lookups
    db.responses.create_index(
        [("participant_id", ASCENDING), ("question_id", ASCENDING)],
        unique=True,
        name="unique_response_per_question"
    )

    # Participants: score index for leaderboard queries
    db.participants.create_index(
        [("score", DESCENDING)],
        name="score_desc"
    )

    # Initialize quiz_state document if it doesn't exist
    existing_state = db.quiz_state.find_one({"_id": "quiz_state"})
    if not existing_state:
        db.quiz_state.insert_one({
            "_id": "quiz_state",
            "status": "waiting",
            "current_question_index": 0,
            "allow_join": True
        })
        logger.info("✅ Initialized quiz_state document")
    else:
        logger.info("ℹ️ quiz_state document already exists")

    logger.info("✅ Database indexes created successfully")


def close_db():
    """Close the MongoDB connection gracefully."""
    global _client, _db
    if _client:
        _client.close()
        _client = None
        _db = None
        logger.info("MongoDB connection closed")
