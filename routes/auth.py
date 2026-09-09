import os
import random
import hashlib
import sqlite3
import smtplib

from email.message import EmailMessage

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash
)

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)


# ============================================================
# AUTH BLUEPRINT
# ============================================================

auth_bp = Blueprint(
    "auth",
    __name__
)


# ============================================================
# DATABASE
# ============================================================

DATABASE = "votelock.db"


def get_connection():

    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row

    return conn


# ============================================================
# SEND OTP EMAIL
# ============================================================

def send_otp_email(receiver_email, otp):

    sender_email = os.getenv("MAIL_USERNAME")
    sender_password = os.getenv("MAIL_PASSWORD")

    if not sender_email or not sender_password:

        print("ERROR: Email credentials are not configured.")
        print("OTP for testing:", otp)

        return False

    message = EmailMessage()

    message["Subject"] = "VoteLock Admin Registration OTP"
    message["From"] = sender_email
    message["To"] = receiver_email

    message.set_content(
        f"""
Hello,

Your VoteLock administrator registration OTP is:

{otp}

This OTP is valid for 10 minutes.

If you did not request this registration, please ignore this email.

Regards,
VoteLock Smart Electronic Voting System
"""
    )

    try:

        with smtplib.SMTP(
            "smtp.gmail.com",
            587
        ) as server:

            server.starttls()

            server.login(
                sender_email,
                sender_password
            )

            server.send_message(message)

        return True

    except Exception as e:

        print("EMAIL ERROR:", e)

        return False


# ============================================================
# LOGIN
# ============================================================

@auth_bp.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )

        if not email or not password:

            flash(
                "Please enter email and password.",
                "error"
            )

            return redirect(
                url_for("auth.login")
            )

        conn = get_connection()

        admin = conn.execute(
            """
            SELECT *
            FROM admins
            WHERE email = ?
            """,
            (email,)
        ).fetchone()

        conn.close()

        if admin is None:

            flash(
                "No administrator account found.",
                "error"
            )

            return redirect(
                url_for("auth.login")
            )

        if admin["is_verified"] != 1:

            flash(
                "Please verify your email before logging in.",
                "error"
            )

            return redirect(
                url_for("auth.login")
            )

        if not check_password_hash(
            admin["password_hash"],
            password
        ):

            flash(
                "Invalid email or password.",
                "error"
            )

            return redirect(
                url_for("auth.login")
            )

        # ----------------------------------------------------
        # LOGIN SUCCESS
        # ----------------------------------------------------

        session.clear()

        session["admin_id"] = admin["id"]
        session["admin_name"] = admin["name"]
        session["admin_email"] = admin["email"]

        return redirect(
            url_for("admin.dashboard")
        )

    return render_template(
        "login.html"
    )


# ============================================================
# REGISTER
# ============================================================

@auth_bp.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )

        confirm_password = request.form.get(
            "confirm_password",
            ""
        )

        # ----------------------------------------------------
        # VALIDATION
        # ----------------------------------------------------

        if not name or not email or not password:

            flash(
                "All fields are required.",
                "error"
            )

            return redirect(
                url_for("auth.register")
            )

        if password != confirm_password:

            flash(
                "Passwords do not match.",
                "error"
            )

            return redirect(
                url_for("auth.register")
            )

        if len(password) < 6:

            flash(
                "Password must contain at least 6 characters.",
                "error"
            )

            return redirect(
                url_for("auth.register")
            )

        # ----------------------------------------------------
        # CHECK EXISTING ADMIN
        # ----------------------------------------------------

        conn = get_connection()

        existing_admin = conn.execute(
            """
            SELECT id
            FROM admins
            WHERE email = ?
            """,
            (email,)
        ).fetchone()

        conn.close()

        if existing_admin:

            flash(
                "An administrator with this email already exists.",
                "error"
            )

            return redirect(
                url_for("auth.login")
            )

        # ----------------------------------------------------
        # GENERATE OTP
        # ----------------------------------------------------

        otp = str(
            random.randint(
                100000,
                999999
            )
        )

        otp_hash = hashlib.sha256(
            otp.encode()
        ).hexdigest()

        # ----------------------------------------------------
        # STORE TEMPORARY REGISTRATION DATA
        # ----------------------------------------------------

        session["registration_name"] = name
        session["registration_email"] = email
        session["registration_password"] = generate_password_hash(
            password
        )
        session["registration_otp"] = otp_hash

        # OTP valid for 10 minutes
        import time

        session["otp_expiry"] = time.time() + 600

        # ----------------------------------------------------
        # SEND EMAIL
        # ----------------------------------------------------

        sent = send_otp_email(
            email,
            otp
        )

        if not sent:

            # Remove temporary registration information
            session.pop("registration_name", None)
            session.pop("registration_email", None)
            session.pop("registration_password", None)
            session.pop("registration_otp", None)
            session.pop("otp_expiry", None)

            flash(
                "Unable to send OTP email. Check your email configuration.",
                "error"
            )

            return redirect(
                url_for("auth.register")
            )

        flash(
            "OTP sent to your email address.",
            "success"
        )

        return redirect(
            url_for("auth.verify_otp")
        )

    return render_template(
        "register.html"
    )


