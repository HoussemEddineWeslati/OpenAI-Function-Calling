"""MySQL access through the stored procedures defined in db/atliq_college_db.sql."""

from __future__ import annotations

import os
from contextlib import contextmanager
from collections.abc import Iterator

import mysql.connector


@contextmanager
def cursor() -> Iterator[mysql.connector.cursor.MySQLCursor]:
    connection = mysql.connector.connect(
        host=os.environ.get("DB_HOST", "localhost"),
        port=int(os.environ.get("DB_PORT", "3306")),
        user=os.environ.get("DB_USER", "root"),
        password=os.environ["DB_PASSWORD"],
        database=os.environ.get("DB_NAME", "atliq_college_db"),
    )
    cur = connection.cursor()
    try:
        yield cur
    finally:
        cur.close()
        connection.close()


def _call(procedure: str, args: list[object]) -> float | None:
    with cursor() as cur:
        cur.callproc(procedure, args)
        for result in cur.stored_results():
            row = result.fetchone()
            if row and row[0] is not None:
                return float(row[0])
    return None


def get_marks(student_name: str, semester: int, operation: str) -> float | None:
    return _call("get_marks", [student_name, semester, operation])


def get_fees(student_name: str, semester: int, fees_type: str) -> float | None:
    return _call("get_fees", [student_name, semester, fees_type])


HANDLERS = {"get_marks": get_marks, "get_fees": get_fees}
