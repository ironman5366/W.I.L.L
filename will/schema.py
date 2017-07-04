# External imports
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import Column, String, Boolean, DateTime, PickleType, Integer, ForeignKey, Text

Base = declarative_base()


class Association(Base):
    __tablename__ = 'association'
    username = Column(String(50), ForeignKey('users.username'), primary_key=True)
    client_id = Column(String(50), ForeignKey('clients.client_id'), primary_key=True)
    access_token = Column(String(100), default=None)
    user_token = Column(String(100), default=None)
    scope = Column(String(15))
    user = relationship("User", back_populates="clients")
    client = relationship("Client", back_populates="users")


class User(Base):

    __tablename__ = "users"

    username = Column(String(50), primary_key=True)

    first_name = Column(String(50))
    last_name = Column(String(50))
    password = Column(Text)
    created = Column(DateTime)
    admin = Column(Boolean, default=False)
    settings = Column(PickleType)
    clients = relationship("Association", back_populates="user")
    notifications = relationship("NotificationStore")


class Client(Base):
    __tablename__ = "clients"

    client_id = Column(String(50), primary_key=True)
    official = Column(Boolean(50), default=False)
    client_secret = Column(Text)
    scope = Column(String(15))
    users = relationship("Association", back_populates="client")


class NotificationStore(Base):
    __tablename__ = "notifications"

    uid = Column(String(50), primary_key=True)
    message = Column(Text)
    title = Column(String(50))
    trigger_time = Column(DateTime)
    scope = Column(String(50))
    summary = Column(Text)
    created = Column(DateTime)

    user_id = Column(String(50), ForeignKey('users.username'))


class APIKey(Base):
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key_type = Column(String(50))
    value = Column(String(50))
    max_usages = Column(Integer)
    usages = Column(Integer)
    refresh = Column(Integer)
    timestamp = Column(DateTime)
    key_url = Column(String(50), default=None)