# ============================================================
# VERIFY OTP
# ============================================================

@auth_bp.route(
    "/verify-otp",
    methods=["GET", "POST"]
)
def verify_otp():

    if "registration_email" not in session:

        flash(
            "Please register first.",
            "error"
        )

        return redirect(
            url_for("auth.register")
        )

    if request.method == "POST":

        entered_otp = request.form.get(
            "otp",
            ""
        ).strip()

        if not entered_otp:

            flash(
                "Please enter the OTP.",
                "error"
            )

            return redirect(
                url_for("auth.verify_otp")
            )

        # ----------------------------------------------------
        # CHECK OTP EXPIRY
        # ----------------------------------------------------

        import time

        expiry = session.get(
            "otp_expiry",
            0
        )

        if time.time() > expiry:

            flash(
                "OTP has expired. Please register again.",
                "error"
            )

            return redirect(
                url_for("auth.register")
            )

        # ----------------------------------------------------
        # HASH ENTERED OTP
        # ----------------------------------------------------

        entered_hash = hashlib.sha256(
            entered_otp.encode()
        ).hexdigest()

        stored_hash = session.get(
            "registration_otp"
        )

        if entered_hash != stored_hash:

            flash(
                "Invalid OTP. Please try again.",
                "error"
            )

            return redirect(
                url_for("auth.verify_otp")
            )

        # ----------------------------------------------------
        # CREATE ADMIN ACCOUNT
        # ----------------------------------------------------

        name = session.get(
            "registration_name"
        )

        email = session.get(
            "registration_email"
        )

        password_hash = session.get(
            "registration_password"
        )

        conn = get_connection()

        try:

            conn.execute(
                """
                INSERT INTO admins
                (
                    name,
                    email,
                    password_hash,
                    is_verified
                )
                VALUES (?, ?, ?, 1)
                """,
                (
                    name,
                    email,
                    password_hash
                )
            )

            conn.commit()

        except sqlite3.IntegrityError:

            conn.close()

            flash(
                "An administrator with this email already exists.",
                "error"
            )

            return redirect(
                url_for("auth.login")
            )

        conn.close()

        # ----------------------------------------------------
        # CLEAR REGISTRATION SESSION
        # ----------------------------------------------------

        session.pop(
            "registration_name",
            None
        )

        session.pop(
            "registration_email",
            None
        )

        session.pop(
            "registration_password",
            None
        )

        session.pop(
            "registration_otp",
            None
        )

        session.pop(
            "otp_expiry",
            None
        )

        flash(
            "Registration successful. You can now log in.",
            "success"
        )

        return redirect(
            url_for("auth.login")
        )

    return render_template(
        "verify_otp.html"
    )


# ============================================================
# LOGOUT
# ============================================================

@auth_bp.route("/logout")
def logout():

    session.clear()

    flash(
        "You have been logged out.",
        "success"
    )

    return redirect(
        url_for("auth.login")
    )