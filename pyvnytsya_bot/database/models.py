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
    
    # Game State
    is_active = Column(Boolean, default=False)
    is_finished = Column(Boolean, default=False)
    round_number = Column(Integer, default=0)
    phase = Column(String, default="registration") # registration, revealing, voting, finished
    survivors_count = Column(Integer, default=2) # How many should survive
    
    scenario = Column(Text, nullable=True)
    pack_id = Column(Integer, ForeignKey("game_packs.id"), nullable=True)
    
    players = relationship("Player", back_populates="room", cascade="all, delete-orphan")
    pack = relationship("GamePack")

class GamePack(Base):
    __tablename__ = "game_packs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id")) # Owner
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    data = Column(Text, nullable=False) # JSON string
    is_public = Column(Boolean, default=False)

class Player(Base):
    __tablename__ = "players"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id")) # Negative for bots
    room_id = Column(Integer, ForeignKey("rooms.id"))
    
    # Characteristics
    profession = Column(String, nullable=True)
    health = Column(String, nullable=True)
    hobby = Column(String, nullable=True)
    phobia = Column(String, nullable=True)
    inventory = Column(String, nullable=True)
    fact = Column(String, nullable=True)
    age = Column(Integer, nullable=True) # Added Age
    bio = Column(String, nullable=True) # Gender/Bio
    action_cards = Column(Text, default="[]") # JSON list of cards
    
    # Game State
    is_alive = Column(Boolean, default=True)
    revealed_traits = Column(String, default="") # Comma separated: "profession,health"
    has_voted = Column(Boolean, default=False)
    revealed_count_round = Column(Integer, default=0) # Cards revealed in current round
    votes_received = Column(Integer, default=0)
    
    room = relationship("Room", back_populates="players")
    user = relationship("User")
