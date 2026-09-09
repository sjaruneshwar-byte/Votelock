from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    session
)

from database import (
    get_dashboard_stats,
    get_recent_logs
)


# ============================================================
# ADMIN BLUEPRINT
# ============================================================

admin_bp = Blueprint(
    "admin",
    __name__,
    url_prefix="/admin"
)


# ============================================================
# ADMIN AUTHENTICATION CHECK
# ============================================================

def admin_required():

    return "admin_id" in session


# ============================================================
# ADMIN HOME
# ============================================================

@admin_bp.route("/")
def home():

    if not admin_required():

        return redirect(
            url_for("auth.login")
        )

    return redirect(
        url_for("admin.dashboard")
    )


# ============================================================
# ADMIN DASHBOARD
# ============================================================

@admin_bp.route("/dashboard")
def dashboard():

    if not admin_required():

        return redirect(
            url_for("auth.login")
        )

    stats = get_dashboard_stats()

    logs = get_recent_logs(10)

    return render_template(
        "dashboard.html",
        stats=stats,
        logs=logs,
        admin_name=session.get(
            "admin_name",
            "Administrator"
        )
    )