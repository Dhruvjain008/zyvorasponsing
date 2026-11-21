import os
from dotenv import load_dotenv
from flask import Flask, flash, redirect, request, session, url_for
from db import close_db, get_db, init_db
from helpers import current_user
from auth.routes import auth_bp
from feed.routes import feed_bp
from projects.routes import projects_bp
from interests.routes import interests_bp
from deals import deals_bp
import deals
from servers.routes import servers_bp
from dms.routes import dms_bp
from reports.routes import reports_bp
from profiles.routes import profiles_bp
from settings.routes import settings_bp
from extensions import socketio
from servers.botapi import api_bp
import unread
import presence
import calls
import mutes

load_dotenv()

app = Flask(__name__)

# SECRET_KEY must be set in environment variables in production (Render dashboard)
_secret = os.getenv("SECRET_KEY")
if not _secret:
    import warnings
    warnings.warn("SECRET_KEY is not set! Using insecure fallback. Set it in Render environment variables.")
app.config["SECRET_KEY"] = _secret or "dev-only-secret-key-change-me"

app.config["MAX_CONTENT_LENGTH"] = 500 * 1024 * 1024  # all files of one post together
app.teardown_appcontext(close_db)
app.register_blueprint(auth_bp)
app.register_blueprint(feed_bp)
app.register_blueprint(projects_bp)
app.register_blueprint(interests_bp)
app.register_blueprint(deals_bp)
app.jinja_env.globals["terms_text"] = deals.describe
app.register_blueprint(servers_bp)
app.register_blueprint(dms_bp)
app.register_blueprint(reports_bp)
app.register_blueprint(profiles_bp)
app.register_blueprint(settings_bp)
app.register_blueprint(api_bp)
from servers.projectlink import proj_bp
app.register_blueprint(proj_bp)
from live import live_bp
app.register_blueprint(live_bp)
from callsvc import calls_bp
app.register_blueprint(calls_bp)

# Use eventlet for async_mode so WebSockets and background tasks work on Render
socketio.init_app(app, async_mode="eventlet", cors_allowed_origins="*")

import servers.chat  # registers the server chat events
import dms.chat  # registers the DM events
import live  # registers the per-user real-time rooms
import callsvc  # registers the call signalling events

from servers import projectlink
app.jinja_env.globals["project_server"] = projectlink.server_of
app.jinja_env.globals["project_chip"] = projectlink.chip
app.jinja_env.globals["presence"] = presence.status_of
app.jinja_env.globals["call_count"] = calls.count
app.jinja_env.globals["muted"] = lambda kind, target: mutes.is_muted(session.get("user_id"), kind, target)


@app.before_request
def start_companion_worker():
    from servers import companions
    companions.ensure_worker(app)    # reminders and event start-times (starts once, in the serving process)


@app.context_processor
def inject_user():
    user = current_user()
    badges = unread.all_counts(user["id"]) if user else None
    # Note: giphy_key is intentionally passed only to templates that need it.
    # Avoid exposing API keys in HTML source for public pages.
    return {"user": user, "badges": badges, "giphy_key": os.getenv("GIPHY_API_KEY", "")}


@app.errorhandler(413)
def too_large(error):
    flash("Those files are too big. Keep a post under 500 MB in total (100 MB per video).")
    return redirect(request.referrer or url_for("feed.index"))


# --- Init DB on startup (runs every time gunicorn/eventlet starts the app) ---
init_db()

if __name__ == "__main__":
    socketio.run(app, host=os.getenv("HOST", "0.0.0.0"), port=int(os.getenv("PORT", "5000")), debug=False)
