import sqlite3
from contextlib import contextmanager

DATABASE = "votelock.db"


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def db_connection():
    conn = get_db()

    try:
        yield conn
        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def init_db():

    conn = get_db()
    cursor = conn.cursor()

    # ==================================================
    # ADMINS
    # ==================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            is_verified INTEGER DEFAULT 0,
            otp_hash TEXT,
            otp_expiry TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ==================================================
    # CANDIDATES
    # ==================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS candidates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            symbol TEXT,
            description TEXT,
            status TEXT DEFAULT 'Active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ==================================================
    # VOTERS
    # ==================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS voters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            voter_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            email TEXT,
            department TEXT,
            username TEXT UNIQUE,
            password_hash TEXT,
            qr_token TEXT UNIQUE,
            has_voted INTEGER DEFAULT 0,
            image_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ==================================================
    # VOTES
    # ==================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS votes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (candidate_id)
            REFERENCES candidates(id)
        )
    """)

    # ==================================================
    # AUDIT LOGS
    # ==================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,
            voter_id TEXT,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ==================================================
    # INDEXES
    # ==================================================

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_voters_voter_id
        ON voters(voter_id)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_voters_qr_token
        ON voters(qr_token)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_votes_candidate
        ON votes(candidate_id)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_audit_logs_created
        ON audit_logs(created_at)
    """)

    conn.commit()
    conn.close()


# ======================================================
# DASHBOARD STATISTICS
# ======================================================

def get_dashboard_stats():

    conn = get_db()

    total_voters = conn.execute(
        "SELECT COUNT(*) FROM voters"
    ).fetchone()[0]

    total_candidates = conn.execute(
        "SELECT COUNT(*) FROM candidates"
    ).fetchone()[0]

    total_votes = conn.execute(
        "SELECT COUNT(*) FROM votes"
    ).fetchone()[0]

    pending_voters = conn.execute(
        """
        SELECT COUNT(*)
        FROM voters
        WHERE has_voted = 0
        """
    ).fetchone()[0]

    voted_voters = conn.execute(
        """
        SELECT COUNT(*)
        FROM voters
        WHERE has_voted = 1
        """
    ).fetchone()[0]

    turnout = 0

    if total_voters > 0:
        turnout = round(
            (voted_voters / total_voters) * 100,
            1
        )

    conn.close()

    return {
        "voters": total_voters,
        "candidates": total_candidates,
        "votes": total_votes,
        "pending_voters": pending_voters,
        "voted_voters": voted_voters,
        "turnout": turnout
    }


# ======================================================
# AUDIT LOG
# ======================================================

def add_audit_log(
    event_type,
    description,
    voter_id=None
):

    conn = get_db()

    conn.execute(
        """
        INSERT INTO audit_logs
        (
            event_type,
            voter_id,
            description
        )
        VALUES (?, ?, ?)
        """,
        (
            event_type,
            voter_id,
            description
        )
    )

    conn.commit()
    conn.close()


def get_recent_logs(limit=10):

    conn = get_db()

    logs = conn.execute(
        """
        SELECT *
        FROM audit_logs
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (limit,)
    ).fetchall()

    conn.close()

    return logs


# ======================================================
# VOTERS
# ======================================================

def get_all_voters():

    conn = get_db()

    voters = conn.execute(
        """
        SELECT *
        FROM voters
        ORDER BY created_at DESC
        """
    ).fetchall()

    conn.close()

    return voters


def get_voter(voter_id):

    conn = get_db()

    voter = conn.execute(
        """
        SELECT *
        FROM voters
        WHERE voter_id = ?
        """,
        (voter_id,)
    ).fetchone()

    conn.close()

    return voter


def delete_voter(voter_id):

    conn = get_db()

    voter = conn.execute(
        """
        SELECT has_voted
        FROM voters
        WHERE voter_id = ?
        """,
        (voter_id,)
    ).fetchone()

    if voter is None:
        conn.close()
        return False, "Voter not found."

    if voter["has_voted"] == 1:
        conn.close()
        return False, "This voter has already voted and cannot be deleted."

    conn.execute(
        """
        DELETE FROM voters
        WHERE voter_id = ?
        """,
        (voter_id,)
    )

    conn.commit()
    conn.close()

    return True, "Voter deleted successfully."


# ======================================================
# CANDIDATES
# ======================================================

def get_all_candidates():

    conn = get_db()

    candidates = conn.execute(
        """
        SELECT *
        FROM candidates
        ORDER BY created_at DESC
        """
    ).fetchall()

    conn.close()

    return candidates


def get_candidate(candidate_id):

    conn = get_db()

    candidate = conn.execute(
        """
        SELECT *
        FROM candidates
        WHERE candidate_id = ?
        """,
        (candidate_id,)
    ).fetchone()

    conn.close()

    return candidate


def delete_candidate(candidate_id):

    conn = get_db()

    candidate = conn.execute(
        """
        SELECT id
        FROM candidates
        WHERE candidate_id = ?
        """,
        (candidate_id,)
    ).fetchone()

    if candidate is None:
        conn.close()
        return False, "Candidate not found."

    vote_count = conn.execute(
        """
        SELECT COUNT(*)
        FROM votes
        WHERE candidate_id = ?
        """,
        (candidate["id"],)
    ).fetchone()[0]

    if vote_count > 0:
        conn.close()

        return (
            False,
            "This candidate already has votes and cannot be deleted."
        )

    conn.execute(
        """
        DELETE FROM candidates
        WHERE candidate_id = ?
        """,
        (candidate_id,)
    )

    conn.commit()
    conn.close()

    return True, "Candidate deleted successfully."


# ======================================================
# VOTER VOTING STATUS
# ======================================================

def voter_has_voted(voter_id):

    conn = get_db()

    result = conn.execute(
        """
        SELECT has_voted
        FROM voters
        WHERE voter_id = ?
        """,
        (voter_id,)
    ).fetchone()

    conn.close()

    if result is None:
        return False

    return result["has_voted"] == 1


def mark_voter_as_voted(voter_id):

    conn = get_db()

    conn.execute(
        """
        UPDATE voters
        SET has_voted = 1
        WHERE voter_id = ?
        """,
        (voter_id,)
    )

    conn.commit()
    conn.close()


if __name__ == "__main__":

    init_db()

    print(
        "VoteLock database initialized successfully."
    )