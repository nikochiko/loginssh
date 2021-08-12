import hashlib
import sqlite3
from textwrap import dedent

import click
from cryptography import Fernet


class DatabaseException(Exception):
    pass


class Database:
    create_profiles_table = dedent("""
            CREATE TABLE profiles (
                id INTEGER PRIMARY KEY,
                name VARCHAR UNIQUE,
                password VARCHAR
            )""")

    create_logins_table = dedent("""
            CREATE TABLE logins (
                id INTEGER PRIMARY KEY,
                name VARCHAR UNIQUE,
                username VARCHAR,
                host VARCHAR,
                password VARCHAR,
                profile_id INTEGER
            )""")

    select_profile_by_name = dedent("""
            SELECT
                id, name, password
            FROM
                profiles
            WHERE name='%(name)s'""")

    select_logins_by_profile_id = dedent("""
            SELECT
                id, name, username, host, password
            FROM
                logins
            WHERE profile_id=%(profile_id)d""")

    select_ssh_login_by_name_and_profile_id = dedent("""
            SELECT
                id, name, username, host, password
            FROM
                logins
            WHERE profile_id=%(profile_id)d AND name='%(name)s'""")

    def __init__(self, db_path):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)

    def db_init(self):
        with self.conn:
            self.conn.execute(Database.create_profiles_table)
            self.conn.execute(Database.create_logins_table)

    def get_profile_by_name(self, name: str):
        with self.conn:
            cur = self.conn.execute(Database.select_profile_by_name % {
                "name": name})
            row = cur.fetchone()

        if row is None:
            raise DatabaseException(
                    f"Row not found for table: 'profiles' with name='{name}'")

        id = row["id"]
        name = row["name"]
        password = row["password"]

        return Profile(db=self, id=id, name=name, password=password)


class Model:
    pass


class Profile(Model):
    def __init__(self, db: Database, id: int, name: str, password: str):
        self.db = db
        self.id = id
        self.name = name
        self.password = password

    def check_password(self, raw_password: str):
        # check if hash of given password matches the one in the object
        return get_hash(raw_password) == self.password


class Login(Model):
    def __init__(self,
                 db: Database,
                 id: int,
                 name: str,
                 username: str,
                 host: str,
                 profile_id: int):
        self.db = db
        self.id = id
        self.name = name
        self.username = username
        self.host = host
        self.profile_id = self.profile_id

    @property
    def profile(self):
        self.db.get_profile_by_id(self.profile_id)


def get_hash(password: str) -> str:
    return hashlib.blake2b(password.encode()).decode()
