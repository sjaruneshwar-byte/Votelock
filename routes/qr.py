from flask import Blueprint, render_template, request, jsonify

from database import get_db, add_audit_log


qr_bp = Blueprint(
    "qr",
    __name__,
    url_prefix="/qr"
)


# ============================================================
# QR SCANNER PAGE
# ============================================================

@qr_bp.route("/scanner")
def scanner():

    return render_template(
        "voter_qr_scanner.html"
    )


# ============================================================
# VERIFY QR TOKEN
# ============================================================

@qr_bp.route("/verify", methods=["POST"])
def verify_qr():

    data = request.get_json()

    if not data:
        return jsonify({
            "success": False,
            "message": "No QR data received."
        }), 400

    qr_token = data.get("qr_token", "").strip()

    if not qr_token:
        return jsonify({
            "success": False,
            "message": "QR token is empty."
        }), 400

    conn = get_db()

    try:

        voter = conn.execute(
            """
            SELECT
                voter_id,
                name,
                email,
                department,
                has_voted
            FROM voters
            WHERE qr_token = ?
            """,
            (qr_token,)
        ).fetchone()

    finally:

        conn.close()

    # --------------------------------------------------------
    # INVALID QR
    # --------------------------------------------------------

    if voter is None:

        return jsonify({
            "success": False,
            "message": "Invalid QR code. Voter not found."
        }), 404

    # --------------------------------------------------------
    # SUCCESSFUL QR VERIFICATION
    # --------------------------------------------------------

    add_audit_log(
        "QR_VERIFIED",
        f"QR code verified successfully for voter {voter['voter_id']}.",
        voter["voter_id"]
    )

    # --------------------------------------------------------
    # RETURN VOTER DETAILS
    # --------------------------------------------------------

    return jsonify({
        "success": True,
        "message": "Voter verified successfully.",
        "voter": {
            "voter_id": voter["voter_id"],
            "name": voter["name"],
            "email": voter["email"],
            "department": voter["department"],
            "has_voted": voter["has_voted"]
        }
    })