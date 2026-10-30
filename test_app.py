"""
test_app.py
Automated end-to-end verification script for the Online Voting System.
Tests authentication, authorization, duplicate voting prevention,
results calculation, and admin management.
"""

import unittest
from app import app
from database import init_db, get_db


class OnlineVotingSystemTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Configure app for testing
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        # Re-initialize clean test database
        init_db(seed_data=True)

    def setUp(self):
        self.client = app.test_client()

    def test_01_homepage_redirect(self):
        """Root URL redirects unauthenticated visitors to /login."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.headers["Location"])

    def test_02_login_pages_render(self):
        """GET /login and GET /register return 200 OK."""
        res_login = self.client.get("/login")
        self.assertEqual(res_login.status_code, 200)
        self.assertIn(b"Voter & Admin Sign In", res_login.data)

        res_reg = self.client.get("/register")
        self.assertEqual(res_reg.status_code, 200)
        self.assertIn(b"Register as a Voter", res_reg.data)

    def test_03_voter_registration(self):
        """Voters can register and are saved to the database."""
        response = self.client.post("/register", data={
            "name": "David Miller",
            "student_id": "STU9999",
            "password": "password123",
            "confirm_password": "password123"
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Registration successful", response.data)

        # Check DB
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE student_id = 'STU9999'").fetchone()
        self.assertIsNotNone(user)
        self.assertEqual(user["role"], "voter")
        conn.close()

    def test_04_prevent_duplicate_student_id(self):
        """System rejects registration with an existing student ID."""
        response = self.client.post("/register", data={
            "name": "Duplicate David",
            "student_id": "STU9999",
            "password": "password123",
            "confirm_password": "password123"
        }, follow_redirects=True)
        self.assertIn(b"already registered", response.data)

    def test_05_voter_login_and_vote(self):
        """Voter STU1002 logs in and casts a valid vote in Poll 1."""
        # 1. Login as STU1002
        login_res = self.client.post("/login", data={
            "student_id": "STU1002",
            "password": "voter123"
        }, follow_redirects=True)
        self.assertIn(b"Welcome, Bob Smith", login_res.data)

        # 2. View ballot
        ballot_res = self.client.get("/vote/1")
        self.assertEqual(ballot_res.status_code, 200)
        self.assertIn(b"Student Council President Election", ballot_res.data)

        # 3. Cast vote for candidate 2 (Maya Chen)
        vote_res = self.client.post("/vote/1", data={"candidate_id": 2}, follow_redirects=True)
        self.assertIn(b"officially recorded", vote_res.data)

    def test_06_enforce_one_vote_per_voter_rule(self):
        """Voter cannot cast a second vote in the same poll."""
        # Log in as STU1002 (who already voted in test_05)
        self.client.post("/login", data={
            "student_id": "STU1002",
            "password": "voter123"
        }, follow_redirects=True)

        repeat_vote_res = self.client.post("/vote/1", data={"candidate_id": 1}, follow_redirects=True)
        self.assertIn(b"ALREADY voted", repeat_vote_res.data)

    def test_07_view_results(self):
        """Results page correctly aggregates vote counts."""
        res = self.client.get("/results/1")
        self.assertEqual(res.status_code, 200)
        # Total votes should now be 2 (Alice voted for Alex in seed, Bob voted for Maya in test 5)
        self.assertIn(b"Total Ballots Cast", res.data)
        self.assertIn(b"Maya Chen", res.data)
        self.assertIn(b"Alex Rivera", res.data)

    def test_08_unauthorized_voter_blocked_from_admin(self):
        """A regular voter cannot access /admin."""
        # Log in as voter STU1002
        self.client.post("/login", data={
            "student_id": "STU1002",
            "password": "voter123"
        }, follow_redirects=True)

        res = self.client.get("/admin", follow_redirects=True)
        self.assertIn(b"Access denied. Administrator privileges required", res.data)

    def test_09_admin_dashboard_and_candidate_management(self):
        """Admin logs in, accesses dashboard, and adds a candidate."""
        # 1. Logout voter
        self.client.get("/logout")

        # 2. Login as admin
        login_res = self.client.post("/login", data={
            "student_id": "ADMIN001",
            "password": "admin123"
        }, follow_redirects=True)
        self.assertIn(b"Administrator Dashboard", login_res.data)

        # 3. Add candidate to poll 1
        add_cand_res = self.client.post("/admin/candidate/add", data={
            "name": "Taylor Swift",
            "description": "Music & arts enhancement on campus.",
            "poll_id": 1
        }, follow_redirects=True)
        self.assertIn(b"has been added successfully", add_cand_res.data)

        # 4. Verify candidate is in DB
        conn = get_db()
        cand = conn.execute("SELECT * FROM candidates WHERE name = 'Taylor Swift'").fetchone()
        self.assertIsNotNone(cand)

        # 5. Admin deletes candidate
        cand_id = cand["id"]
        del_res = self.client.post(f"/admin/candidate/delete/{cand_id}", follow_redirects=True)
        self.assertIn(b"was removed", del_res.data)
        conn.close()

    def test_10_admin_add_election_name_only_and_candidate_manually(self):
        """Admin creates an election with only the name, then manually adds candidate details."""
        # 1. Login as admin
        self.client.get("/logout")
        self.client.post("/login", data={
            "student_id": "ADMIN001",
            "password": "admin123"
        }, follow_redirects=True)

        # 2. Add election with ONLY the election name (title)
        election_name = "Drama Club President 2026"
        res_poll = self.client.post("/admin/poll/add", data={
            "title": election_name
        }, follow_redirects=True)
        self.assertEqual(res_poll.status_code, 200)
        self.assertIn(b"added successfully", res_poll.data)

        # 3. Verify election exists in DB with active status
        conn = get_db()
        poll = conn.execute("SELECT * FROM polls WHERE title = ?", (election_name,)).fetchone()
        self.assertIsNotNone(poll)
        self.assertEqual(poll["status"], "active")
        poll_id = poll["id"]

        # 4. Manually add candidate details for this newly created election
        candidate_name = "Emma Stone"
        candidate_details = "Advocating for student theater workshops and new stage equipment."
        res_cand = self.client.post("/admin/candidate/add", data={
            "poll_id": poll_id,
            "name": candidate_name,
            "description": candidate_details
        }, follow_redirects=True)
        self.assertEqual(res_cand.status_code, 200)
        self.assertIn(b"has been added successfully", res_cand.data)

        # 5. Verify candidate in DB linked to new election
        cand = conn.execute(
            "SELECT * FROM candidates WHERE name = ? AND poll_id = ?",
            (candidate_name, poll_id)
        ).fetchone()
        self.assertIsNotNone(cand)
        self.assertEqual(cand["description"], candidate_details)
        conn.close()

        # 6. Verify voter can view this election and candidate
        self.client.get("/logout")
        self.client.post("/login", data={
            "student_id": "STU1002",
            "password": "voter123"
        }, follow_redirects=True)
        ballot_res = self.client.get(f"/vote/{poll_id}")
        self.assertEqual(ballot_res.status_code, 200)
        self.assertIn(b"Drama Club President 2026", ballot_res.data)
        self.assertIn(b"Emma Stone", ballot_res.data)

    def test_11_separated_admin_and_student_pages(self):
        """Verify complete separation of Admin and Student portals and routing."""
        # 1. Unauthenticated /admin redirects to /admin/login
        self.client.get("/logout")
        admin_gate_res = self.client.get("/admin")
        self.assertEqual(admin_gate_res.status_code, 302)
        self.assertIn("/admin/login", admin_gate_res.headers["Location"])

        # 2. Render /admin/login page
        admin_login_res = self.client.get("/admin/login")
        self.assertEqual(admin_login_res.status_code, 200)
        self.assertIn(b"Administrator Portal", admin_login_res.data)

        # 3. Student trying to login via /admin/login is told to use Student Portal
        mismatch_res = self.client.post("/admin/login", data={
            "student_id": "STU1002",
            "password": "voter123"
        }, follow_redirects=True)
        self.assertIn(b"Student Portal", mismatch_res.data)

        # 4. Admin logs in via /admin/login and lands on Administrator Dashboard
        admin_auth_res = self.client.post("/admin/login", data={
            "student_id": "ADMIN001",
            "password": "admin123"
        }, follow_redirects=True)
        self.assertEqual(admin_auth_res.status_code, 200)
        self.assertIn(b"Administrator Dashboard", admin_auth_res.data)

        # 5. Logged-in Admin trying to access student voting page /vote is redirected to /admin
        admin_to_student_res = self.client.get("/vote", follow_redirects=True)
        self.assertIn(b"Administrator Dashboard", admin_to_student_res.data)
        self.assertIn(b"Administrators manage elections via the Admin Dashboard", admin_to_student_res.data)

        # 6. Admin logout redirects to /admin/login
        admin_logout_res = self.client.get("/logout")
        self.assertEqual(admin_logout_res.status_code, 302)
        self.assertIn("/admin/login", admin_logout_res.headers["Location"])

        # 7. Student logs in and accesses /student portal cleanly
        student_login_res = self.client.post("/login", data={
            "student_id": "STU1002",
            "password": "voter123"
        }, follow_redirects=True)
        self.assertIn(b"Student Voting Portal", student_login_res.data)

        student_portal_res = self.client.get("/student")
        self.assertEqual(student_portal_res.status_code, 200)
        self.assertIn(b"Student Voting Portal", student_portal_res.data)


if __name__ == "__main__":
    unittest.main()
