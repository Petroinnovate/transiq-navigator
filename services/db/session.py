"""
Database session management for SQLAlchemy
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from typing import Generator

from core.config.settings import settings
from core.logging.logger import get_logger

logger = get_logger(__name__)

# SQLAlchemy Base
Base = declarative_base()

# Database engine
engine = None
SessionLocal = None


def init_db():
    """Initialize database connection"""
    global engine, SessionLocal
    
    database_url = settings.DATABASE_URL
    
    # SQLAlchemy requires postgresql:// not postgres://
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
    # SQLite needs check_same_thread=False for FastAPI
    connect_args = {}
    if database_url.startswith('sqlite'):
        connect_args = {"check_same_thread": False}
    
    # Connection pooling for PostgreSQL
    pool_config = {}
    if database_url.startswith('postgresql'):
        pool_config = {
            "pool_size": 10,          # Number of persistent connections
            "max_overflow": 20,        # Max overflow connections
            "pool_timeout": 30,        # Timeout for getting connection
            "pool_recycle": 3600,      # Recycle connections after 1 hour
            "pool_pre_ping": True,     # Verify connections before using
        }
    
    engine = create_engine(
        database_url,
        connect_args=connect_args,
        echo=settings.DEBUG,  # Log SQL queries in debug mode
        **pool_config
    )
    
    SessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine
    )
    
    logger.info(f"Database engine initialized: {database_url.split('@')[-1] if '@' in database_url else database_url}")
    
    # Create tables (only if they don't exist)
    try:
        # Import all models so Base.metadata knows about them
        import services.db.models  # noqa: F401  — core TransIQ models
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created/verified")
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")
        raise


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency for database sessions
    
    Usage:
        @app.get("/items/")
        def read_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
    """
    if SessionLocal is None:
        init_db()
    
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context():
    """
    Context manager for database sessions (for use outside FastAPI)
    
    Usage:
        with get_db_context() as db:
            db.query(Item).all()
    """
    if SessionLocal is None:
        init_db()
    
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def close_db():
    """Close database connections"""
    global engine
    if engine:
        engine.dispose()
        logger.info("Database connections closed")


# Alias used by DDR endpoints
get_db_session = get_db_context
