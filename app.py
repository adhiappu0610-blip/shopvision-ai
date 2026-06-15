from flask import Flask, render_template, request, redirect, session, flash, make_response
import sqlite3
import csv
import os
import pandas as pd
from sklearn.linear_model import LinearRegression
import numpy as np
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = "shopvision_secret_key"

DB = "shopvision.db"
CSV_FILE = "data/sample_sales.csv"


def db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT UNIQUE,
        password TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS products(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product TEXT,
        category TEXT,
        price REAL,
        cost REAL,
        stock INTEGER,
        sold INTEGER,
        branch TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS bills(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer TEXT,
        subtotal REAL,
        gst REAL,
        grand_total REAL,
        created_at TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS bill_items(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bill_id INTEGER,
        product_id INTEGER,
        product TEXT,
        qty INTEGER,
        price REAL,
        total REAL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS expenses(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        amount REAL,
        created_at TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS customers(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        phone TEXT,
        created_at TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS chat_history(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        question TEXT,
        answer TEXT,
        created_at TEXT
    )
    """)

    conn.commit()
    conn.close()


def import_csv_once():
    conn = db()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM products")
    count = cur.fetchone()[0]

    if count == 0 and os.path.exists(CSV_FILE):

        with open(CSV_FILE, "r", encoding="utf-8") as file:

            reader = csv.DictReader(file)

            for row in reader:

                cur.execute("""
                INSERT INTO products(product, category, price, cost, stock, sold, branch)
                VALUES(?,?,?,?,?,?,?)
                """, (
                    row["product"],
                    row["category"],
                    float(row["price"]),
                    float(row["cost"]),
                    int(row["stock"]),
                    int(row["sold"]),
                    row["branch"]
                ))

    conn.commit()
    conn.close()


def predict_future_sales():

    try:

        df = pd.read_csv(CSV_FILE)

        X = np.array(range(len(df))).reshape(-1, 1)

        y = df["sold"]

        model = LinearRegression()

        model.fit(X, y)

        future = model.predict([[len(df) + 1]])

        return round(float(future[0]), 2)

    except:
        return 0


def check_login():
    return "user_id" in session


@app.route("/")
def home():

    if check_login():
        return redirect("/dashboard")

    return render_template("home.html")


@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        conn = db()
        cur = conn.cursor()

        try:

            cur.execute("""
            INSERT INTO users(name, email, password)
            VALUES(?,?,?)
            """, (
                request.form["name"],
                request.form["email"],
                request.form["password"]
            ))

            conn.commit()

            flash("Registration successful", "success")

            return redirect("/login")

        except:

            flash("Email already exists", "danger")

        finally:

            conn.close()

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        conn = db()
        cur = conn.cursor()

        cur.execute("""
        SELECT * FROM users
        WHERE email=? AND password=?
        """, (
            request.form["email"],
            request.form["password"]
        ))

        user = cur.fetchone()

        conn.close()

        if user:

            session["user_id"] = user["id"]
            session["name"] = user["name"]

            return redirect("/dashboard")

        flash("Invalid email or password", "danger")

    return render_template("login.html")


@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")


@app.route("/dashboard")
def dashboard():

    if not check_login():
        return redirect("/login")

    conn = db()
    cur = conn.cursor()

    cur.execute("SELECT SUM(price * sold) FROM products")
    total_sales = cur.fetchone()[0] or 0

    cur.execute("SELECT SUM((price - cost) * sold) FROM products")
    gross_profit = cur.fetchone()[0] or 0

    cur.execute("SELECT COUNT(*) FROM products")
    products_count = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM bills")
    bills_count = cur.fetchone()[0]

    cur.execute("SELECT product FROM products ORDER BY sold DESC LIMIT 1")
    best = cur.fetchone()

    best_product = best["product"] if best else "No Data"

    future_sales = predict_future_sales()

    cur.execute("SELECT product, sold FROM products ORDER BY sold DESC LIMIT 6")
    chart_data = cur.fetchall()

    conn.close()

    return render_template(
        "dashboard.html",
        total_sales=round(total_sales, 2),
        gross_profit=round(gross_profit, 2),
        products_count=products_count,
        bills_count=bills_count,
        best_product=best_product,
        future_sales=future_sales,
        chart_data=chart_data
    )


@app.route("/inventory")
def inventory():

    if not check_login():
        return redirect("/login")

    conn = db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM products ORDER BY stock ASC")

    products = cur.fetchall()

    conn.close()

    return render_template("inventory.html", products=products)


@app.route("/analytics")
def analytics():

    if not check_login():
        return redirect("/login")

    conn = db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM products ORDER BY sold DESC")

    products = cur.fetchall()

    conn.close()

    return render_template("analytics.html", products=products)


@app.route("/reports")
def reports():

    if not check_login():
        return redirect("/login")

    conn = db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM bills ORDER BY id DESC")

    bills = cur.fetchall()

    conn.close()

    return render_template("reports.html", bills=bills)


@app.route("/ai", methods=["GET", "POST"])
def ai():

    if not check_login():
        return redirect("/login")

    answer = ""

    conn = db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM products")

    products = cur.fetchall()

    if request.method == "POST":

        question = request.form["question"]

        q = question.lower().strip()

        matched_product = None

        for p in products:

            pname = p["product"].lower()

            if pname in q:

                matched_product = p

                break

            for word in pname.split():

                if len(word) >= 3 and word in q:

                    matched_product = p

                    break

            if matched_product:
                break

        if matched_product:

            p = matched_product

            profit_per_unit = round(
                p["price"] - p["cost"], 2
            )

            total_profit = round(
                (p["price"] - p["cost"]) * p["sold"], 2
            )

            predicted = int(
                p["sold"] * 1.15
            )

            if "stock" in q or "available" in q:

                answer = f"""
📦 Stock Details

Product: {p['product']}

Current Stock:
{p['stock']} units

Sold:
{p['sold']} units

Status:
{'Low stock. Reorder needed.' if p['stock'] <= 15 else 'Stock available.'}
"""

            elif "price" in q or "rate" in q:

                answer = f"""
💵 Price Details

Product:
{p['product']}

Selling Price:
₹{p['price']}

Cost Price:
₹{p['cost']}

Profit Per Unit:
₹{profit_per_unit}
"""

            elif "profit" in q:

                answer = f"""
💰 Profit Details

Product:
{p['product']}

Profit Per Unit:
₹{profit_per_unit}

Total Profit:
₹{total_profit}
"""

            elif "sales" in q or "sold" in q:

                answer = f"""
📈 Sales Details

Product:
{p['product']}

Sold Units:
{p['sold']} units
"""

            elif "predict" in q or "prediction" in q:

                answer = f"""
🤖 Product Prediction

Product:
{p['product']}

Current Sold:
{p['sold']} units

Predicted Next Month:
{predicted} units
"""

            else:

                answer = f"""
🛒 Product Details

Product:
{p['product']}

Category:
{p['category']}

Price:
₹{p['price']}

Stock:
{p['stock']} units

Sold:
{p['sold']} units
"""

        elif "slow" in q:

            slow = [
                p for p in products
                if p["sold"] <= 70
            ]

            answer = "🐢 Slow Moving Products\n\n"

            for p in slow:

                answer += f"""
{p['product']}
Sold: {p['sold']} units

"""

        elif "best" in q:

            best = max(
                products,
                key=lambda x: x["sold"]
            )

            answer = f"""
🏆 Best Selling Product

{best['product']}

Sold:
{best['sold']} units
"""

        elif "predict" in q or "high" in q or "low" in q:

            high_product = max(
                products,
                key=lambda x: x["sold"]
            )

            low_product = min(
                products,
                key=lambda x: x["sold"]
            )

            answer = f"""
📈 High & Low Product Prediction

🔥 High Selling Product:
{high_product['product']}

Current Sold:
{high_product['sold']} units

Predicted:
{int(high_product['sold'] * 1.20)} units


🐢 Low Selling Product:
{low_product['product']}

Current Sold:
{low_product['sold']} units

Predicted:
{int(low_product['sold'] * 0.90)} units
"""

        elif "ml" in q or "machine learning" in q:

            prediction = predict_future_sales()

            answer = f"""
🤖 Machine Learning Forecast

Model:
Linear Regression

Future Sales Prediction:
{prediction} units
"""

        else:

            answer = """
Ask Like:

stock of milk
price of milk
profit of milk
sales of milk
prediction of milk
milk details
best selling product
show slow moving products
"""

        cur.execute("""
        INSERT INTO chat_history(question, answer, created_at)
        VALUES(?,?,?)
        """, (
            question,
            answer,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))

        conn.commit()

    conn.close()

    return render_template("ai.html", answer=answer)


if __name__ == "__main__":

    init_db()

    import_csv_once()

    app.run(debug=True)

