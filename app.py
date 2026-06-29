from datetime import datetime
import operator
from decimal import Decimal, DivisionByZero, InvalidOperation
import os
from dotenv import load_dotenv
from flask import Flask, redirect, render_template, request, url_for
from flask.cli import load_dotenv
from pymongo import MongoClient

app = Flask(__name__)



# Load environment variables
load_dotenv()

# ==============================
# MongoDB Atlas Connection
# ==============================

MONGO_URI = os.getenv("MONGO_URI")

if not MONGO_URI:
    raise ValueError("MONGO_URI not found. Please check your .env file.")

client = MongoClient(MONGO_URI)

db = client["calculator_db"]
calculations_collection = db["calculations"]

# ==============================
# Calculator Operations
# ==============================

OPERATIONS = {
    "add": ("+", operator.add),
    "subtract": ("-", operator.sub),
    "multiply": ("x", operator.mul),
    "divide": ("/", operator.truediv),
}


def format_decimal(value):
    return str(value)

def calculate(first_number, second_number, operation):

    if first_number == "" or second_number == "":
        raise ValueError("Please enter both numbers.")

    if operation not in OPERATIONS:
        raise ValueError("Please select a valid operation.")

    try:
        first = Decimal(first_number)
        second = Decimal(second_number)

    except InvalidOperation:
        raise ValueError("Please enter valid numbers only.")

    if operation == "divide" and second == 0:
        raise ValueError("Cannot divide by zero.")

    # Manual calculations
    if operation == "add":
        result = first + second
        symbol = "+"

    elif operation == "subtract":
        result = first - second
        symbol = "-"

    elif operation == "multiply":
        result = first * second
        symbol = "x"

    elif operation == "divide":
        result = first / second
        symbol = "/"

    expression = (
        f"{format_decimal(first)} "
        f"{symbol} "
        f"{format_decimal(second)}"
    )

    return expression, format_decimal(result)

# ==============================
# Home Page
# ==============================

@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    error = None
    expression = None

    if request.method == "POST":

        first_number = request.form.get("first_number")
        second_number = request.form.get("second_number")
        operation = request.form.get("operation")

        # None అయితే empty string గా మార్చడం
        first_number = first_number.strip() if first_number else ""
        second_number = second_number.strip() if second_number else ""
        operation = operation.strip() if operation else ""

        # Empty fields validation
        if first_number == "" or second_number == "":
            error = "Please enter both numbers."

        elif operation == "":
            error = "Please select an operation."

        else:
            try:
                expression, result = calculate(
                    first_number,
                    second_number,
                    operation
                )

                # Save only successful calculations
                calculations_collection.insert_one({
                    "first_number": first_number,
                    "second_number": second_number,
                    "operation": OPERATIONS[operation][0],
                    "result": result,
                    "created_at": datetime.now()
                })

            except ValueError as exc:
                error = str(exc)

            except Exception:
                error = "Something went wrong. Please try again."

    history = list(
        calculations_collection.find()
        .sort("_id", -1)
        .limit(8)
    )

    return render_template(
        "index.html",
        result=result,
        error=error,
        expression=expression,
        operations=OPERATIONS,
        history=history
    )

# ==============================
# History Page
# ==============================

@app.route("/history")
def history():

    calculations = list(
        calculations_collection.find()
        .sort("_id", -1)
    )

    return render_template(
        "history.html",
        calculations=calculations
    )


# ==============================
# Clear History
# ==============================

@app.route("/clear", methods=["POST"])
def clear_history():

    calculations_collection.delete_many({})

    return redirect(url_for("history"))


# ==============================
# Run App
# ==============================

if __name__ == "__main__":
    app.run(debug=True)