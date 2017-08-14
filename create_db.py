# Builtin imports
import logging
import uuid
import sys
import time

# External imports
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, event
from sqlalchemy.exc import SQLAlchemyError
import itsdangerous
import bcrypt

# Internal imports
from will.schema import *

log = logging.getLogger()

# Lazy hack to make an embedded memory db accessible from unit testing
engine = None


def db_init(db_url, db_port, db_username, db_password, secret_key, client_name, debug=False):
    """
    Initialize the db
    :param db_url:
    :param db_port:
    :param db_username:
    :param db_password:
    :param secret_key:
    :param client_name:
    :return:
    """
    global engine
    signer = itsdangerous.Signer(secret_key)
    if debug:
        connection_url = "sqlite:///:memory:"
    else:
        connection_url = "mysql://{username}:{password}@{db_url}".format(
                username=db_username,
                password=db_password,
                db_url=db_url
            )

    def db_connect(connection_url, n=1):
        try:
            return create_engine(connection_url)
        except SQLAlchemyError:
            if n >= 10:
                sys.exit(1)
            else:
                time.sleep(1)
                db_connect(connection_url, n+1)
    engine = db_connect(connection_url)
    if debug:
        if sys.version_info[1] < 6:
            # If using the outdated pysqlite driver,
            # manually handle the connect and begin statements to prevent errors in python versions < 3.6
            @event.listens_for(engine, "connect")
            def do_connect(dbapi_connection, connection_record):
                # disable pysqlite's emitting of the BEGIN statement entirely.
                # also stops it from emitting COMMIT before any DDL.
                dbapi_connection.isolation_level = None

            @event.listens_for(engine, "begin")
            def do_begin(conn):
                # emit our own BEGIN
                conn.execute("BEGIN")
    else:
        # Otherwise, don't modify transactions, but create the production MySQL table
        engine.execute("CREATE DATABASE `W.I.L.L`")  # create db
        engine.execute("USE `W.I.L.L`")
    Base.metadata.create_all(engine) 
    # Create a new client
    DBSession = sessionmaker()
    DBSession.configure(bind=engine)
    session = DBSession()
    # Create the official client with the necessary fields
    raw_secret_key = str(uuid.uuid4()).encode('utf-8')
    # Hash the key. This version will be put in the database
    hashed_secret_key = bcrypt.hashpw(raw_secret_key, bcrypt.gensalt()).decode('utf-8')
    # Sign the key. This version will be returned to the user
    # Create an official client
    c = Client(client_id="web-official", official=True, client_secret=hashed_secret_key, scope="admin")
    session.add(c)
    session.commit()
    signed_secret_key = signer.sign(raw_secret_key).decode('utf-8')
    session.close()
    return signed_secret_key


if __name__ == "__main__":
    db_url, db_port, db_username, db_password, secret_key, client_name = sys.argv[1:7]
    secret_key = db_init(db_url, db_port, db_username, db_password, secret_key, client_name)
    print(secret_key)
