import os
import sqlite3
from textwrap import dedent

from typing import Any, Optional


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
            WHERE name=?""")

    select_logins_by_profile_id = dedent("""
            SELECT
                id, name, username, host, password
            FROM
                logins
            WHERE profile_id=?""")

    select_ssh_login_by_name_and_profile_id = dedent("""
            SELECT
                id, name, username, host, password
            FROM
                logins
            WHERE profile_id=? AND name=?""")

    select_columns_from_table_by_id = dedent("""
            SELECT
                ?
            FROM
                ?
            WHERE id=?""")

    select_columns_from_table_by_kwargs = dedent("""
            SELECT
                %(columns)s
            FROM
                %(tablename)s
            WHERE %(conditions)s""")

    insert_into_table = dedent("""
            INSERT INTO %(tablename)s
                (%(columns)s)
            VALUES (%(values_qmarks)s)
            RETURNING %(returning_columns)s""")

    def __init__(self, db_path: os.PathLike):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        if os.getenv("DEBUG"):
            self.conn.set_trace_callback(print)

    def _refresh_conn(self):
        self.conn = sqlite3.connect(self.db_path)

    def init_db(self, profile_name: Optional[str] = None):
        with self.conn:
            self.conn.execute(Database.create_profiles_table)
            self.conn.execute(Database.create_logins_table)

    def rm_db(self):
        """Deletes the sqlite database"""
        os.unlink(self.db_path)

    def reset_db(self):
        """Resets the sqlite database - remove and re-initialize"""
        self.rm_db()
        self._refresh_conn()
        self.init_db()

    def execute_select_columns_from_table_by_id(
            self,
            table: str,
            columns: list[str],
            id: Any) -> dict[str, Any]:
        with self.conn:
            cursor = self.conn.execute(
                    Database.select_columns_from_table_by_id, (
                        columns, table, id))

            row = cursor.fetchone()

        if row is None:
            raise DatabaseException(
                    f"Row not found for table: '{table}' with id: {id}")

        return {column_name: row_item
                for (column_name, row_item) in zip(columns, row)}

    def execute_select_columns_from_table_by_kwargs(
            self,
            table: str,
            columns: list[str],
            conditions: dict[str, Any],
            limit: Optional[int] = None) -> list[dict[str, Any]]:

        sql_statement = self.get_select_columns_from_table_by_kwargs_sql(
                table, columns, conditions, limit=limit)

        with self.conn:
            cursor = self.conn.execute(
                    sql_statement, list(conditions.values()))

            rows = cursor.fetchall()

        if not rows:
            raise DatabaseException(
                    f"Rows not found for table: '{table}' "
                    f"and conditions: {conditions}")

        return [{column_name: row_item
                for (column_name, row_item) in zip(columns, row)}
                for row in rows]

    def get_insert_into_table_sql(self,
                                  table: str,
                                  columns: list[str],
                                  returning_columns: list[str]) -> str:
        columns_str = ", ".join(columns)
        returning_columns_str = ", ".join(returning_columns)
        values_qmarks = ", ".join("?" * len(columns))
        sql_statement = Database.insert_into_table % {
                "tablename": table,
                "columns": columns_str,
                "values_qmarks": values_qmarks,
                "returning_columns": returning_columns_str}
        return sql_statement

    def get_select_columns_from_table_by_kwargs_sql(
            self,
            table: str,
            columns: list[str],
            conditions: dict[str, Any],
            limit: Optional[int] = None) -> str:
        columns_str = ", ".join(columns)
        condition_ops = [
                f"{condition_key} IS NOT"
                if condition_value is None
                else f"{condition_key} ="
                for condition_key, condition_value in conditions.items()]
        conditions_str = " AND ".join(
                f"{op} ?" for op in condition_ops)

        sql_statement = self.select_columns_from_table_by_kwargs % {
                "tablename": table,
                "columns": columns_str,
                "conditions": conditions_str}

        if limit:
            sql_statement += f" LIMIT {limit}"

        return sql_statement

    def execute_insert_into_table(
            self,
            table: str,
            columns: list[str],
            values: list[str],
            id_column: str) -> Any:
        returning_columns = [id_column] + columns
        sql_statement = self.get_insert_into_table_sql(table,
                                                       columns,
                                                       returning_columns)
        with self.conn:
            cursor = self.conn.execute(sql_statement, (*values,))

            row = cursor.fetchone()

        return {column_name: row_item
                for (column_name, row_item) in zip(returning_columns, row)}
