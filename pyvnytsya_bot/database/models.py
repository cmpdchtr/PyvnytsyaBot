from sqlalchemy import Column, Integer, String, BigInteger, ForeignKey, Boolean, Text
from sqlalchemy.orm import relationship
from .base import Base

class User(Base):
    __tablename__ = "users"

    id = Column(BigInteger, primary_key=True) # Telegram ID
    username = Column(String, nullable=True)
    full_name = Column(String, nullable=True)

class Room(Base):
    __tablename__ = "rooms"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(6), unique=True, nullable=False)
    creator_id = Column(BigInteger, ForeignKey("users.id"))
    is_active = Column(Boolean, default=False)
    is_finished = Column(Boolean, default=False)
    scenario = Column(Text, nullable=True) # AI generated scenario
    
    players = relationship("Player", back_populates="room", cascade="all, delete-orphan")

class Player(Base):
    __tablename__ = "players"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id"))
    room_id = Column(Integer, ForeignKey("rooms.id"))
    
    # Characteristics
    profession = Column(String, nullable=True)
    health = Column(String, nullable=True)
    hobby = Column(String, nullable=True)
    phobia = Column(String, nullable=True)
    inventory = Column(String, nullable=True)
    fact = Column(String, nullable=True)
    
    is_kicked = Column(Boolean, default=False)
    
    room = relationship("Room", back_populates="players")
    user = relationship("User")
