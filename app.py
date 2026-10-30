"""
app.py
Main Flask Application for Online Voting System.
Handles routes for authentication, voter ballot casting, results display,
and admin candidate/poll management.
"""

from functools import wraps
from datetime import datetime
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    g
)
import os
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_db, DB_PATH, init_db

app = Flask(__name__)
# Secret key used to encrypt session cookies (configurable via SECRET_KEY environment variable)
app.secret_key = os.environ.get("SECRET_KEY", "classroom-demo-secret-key-change-in-production")

# Ensure SQLite database exists automatically upon startup (e.g. under WSGI/Gunicorn on cloud)
if not os.path.exists(DB_PATH):
    init_db(seed_data=True)


# ---------------------------------------------------------------------------
# Database connection lifecycle per request
# ---------------------------------------------------------------------------
@app.before_request
def before_request():
    """Opens a database connection before handling each incoming request."""
    g.db = get_db()


@app.teardown_appcontext
def close_db_connection(exception=None):
    """Closes the database connection when the request finishes."""
    db = g.pop('db', None)
    if db is not None:
        db.close()


# ---------------------------------------------------------------------------
# Authentication Decorators
# ---------------------------------------------------------------------------
def login_required(f):
    """Restricts access to authenticated users only."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Please sign in first to access this page.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function


def student_required(f):
    """Restricts access to student voters only. Administrators are redirected to their dashboard."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Please sign in with your Student ID first.", "warning")
            return redirect(url_for("login"))
        if session.get("role") == "admin":
            flash("Administrators manage elections via the Admin Dashboard. Cast ballots with a Student account.", "info")
            return redirect(url_for("admin_dashboard"))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """Restricts access to users with the 'admin' role."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Please sign in as an administrator to access the Admin Portal.", "warning")
            return redirect(url_for("admin_login"))
        if session.get("role") != "admin":
            flash("Access denied. Administrator privileges required.", "danger")
            return redirect(url_for("vote_index"))
        return f(*args, **kwargs)
    return decorated_function


# ---------------------------------------------------------------------------
# Home & Authentication Routes
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    """Redirects home page: admin to dashboard, voter to voting, or login."""
    if "user_id" in session:
        if session.get("role") == "admin":
            return redirect(url_for("admin_dashboard"))
        return redirect(url_for("vote_index"))
    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    """
    Voter registration:
    Collects Name, Student ID, and Password, hashes the password,
    and stores the new voter in the 'users' table.
    """
    if "user_id" in session:
        return redirect(url_for("vote_index"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        student_id = request.form.get("student_id", "").strip().upper()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        # Form validations
        if not name or not student_id or not password:
            flash("All fields are required.", "danger")
            return render_template("register.html", name=name, student_id=student_id)

        if len(password) < 6:
            flash("Password must be at least 6 characters long.", "danger")
            return render_template("register.html", name=name, student_id=student_id)

        if password != confirm_password:
            flash("Passwords do not match. Please try again.", "danger")
            return render_template("register.html", name=name, student_id=student_id)

        # Check if student ID already registered
        existing_user = g.db.execute(
            "SELECT id FROM users WHERE student_id = ?", (student_id,)
        ).fetchone()

        if existing_user:
            flash("A voter with this Student ID is already registered. Please sign in.", "warning")
            return redirect(url_for("login"))

        # Hash password and insert voter
        pw_hash = generate_password_hash(password)
        try:
            g.db.execute(
                "INSERT INTO users (name, student_id, password_hash, role) VALUES (?, ?, ?, 'voter')",
                (name, student_id, pw_hash)
            )
            g.db.commit()
            flash("Registration successful! You can now sign in and vote.", "success")
            return redirect(url_for("login"))
        except Exception as e:
            flash(f"An error occurred while creating your account: {str(e)}", "danger")

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
@app.route("/student/login", methods=["GET", "POST"])
def login():
    """
    Student Voter Sign In:
    Validates Student ID and Password. If an admin logs in here,
    they are automatically routed to the Admin Dashboard.
    """
    if "user_id" in session:
        if session.get("role") == "admin":
            return redirect(url_for("admin_dashboard"))
        return redirect(url_for("vote_index"))

    if request.method == "POST":
        student_id = request.form.get("student_id", "").strip().upper()
        password = request.form.get("password", "")

        if not student_id or not password:
            flash("Please enter both Student ID and Password.", "danger")
            return render_template("login.html", student_id=student_id)

        # Look up user in SQLite
        user = g.db.execute(
            "SELECT * FROM users WHERE student_id = ?", (student_id,)
        ).fetchone()

        # Check hash
        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            session["name"] = user["name"]
            session["student_id"] = user["student_id"]
            session["role"] = user["role"]

            flash(f"Welcome, {user['name']}! You have signed in successfully.", "success")
            if user["role"] == "admin":
                return redirect(url_for("admin_dashboard"))
            return redirect(url_for("vote_index"))
        else:
            flash("Invalid Student ID or Password. Please try again.", "danger")

    return render_template("login.html")


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    """
    Dedicated Administrator Sign In:
    Provides a separate, secure login portal exclusively for administrators.
    """
    if "user_id" in session:
        if session.get("role") == "admin":
            return redirect(url_for("admin_dashboard"))
        return redirect(url_for("vote_index"))

    if request.method == "POST":
        student_id = request.form.get("student_id", "").strip().upper()
        password = request.form.get("password", "")

        if not student_id or not password:
            flash("Please enter both Administrator ID and Password.", "danger")
            return render_template("admin_login.html", student_id=student_id)

        user = g.db.execute(
            "SELECT * FROM users WHERE student_id = ?", (student_id,)
        ).fetchone()

        if user and check_password_hash(user["password_hash"], password):
            if user["role"] != "admin":
                flash("This is a Student account. Please sign in via the Student Portal.", "warning")
                return redirect(url_for("login"))

            session["user_id"] = user["id"]
            session["name"] = user["name"]
            session["student_id"] = user["student_id"]
            session["role"] = user["role"]

            flash(f"Welcome, Administrator {user['name']}! Accessing Admin Dashboard.", "success")
            return redirect(url_for("admin_dashboard"))
        else:
            flash("Invalid Administrator credentials. Please try again.", "danger")

    return render_template("admin_login.html")


@app.route("/logout")
def logout():
    """Clears the session cookie and logs the user out."""
    role = session.get("role")
    session.clear()
    flash("You have been successfully logged out.", "info")
    if role == "admin":
        return redirect(url_for("admin_login"))
    return redirect(url_for("login"))


# ---------------------------------------------------------------------------
# Student Voter Routes (Poll Listing & Ballot Casting)
# ---------------------------------------------------------------------------
@app.route("/student")
@app.route("/student/portal")
@app.route("/vote")
@student_required
def vote_index():
    """
    Displays list of all polls (active & closed), showing whether the current
    voter has already cast a ballot in each poll.
    """
    user_id = session["user_id"]

    # Fetch all polls
    polls = g.db.execute(
        "SELECT * FROM polls ORDER BY id DESC"
    ).fetchall()

    # Find which polls the voter has already voted in
    voted_poll_rows = g.db.execute(
        "SELECT poll_id, candidate_id FROM votes WHERE voter_id = ?", (user_id,)
    ).fetchall()
    voted_polls_map = {row["poll_id"]: row["candidate_id"] for row in voted_poll_rows}

    # Fetch candidates count for each poll
    candidates_count = {}
    for poll in polls:
        cnt = g.db.execute(
            "SELECT COUNT(*) as cnt FROM candidates WHERE poll_id = ?", (poll["id"],)
        ).fetchone()
        candidates_count[poll["id"]] = cnt["cnt"]

    return render_template(
        "vote.html",
        polls=polls,
        voted_polls_map=voted_polls_map,
        candidates_count=candidates_count,
        selected_poll=None
    )


@app.route("/student/vote/<int:poll_id>", methods=["GET", "POST"])
@app.route("/vote/<int:poll_id>", methods=["GET", "POST"])
@student_required
def cast_vote(poll_id):
    """
    Displays the ballot for a specific poll with candidates, and handles POST
    submission to record the vote with one-vote-per-voter enforcement.
    """
    user_id = session["user_id"]

    # Retrieve poll details
    poll = g.db.execute("SELECT * FROM polls WHERE id = ?", (poll_id,)).fetchone()
    if not poll:
        flash("The requested poll does not exist.", "danger")
        return redirect(url_for("vote_index"))

    # Fetch candidates for this poll
    candidates = g.db.execute(
        "SELECT * FROM candidates WHERE poll_id = ? ORDER BY id ASC", (poll_id,)
    ).fetchall()

    # Check if the user has ALREADY voted in this poll
    existing_vote = g.db.execute(
        "SELECT * FROM votes WHERE voter_id = ? AND poll_id = ?",
        (user_id, poll_id)
    ).fetchone()

    # Handle Ballot Submission
    if request.method == "POST":
        # 1. Check if poll is active
        if poll["status"] != "active":
            flash("This poll is closed and no longer accepting votes.", "danger")
            return redirect(url_for("view_results", poll_id=poll_id))

        # 2. Check duplicate voting
        if existing_vote:
            flash("You have ALREADY voted in this poll. Each voter is allowed only one vote.", "warning")
            return redirect(url_for("view_results", poll_id=poll_id))

        candidate_id = request.form.get("candidate_id")
        if not candidate_id:
            flash("Please choose a candidate before submitting your vote.", "danger")
            return render_template(
                "vote.html",
                selected_poll=poll,
                candidates=candidates,
                has_voted=False
            )

        # 3. Verify candidate belongs to this poll
        valid_candidate = g.db.execute(
            "SELECT id, name FROM candidates WHERE id = ? AND poll_id = ?",
            (candidate_id, poll_id)
        ).fetchone()

        if not valid_candidate:
            flash("Invalid candidate selected.", "danger")
            return redirect(url_for("cast_vote", poll_id=poll_id))

        # 4. Record vote in the database
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            g.db.execute(
                "INSERT INTO votes (voter_id, candidate_id, poll_id, timestamp) VALUES (?, ?, ?, ?)",
                (user_id, candidate_id, poll_id, now_str)
            )
            g.db.commit()
            flash(f"Success! Your vote for '{valid_candidate['name']}' has been officially recorded.", "success")
            return redirect(url_for("view_results", poll_id=poll_id))
        except Exception as e:
            # Catch potential unique constraint violation
            flash("Voting error: You may have already cast a vote in this poll.", "danger")
            return redirect(url_for("view_results", poll_id=poll_id))

    # GET request: render ballot
    return render_template(
        "vote.html",
        selected_poll=poll,
        candidates=candidates,
        has_voted=bool(existing_vote),
        existing_vote=existing_vote
    )


# ---------------------------------------------------------------------------
# Results Route
# ---------------------------------------------------------------------------
@app.route("/results")
@app.route("/results/<int:poll_id>")
def view_results(poll_id=None):
    """
    Displays vote tallies and percentage progress bars for a selected poll.
    Accessible to all users to promote transparency.
    """
    polls = g.db.execute("SELECT * FROM polls ORDER BY id DESC").fetchall()
    if not polls:
        flash("No polls have been created yet.", "info")
        return render_template("results.html", polls=[], selected_poll=None, results=[])

    # If no poll_id provided in URL, default to the first active poll or first poll
    if poll_id is None:
        selected_poll = next((p for p in polls if p["status"] == "active"), polls[0])
        poll_id = selected_poll["id"]
    else:
        selected_poll = g.db.execute("SELECT * FROM polls WHERE id = ?", (poll_id,)).fetchone()
        if not selected_poll:
            flash("Poll not found.", "warning")
            return redirect(url_for("view_results"))

    # Compute total votes cast for this poll
    total_votes_row = g.db.execute(
        "SELECT COUNT(*) AS total FROM votes WHERE poll_id = ?", (poll_id,)
    ).fetchone()
    total_votes = total_votes_row["total"] if total_votes_row else 0

    # Query candidates and their respective vote counts using LEFT JOIN
    query = """
        SELECT
            c.id,
            c.name,
            c.description,
            COUNT(v.id) AS vote_count
        FROM candidates c
        LEFT JOIN votes v ON c.id = v.candidate_id AND v.poll_id = c.poll_id
        WHERE c.poll_id = ?
        GROUP BY c.id
        ORDER BY vote_count DESC, c.name ASC
    """
    candidate_rows = g.db.execute(query, (poll_id,)).fetchall()

    # Calculate percentages and identify winner/leader
    results = []
    max_votes = 0
    if candidate_rows:
        max_votes = candidate_rows[0]["vote_count"]

    for row in candidate_rows:
        count = row["vote_count"]
        percentage = round((count / total_votes * 100), 1) if total_votes > 0 else 0
        is_leader = (count == max_votes and count > 0)
        results.append({
            "id": row["id"],
            "name": row["name"],
            "description": row["description"],
            "vote_count": count,
            "percentage": percentage,
            "is_leader": is_leader
        })

    return render_template(
        "results.html",
        polls=polls,
        selected_poll=selected_poll,
        results=results,
        total_votes=total_votes
    )


# ---------------------------------------------------------------------------
# Admin Dashboard & Management Routes
# ---------------------------------------------------------------------------
@app.route("/admin")
@admin_required
def admin_dashboard():
    """
    Admin control panel:
    - Summary analytics (voters count, polls count, total votes)
    - Candidate list with poll names & delete option
    - Poll list with status toggle and delete option
    - Registered voters list
    """
    total_voters = g.db.execute("SELECT COUNT(*) AS cnt FROM users WHERE role = 'voter'").fetchone()["cnt"]
    total_polls = g.db.execute("SELECT COUNT(*) AS cnt FROM polls").fetchone()["cnt"]
    total_votes = g.db.execute("SELECT COUNT(*) AS cnt FROM votes").fetchone()["cnt"]

    polls = g.db.execute("SELECT * FROM polls ORDER BY id DESC").fetchall()

    # Candidates joined with poll title
    candidates = g.db.execute("""
        SELECT c.*, p.title AS poll_title
        FROM candidates c
        JOIN polls p ON c.poll_id = p.id
        ORDER BY c.poll_id DESC, c.id ASC
    """).fetchall()

    # Voters list with their voting activity count
    voters = g.db.execute("""
        SELECT u.id, u.name, u.student_id, COUNT(v.id) AS votes_cast
        FROM users u
        LEFT JOIN votes v ON u.id = v.voter_id
        WHERE u.role = 'voter'
        GROUP BY u.id
        ORDER BY u.id ASC
    """).fetchall()

    return render_template(
        "admin.html",
        total_voters=total_voters,
        total_polls=total_polls,
        total_votes=total_votes,
        polls=polls,
        candidates=candidates,
        voters=voters
    )


@app.route("/admin/candidate/add", methods=["POST"])
@admin_required
def admin_add_candidate():
    """Admin route to manually add candidate details to an election."""
    name = request.form.get("name", "").strip()
    description = request.form.get("description", "").strip()
    poll_id = request.form.get("poll_id")

    if not name or not poll_id:
        flash("Candidate name and target election are required.", "danger")
        return redirect(url_for("admin_dashboard"))

    try:
        g.db.execute(
            "INSERT INTO candidates (name, description, poll_id) VALUES (?, ?, ?)",
            (name, description, poll_id)
        )
        g.db.commit()
        flash(f"Candidate '{name}' has been added successfully.", "success")
    except Exception as e:
        flash(f"Error adding candidate details: {str(e)}", "danger")

    return redirect(url_for("admin_dashboard"))


@app.route("/admin/candidate/delete/<int:candidate_id>", methods=["POST"])
@admin_required
def admin_delete_candidate(candidate_id):
    """Admin route to remove a candidate."""
    cand = g.db.execute("SELECT name FROM candidates WHERE id = ?", (candidate_id,)).fetchone()
    if cand:
        g.db.execute("DELETE FROM candidates WHERE id = ?", (candidate_id,))
        g.db.commit()
        flash(f"Candidate '{cand['name']}' was removed.", "info")
    else:
        flash("Candidate not found.", "warning")

    return redirect(url_for("admin_dashboard"))


@app.route("/admin/poll/add", methods=["POST"])
@admin_required
def admin_add_poll():
    """Admin route to create a new election (requires only the election name)."""
    title = request.form.get("title", "").strip()

    if not title:
        flash("Election name is required.", "danger")
        return redirect(url_for("admin_dashboard"))

    now = datetime.now()
    start_time = request.form.get("start_time", "").strip()
    if not start_time:
        start_time = now.strftime("%Y-%m-%d %H:%M:%S")
    else:
        start_time = start_time.replace("T", " ")
        if len(start_time) == 16:
            start_time += ":00"

    end_time = request.form.get("end_time", "").strip()
    if not end_time:
        end_time = "Ongoing"
    else:
        end_time = end_time.replace("T", " ")
        if len(end_time) == 16:
            end_time += ":00"

    status = request.form.get("status", "active")

    try:
        g.db.execute(
            "INSERT INTO polls (title, start_time, end_time, status) VALUES (?, ?, ?, ?)",
            (title, start_time, end_time, status)
        )
        g.db.commit()
        flash(f"Election '{title}' added successfully! You can now add candidate details manually.", "success")
    except Exception as e:
        flash(f"Error adding election: {str(e)}", "danger")

    return redirect(url_for("admin_dashboard"))


@app.route("/admin/poll/toggle/<int:poll_id>", methods=["POST"])
@admin_required
def admin_toggle_poll(poll_id):
    """Admin route to toggle poll between 'active' and 'closed'."""
    poll = g.db.execute("SELECT status, title FROM polls WHERE id = ?", (poll_id,)).fetchone()
    if poll:
        new_status = "closed" if poll["status"] == "active" else "active"
        g.db.execute("UPDATE polls SET status = ? WHERE id = ?", (new_status, poll_id))
        g.db.commit()
        flash(f"Poll '{poll['title']}' status changed to {new_status.upper()}.", "info")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/poll/delete/<int:poll_id>", methods=["POST"])
@admin_required
def admin_delete_poll(poll_id):
    """Admin route to delete a poll along with its candidates and votes."""
    poll = g.db.execute("SELECT title FROM polls WHERE id = ?", (poll_id,)).fetchone()
    if poll:
        g.db.execute("DELETE FROM polls WHERE id = ?", (poll_id,))
        g.db.commit()
        flash(f"Poll '{poll['title']}' and its associated votes/candidates were deleted.", "info")
    return redirect(url_for("admin_dashboard"))


# ---------------------------------------------------------------------------
# Application Entry Point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print("\n" + "=" * 60)
    print(" ONLINE VOTING SYSTEM (Classroom Demonstration Project)")
    print(f" Access the application at: http://127.0.0.1:{port}")
    print(" Default Admin: ADMIN001 / admin123")
    print(" Default Voter: STU1001 / voter123")
    print("=" * 60 + "\n")

    # Run Flask server (0.0.0.0 allows external cloud routing and port binding)
    app.run(debug=True, host="0.0.0.0", port=port)
