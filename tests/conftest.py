import os
import tempfile

import pytest

import database.db as db_module

_fd, _TEST_DB_PATH = tempfile.mkstemp(suffix=".db")
os.close(_fd)
db_module.DB_PATH = _TEST_DB_PATH  # must happen before `app` is imported below

from app import app as flask_app                       # noqa: E402
from database.db import get_db, init_db, seed_db       # noqa: E402
from werkzeug.security import generate_password_hash   # noqa: E402


@pytest.fixture(autouse=True)
def _reset_db():
    conn = get_db()
    conn.execute("DELETE FROM expenses")
    conn.execute("DELETE FROM users")
    conn.commit()
    conn.close()
    init_db()
    seed_db()
    yield


@pytest.fixture
def client():
    flask_app.config.update(TESTING=True)
    return flask_app.test_client()


@pytest.fixture
def seeded_user_id():
    conn = get_db()
    row = conn.execute(
        "SELECT id FROM users WHERE email = ?", ("demo@spendly.com",)
    ).fetchone()
    conn.close()
    return row["id"]


@pytest.fixture
def empty_user_id():
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        ("Empty User", "empty@spendly.com", generate_password_hash("password123")),
    )
    conn.commit()
    user_id = cur.lastrowid
    conn.close()
    return user_id


@pytest.fixture
def auth_client(client, seeded_user_id):
    with client.session_transaction() as sess:
        sess["user_id"] = seeded_user_id
        sess["user_name"] = "Demo User"
    return client
