-- SQLite schema for GPG webservice users and keys
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    api_key TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS gpg_keys (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    public_key TEXT NOT NULL,
    encrypted_private_key BLOB NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(id)
);
