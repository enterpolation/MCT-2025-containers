import os
from typing import Dict, Generator, Optional
from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
import redis

from db import SessionLocal, Visit

# Initialize FastAPI app
app = FastAPI()

# Redis connection
REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")  # Default to local Redis
CACHE_KEY: str = "visits:count"  # Redis key for visit count
redis_client: redis.Redis = redis.from_url(REDIS_URL, decode_responses=True)  # Initialize Redis client


def get_db() -> Generator[Session, None, None]:
    """
    Dependency that provides a database session.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_cached_count() -> Optional[int]:
    """
    Get visit count from Redis cache.

    :return: Cached count or None if not available.
    """
    try:
        cached = redis_client.get(CACHE_KEY)
        if cached is None:
            return None
        return int(str(cached))
    except Exception:
        return None


def update_cache(db: Session) -> int:
    """
    Query database for actual count and update cache.

    :param db: Database session.
    :return: Actual visit count.
    """
    count = db.query(Visit).count()
    try:
        redis_client.set(CACHE_KEY, count)
    except Exception:
        pass  # Cache failure shouldn't break the app
    return count


def increment_cache() -> None:
    """
    Increment cached visit count atomically.
    """
    try:
        redis_client.incr(CACHE_KEY)
    except Exception:
        pass  # Cache failure shouldn't break the app


@app.get("/ping")
def pong(db: Session = Depends(get_db)) -> str:
    """
    A simple ping endpoint that records a visit in the database.

    :param db: Database session.
    :return: A string "pong".
    """
    new_visit = Visit(client_ip="127.0.0.1")
    db.add(new_visit)
    db.commit()

    # Increment cache after successful DB write for consistency
    increment_cache()

    return "pong"


@app.get("/visits")
def get_visits(db: Session = Depends(get_db)) -> Dict[str, int]:
    """
    Retrieves the total number of visits recorded in the database.
    Uses Redis cache for performance, falls back to DB if cache miss.

    :param db: Database session.
    :return: A dictionary with the count of visits.
    """
    # Try cache first
    cached_count = get_cached_count()
    if cached_count is not None:
        return {"visits": cached_count}

    # Cache miss - query DB and update cache
    count = update_cache(db)
    return {"visits": count}


@app.get("/health")
def health() -> Dict[str, str]:
    """
    Health check endpoint.

    :return: A dictionary indicating the service is healthy.
    """
    return {"status": "ok"}
