from datetime import datetime
import operator
import sqlite3
from decimal import Decimal, DivisionByZero, InvalidOperation
from pathlib import Path

from flask import Flask, redirect, render_template, request, url_for


app = Flask(__name__)
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "calculator.db"

OPERATIONS = {
    "add": ("+", operator.add),
    "subtract": ("-", operator.sub),
    "multiply": ("x", operator.mul),
    "divide": ("/", operator.truediv),
}


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS calculations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                first_number TEXT NOT NULL,
                second_number TEXT NOT NULL,
                operation TEXT NOT NULL,
                result TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.commit()


def format_decimal(value):
    if isinstance(value, Decimal):
        normalized = value.normalize()
        return format(normalized, "f").rstrip("0").rstrip(".") or "0"
    return str(value)


def calculate(first_number, second_number, operation):
    if operation not in OPERATIONS:
        raise ValueError("Please select a valid operation.")

    try:
        first = Decimal(first_number)
        second = Decimal(second_number)
    except InvalidOperation as exc:
        raise ValueError("Please enter valid numbers only.") from exc

    symbol, fn = OPERATIONS[operation]
    if operation == "divide" and second == 0:
        raise ValueError("Cannot divide by zero.")

    try:
        result = fn(first, second)
    except DivisionByZero as exc:
        raise ValueError("Cannot divide by zero.") from exc

    expression = f"{format_decimal(first)} {symbol} {format_decimal(second)}"
    return expression, format_decimal(result)


@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    error = None
    expression = None

    if request.method == "POST":
        first_number = request.form.get("first_number", "").strip()
        second_number = request.form.get("second_number", "").strip()
        operation = request.form.get("operation", "").strip()

        try:
            expression, result = calculate(first_number, second_number, operation)
            with get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO calculations
                    (first_number, second_number, operation, result, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        first_number,
                        second_number,
                        OPERATIONS[operation][0],
                        result,
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    ),
                )
                conn.commit()
        except ValueError as exc:
            error = str(exc)

    with get_connection() as conn:
        history = conn.execute(
            "SELECT * FROM calculations ORDER BY id DESC LIMIT 8"
        ).fetchall()

    return render_template(
        "index.html",
        result=result,
        error=error,
        expression=expression,
        operations=OPERATIONS,
        history=history,
    )


@app.route("/history")
def history():
    with get_connection() as conn:
        calculations = conn.execute(
            "SELECT * FROM calculations ORDER BY id DESC"
        ).fetchall()
    return render_template("history.html", calculations=calculations)


@app.route("/clear", methods=["POST"])
def clear_history():
    with get_connection() as conn:
        conn.execute("DELETE FROM calculations")
        conn.commit()
    return redirect(url_for("history"))


init_db()


if __name__ == "__main__":
    app.run(debug=True)
