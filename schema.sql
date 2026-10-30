-- ====================================================================
-- Online Voting System Database Schema (SQLite)
-- Classroom demonstration project
-- ====================================================================

-- Drop old tables if re-initializing
DROP TABLE IF EXISTS votes;
DROP TABLE IF EXISTS candidates;
DROP TABLE IF EXISTS polls;
DROP TABLE IF EXISTS users;

-- 1. Users Table
-- Stores credentials and user roles (voter or admin)
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    student_id TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'voter' CHECK(role IN ('voter', 'admin'))
);

-- 2. Polls Table
-- Stores election/poll information and operational status
CREATE TABLE polls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active', 'closed'))
);

-- 3. Candidates Table
-- Stores candidate details linked to specific polls
CREATE TABLE candidates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    poll_id INTEGER NOT NULL,
    FOREIGN KEY (poll_id) REFERENCES polls (id) ON DELETE CASCADE
);

-- 4. Votes Table
-- Records each ballot cast.
-- UNIQUE(voter_id, poll_id) enforces that a voter can vote at most ONCE per poll.
CREATE TABLE votes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    voter_id INTEGER NOT NULL,
    candidate_id INTEGER NOT NULL,
    poll_id INTEGER NOT NULL,
    timestamp TEXT NOT NULL DEFAULT (DATETIME('now', 'localtime')),
    FOREIGN KEY (voter_id) REFERENCES users (id) ON DELETE CASCADE,
    FOREIGN KEY (candidate_id) REFERENCES candidates (id) ON DELETE CASCADE,
    FOREIGN KEY (poll_id) REFERENCES polls (id) ON DELETE CASCADE,
    UNIQUE (voter_id, poll_id)
);
