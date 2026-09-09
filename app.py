from flask import Flask, redirect, url_for
from dotenv import load_dotenv
import os

from database import init_db

load_dotenv()

app = Flask(__name__)

app.secret_key = os.getenv(
    "SECRET_KEY",
    "votelock-secret-key-2026"
)

init_db()

from routes.auth import auth_bp
from routes.admin import admin_bp
from routes.voters import voters_bp
from routes.candidates import candidates_bp


app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(voters_bp)
app.register_blueprint(candidates_bp)


@app.route("/")
def index():

    return redirect(
        url_for("auth.login")
    )


@app.route("/health")
def health():

    return {
        "status": "ok",
        "application": "VoteLock"
    }


if __name__ == "__main__":

    print("=" * 55)
    print("VoteLock Smart Electronic Voting System")
    print("=" * 55)
    print("Login    : http://127.0.0.1:5000/login")
    print("Register : http://127.0.0.1:5000/register")
    print("Dashboard: http://127.0.0.1:5000/admin/dashboard")
    print("=" * 55)

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )