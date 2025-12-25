from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy import event
from sqlalchemy.engine import Engine
from .config import settings

# Create engine with connection pooling and performance settings
engine = create_engine(
    settings.DATABASE_URL,
    echo=False,  # Turn off verbose SQL logging for performance
    connect_args={"check_same_thread": False},  # Allow multi-threading for SQLite
    pool_size=20,
    max_overflow=30
)

# Enable WAL mode and performance optimizations for SQLite
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    """Configure SQLite for better concurrency and performance"""
    cursor = dbapi_conn.cursor()
    # WAL mode allows concurrent reads while writing
    cursor.execute("PRAGMA journal_mode=WAL")
    # NORMAL is faster than FULL, acceptable for most use cases
    cursor.execute("PRAGMA synchronous=NORMAL")
    # Increase cache size (10000 pages ~= 40MB)
    cursor.execute("PRAGMA cache_size=10000")
    # Enable foreign key constraints
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

def get_session():
    with Session(engine) as session:
        yield session

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
