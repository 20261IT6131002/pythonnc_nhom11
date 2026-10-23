from __future__ import annotations
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from hotel.config import DATABASE_URL

class Base(DeclarativeBase):
    pass

def make_engine(url: str):
    opts = {'pool_pre_ping': True, 'future': True}
    if url.startswith('sqlite'):
        opts['connect_args'] = {'check_same_thread': False, 'timeout': 20}
    return create_engine(url, **opts)

engine = make_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
