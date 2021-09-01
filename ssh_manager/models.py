import hashlib
import os
from typing import Any

from .database import Database


class ModelException(Exception):
    pass


def get_more_than_one_results_exception():
    class MoreThanOneResultsException(ModelException):
        def __init__(self, *args, **kwargs):
            if args:
                return super().__init__(*args, **kwargs)

            return super().__init__(
                    "Query returned more than 1 results", **kwargs)

    return MoreThanOneResultsException


def get_not_found_exception_class():
    class NotFoundException(ModelException):
        def __init__(self, *args, **kwargs):
            if args:
                return super().__init__(*args, **kwargs)

            return super().__init__(
                    "Couldn't find a row that matches the given constraints",
                    **kwargs)

    return NotFoundException


class Model:
    __tablename__ = None
    __columns__ = None
    __pk_column__ = "id"

    ModelException = ModelException
    NotFoundException = get_not_found_exception_class()
    MoreThanOneResultsException = get_more_than_one_results_exception()

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
        objs = cls.get_columns_by_conditions(cls.__columns__, kwargs)
        if len(objs) > 1:
            raise cls.MoreThanOneResultsException()

        return objs[0]

    @classmethod
    def filter_by(cls, **kwargs):
        objs = cls.get_columns_by_conditions(cls.__columns__, kwargs)
        return objs

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


class Migration(Model):
    """
    Class for migrations table that is used internally to track DB migrations
    """
    __tablename__ = "migrations"
    __columns__ = ["id", "name", "hash", "previous", "next"]


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
    __columns__ = ["id", "name", "username", "password", "host", "profile_id"]

    def __init__(self,
                 id: int,
                 name: str,
                 username: str,
                 password: str,
                 host: str,
                 profile_id: int):
        self.id = id
        self.name = name
        self.username = username
        self.password = password
        self.host = host
        self.profile_id = profile_id

        super().__init__()

    @classmethod
    def get_names_by_profile_name(cls, profile_name: str) -> list[str]:
        profile = Profile.get_by(name=profile_name)
        logins = cls.filter_by(profile_id=profile.id)
        return [login.name for login in logins]

    @property
    def profile(self):
        return Profile.get(self.profile_id)


def get_hash(password: str) -> str:
    return hashlib.blake2b(password.encode()).hexdigest()
