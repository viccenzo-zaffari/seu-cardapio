from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./cardapio.db")

if DATABASE_URL.startswith("postgresql"):
    DATABASE_URL = DATABASE_URL.split("?")[0]
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+pg8000://")
    engine = create_engine(DATABASE_URL, connect_args={"ssl_context": True})
else:
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()