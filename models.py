import hashlib
import os
from typing import Any

from database import Database


class Model:
    __tablename__ = None
    __columns__ = None
    __pk_column__ = "id"

    @classmethod
    @property
    def db(cls):
        return Database(os.getenv("DB_PATH"))

    @classmethod
    def get_columns_by_id(cls, columns: list[str], id: Any):
        row = cls.db.execute_select_columns_from_table_by_id(
                cls.__tablename__, columns, id)

        obj = cls(**row)
        return obj

    @classmethod
    def get(cls, id: Any):
        return cls.get_columns_by_id(cls.__columns__, id)

    @classmethod
    def get_columns_by_conditions(cls,
                                  columns: list[str],
                                  conditions: dict[str, Any]):
        rows = cls.db.execute_select_columns_from_table_by_kwargs(
                cls.__tablename__, columns, conditions)

        objs = [cls(**row) for row in rows]
        return objs

    @classmethod
    def get_by(cls, **kwargs):
        return cls.get_columns_by_conditions(cls.__columns__, kwargs)

    @classmethod
    def new(cls, **kwargs):
        row = cls.db.execute_insert_into_table(
                cls.__tablename__,
                columns=list(kwargs.keys()),
                values=list(kwargs.values()),
                id_column=cls.__pk_column__)
        return cls(**row)

    def __init__(self):
        self.db = Database(os.getenv("DB_PATH"))


class Profile(Model):
    __tablename__ = "profiles"
    __columns__ = ["id", "name", "password"]

    def __init__(self, id: int, name: str, password: str):
        self.id = id
        self.name = name
        self.password = password

        super().__init__()

    @classmethod
    def new_profile(cls, name, password):
        hashed_password = get_hash(password)
        return cls.new(name=name, password=hashed_password)

    def check_password(self, raw_password: str):
        # check if hash of given password matches the one in the object
        return get_hash(raw_password) == self.password


class Login(Model):
    __tablename__ = "logins"
    __columns__ = ["id", "name", "username", "host", "profile_id"]

    def __init__(self,
                 id: int,
                 name: str,
                 username: str,
                 host: str,
                 profile_id: int):
        self.id = id
        self.name = name
        self.username = username
        self.host = host
        self.profile_id = self.profile_id

        super().__init__()

    @property
    def profile(self):
        return Profile.get(self.profile_id)


def get_hash(password: str) -> str:
    return hashlib.blake2b(password.encode()).hexdigest()
