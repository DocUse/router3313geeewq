from __future__ import annotations


SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS portals (
    member_id TEXT PRIMARY KEY,
    domain TEXT NOT NULL,
    application_token TEXT,
    access_token TEXT,
    refresh_token TEXT,
    client_endpoint TEXT,
    server_endpoint TEXT,
    status TEXT,
    installed_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""
