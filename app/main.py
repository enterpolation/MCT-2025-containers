from typing import Dict, Generator
from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from db import SessionLocal, Visit


app = FastAPI()


def get_db() -> Generator[Session, None, None]:
    """
    Dependency that provides a database session.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


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
    return "pong"


@app.get("/visits")
def get_visits(db: Session = Depends(get_db)) -> Dict[str, int]:
    """
    Retrieves the total number of visits recorded in the database.

    :param db: Database session.
    :return: A dictionary with the count of visits.
    """
    count = db.query(Visit).count()
    return {"visits": count}


@app.get("/health")
def health() -> Dict[str, str]:
    """
    Health check endpoint.

    :return: A dictionary indicating the service is healthy.
    """
    return {"status": "ok"}
