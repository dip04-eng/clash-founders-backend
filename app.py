"""
app.py
------
Main application entry point for the Real-Time Quiz Platform.

Initializes Flask, Socket.IO, MongoDB, CORS, and registers
all routes and event handlers.

Usage:
    python app.py

The server runs on http://0.0.0.0:5000 by default.
Uses Eventlet for WebSocket support.
"""

# Monkey-patch MUST happen first before any other imports
import eventlet
eventlet.monkey_patch()

import logging
import sys
from flask import Flask
from flask_socketio import SocketIO
from flask_cors import CORS

from config import Config
from database.mongodb import init_db
from routes.participant_routes import participant_bp
from routes.admin_routes import admin_bp
from socketio_events.quiz_events import register_socketio_events
from seed_data import seed_questions

# ── Logging Configuration ──────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)
logger = logging.getLogger(__name__)

# ── Application Factory ─────────────────────────────────────────


def create_app():
    """Create and configure the Flask application."""

    app = Flask(__name__)
    app.config["SECRET_KEY"] = Config.SECRET_KEY

    # ── CORS ─────────────────────────────────────────────────
    # Allow all origins for development; restrict in production
    CORS(app, resources={
        r"/*": {"origins": Config.CORS_ORIGINS}
    })

    # ── Socket.IO ────────────────────────────────────────────
    socketio = SocketIO(
        app,
        cors_allowed_origins="*",
        async_mode="eventlet",
        logger=False,
        engineio_logger=False,
        ping_timeout=60,
        ping_interval=25,
    )

    # ── Register Blueprints (REST API routes) ────────────────
    app.register_blueprint(participant_bp)
    app.register_blueprint(admin_bp)

    # ── Register Socket.IO Events ────────────────────────────
    register_socketio_events(socketio)

    # ── Health Check Route ───────────────────────────────────
    @app.route("/health", methods=["GET"])
    def health_check():
        """Simple health check endpoint."""
        return {"status": "ok", "message": "Quiz server is running"}, 200

    @app.route("/", methods=["GET"])
    def index():
        """Root endpoint with API info."""
        return {
            "app": "Real-Time Quiz Platform",
            "version": "1.0.0",
            "status": "running",
            "endpoints": {
                "health": "/health",
                "join": "POST /api/participant/join",
                "leaderboard": "GET /api/leaderboard",
                "quiz_state": "GET /api/quiz-state",
                "participants": "GET /api/participants",
                "admin_start": "POST /api/admin/start",
                "admin_next": "POST /api/admin/next-question",
                "admin_end": "POST /api/admin/end",
                "admin_reset": "POST /api/admin/reset",
                "admin_status": "GET /api/admin/status",
            }
        }, 200

    return app, socketio


# ── Main Entry Point ─────────────────────────────────────────────

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  Real-Time Quiz Platform - Backend Server")
    print("=" * 60 + "\n")

    # Create the application
    app, socketio = create_app()

    # Initialize database and seed data
    try:
        logger.info("Initializing database...")
        init_db()
        # logger.info("Seeding questions...")
        # seed_questions()
        logger.info("[OK] Database ready!")
    except Exception as e:
        logger.error(f"[ERROR] Database initialization failed: {e}")
        logger.error("Please check your MONGO_URI in the .env file")
        sys.exit(1)

    # Start the server
    logger.info(f"Starting server on {Config.HOST}:{Config.PORT}")
    logger.info(f"WebSocket support: Eventlet")
    logger.info(f"CORS origins: {Config.CORS_ORIGINS}")
    print(f"\n  Server running at http://localhost:{Config.PORT}\n")

    socketio.run(
        app,
        host=Config.HOST,
        port=Config.PORT,
        debug=Config.DEBUG,
        use_reloader=False,  # Disable reloader with eventlet
    )
