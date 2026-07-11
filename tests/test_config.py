from app.core.config import normalize_database_url


def test_normalize_database_url_keeps_sqlite_urls_unchanged():
    assert normalize_database_url("sqlite+aiosqlite:///./nutrilens.db") == "sqlite+aiosqlite:///./nutrilens.db"


def test_normalize_database_url_converts_neon_pooler_url_for_asyncpg():
    raw_url = (
        "postgresql://neondb_owner:secret@example-pooler.aws.neon.tech/neondb"
        "?sslmode=require&channel_binding=require"
    )

    assert (
        normalize_database_url(raw_url)
        == "postgresql+asyncpg://neondb_owner:secret@example-pooler.aws.neon.tech/neondb?ssl=require"
    )


def test_normalize_database_url_rewrites_asyncpg_sslmode_query():
    raw_url = "postgresql+asyncpg://user:secret@example.com/db?sslmode=require&application_name=nutrilens"

    assert (
        normalize_database_url(raw_url)
        == "postgresql+asyncpg://user:secret@example.com/db?application_name=nutrilens&ssl=require"
    )
