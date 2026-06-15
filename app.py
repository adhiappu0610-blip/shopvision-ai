from flask import Flask, render_template, request, redirect, session, send_file
import sqlite3
import os
import csv
from datetime import datetime

app = Flask(__name__)
app.secret_key = "shopvision_ai_secret_key"

DATABASE = "shopvision.db"


# ---------------- DATABASE CONNECTION ----------------

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


# ---------------- CREATE TABLES ----------------

def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        password TEXT NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product TEXT NOT NULL,
        category TEXT,
        price REAL DEFAULT 0,
        cost REAL DEFAULT 0,
        stock INTEGER DEFAULT 0,
        sold INTEGER DEFAULT 0,
        branch TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS bills (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer TEXT,
        phone TEXT,
        total REAL,
        gst REAL,
        grand_total REAL,
        created_at TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        amount REAL,
        created_at TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS chat_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        question TEXT,
        answer TEXT,
        created_at TEXT
    )
    """)

    conn.commit()
    conn.close()


init_db()


# ---------------- LOGIN CHECK ----------------

def login_required():
    return "user" in session


# ---------------- LANDING ----------------

@app.route("/")
def landing():
    return render_template("landing.html")


# ---------------- REGISTER ----------------

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db()
        cur = conn.cursor()

        cur.execute(
            "INSERT INTO users(username, password) VALUES (?, ?)",
            (username, password)
        )

        conn.commit()
        conn.close()

        return redirect("/login")

    return render_template("register.html")


# ---------------- LOGIN ----------------

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db()
        cur = conn.cursor()

        cur.execute(
            "SELECT * FROM users WHERE username=? AND password=?",
            (username, password)
        )

        user = cur.fetchone()
        conn.close()

        if user:
            session["user"] = username
            return redirect("/dashboard")

        return render_template("login.html", error="Invalid username or password")

    return render_template("login.html")


# ---------------- DASHBOARD ----------------

@app.route("/dashboard")
def dashboard():
    if not login_required():
        return redirect("/login")

    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM products")
    total_products = cur.fetchone()[0]

    cur.execute("SELECT SUM(price * sold) FROM products")
    total_sales = cur.fetchone()[0] or 0

    cur.execute("SELECT SUM((price - cost) * sold) FROM products")
    gross_profit = cur.fetchone()[0] or 0

    cur.execute("SELECT SUM(amount) FROM expenses")
    expenses = cur.fetchone()[0] or 0

    net_profit = gross_profit - expenses

    cur.execute("SELECT COUNT(*) FROM products WHERE stock <= 5")
    low_stock = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM products WHERE sold = 0")
    dead_stock = cur.fetchone()[0]

    cur.execute("SELECT product FROM products ORDER BY sold DESC LIMIT 1")
    best = cur.fetchone()
    best_product = best["product"] if best else "No data"

    cur.execute("SELECT product, sold FROM products ORDER BY sold DESC LIMIT 6")
    chart_data = cur.fetchall()

    conn.close()

    return render_template(
        "dashboard.html",
        total_products=total_products,
        total_sales=total_sales,
        gross_profit=gross_profit,
        expenses=expenses,
        net_profit=net_profit,
        low_stock=low_stock,
        dead_stock=dead_stock,
        best_product=best_product,
        chart_data=chart_data
    )


# ---------------- INVENTORY ----------------

@app.route("/inventory", methods=["GET", "POST"])
def inventory():
    if not login_required():
        return redirect("/login")

    conn = get_db()
    cur = conn.cursor()

    if request.method == "POST":
        product = request.form["product"]
        category = request.form["category"]
        price = float(request.form["price"])
        cost = float(request.form["cost"])
        stock = int(request.form["stock"])
        branch = request.form["branch"]

        cur.execute("""
        INSERT INTO products(product, category, price, cost, stock, sold, branch)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (product, category, price, cost, stock, 0, branch))

        conn.commit()
        return redirect("/inventory")

    cur.execute("SELECT * FROM products")
    products = cur.fetchall()

    conn.close()

    return render_template("inventory.html", products=products)


# ---------------- BILLING ----------------

@app.route("/billing", methods=["GET", "POST"])
def billing():
    if not login_required():
        return redirect("/login")

    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM products")
    products = cur.fetchall()

    if request.method == "POST":
        customer = request.form["customer"]
        phone = request.form["phone"]
        product_id = request.form["product_id"]
        qty = int(request.form["qty"])

        cur.execute("SELECT * FROM products WHERE id=?", (product_id,))
        product = cur.fetchone()

        if product and product["stock"] >= qty:
            total = product["price"] * qty
            gst = total * 0.05
            grand_total = total + gst

            cur.execute("""
            INSERT INTO bills(customer, phone, total, gst, grand_total, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (
                customer,
                phone,
                total,
                gst,
                grand_total,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ))

            cur.execute("""
            UPDATE products
            SET stock = stock - ?, sold = sold + ?
            WHERE id=?
            """, (qty, qty, product_id))

            conn.commit()
            conn.close()

            return redirect("/reports")

    conn.close()

    return render_template("billing.html", products=products)


# ---------------- ANALYTICS ----------------

@app.route("/analytics")
def analytics():
    if not login_required():
        return redirect("/login")

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
    SELECT product, category, price, cost, stock, sold,
    (price * sold) AS sales,
    ((price - cost) * sold) AS profit
    FROM products
    ORDER BY sold DESC
    """)

    analytics_data = cur.fetchall()
    conn.close()

    return render_template("analytics.html", analytics_data=analytics_data)


# ---------------- REPORTS ----------------

@app.route("/reports")
def reports():
    if not login_required():
        return redirect("/login")

    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM bills ORDER BY id DESC")
    bills = cur.fetchall()

    conn.close()

    return render_template("reports.html", bills=bills)


# ---------------- EXPORT CSV ----------------

@app.route("/export_bills")
def export_bills():
    if not login_required():
        return redirect("/login")

    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM bills")
    bills = cur.fetchall()

    filename = "bills_export.csv"

    with open(filename, "w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["ID", "Customer", "Phone", "Total", "GST", "Grand Total", "Date"])

        for bill in bills:
            writer.writerow([
                bill["id"],
                bill["customer"],
                bill["phone"],
                bill["total"],
                bill["gst"],
                bill["grand_total"],
                bill["created_at"]
            ])

    conn.close()

    return send_file(filename, as_attachment=True)


# ---------------- AI ASSISTANT ----------------

@app.route("/ai", methods=["GET", "POST"])
def ai():
    if not login_required():
        return redirect("/login")

    answer = None

    if request.method == "POST":
        question = request.form["question"]

        conn = get_db()
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) FROM products")
        total_products = cur.fetchone()[0]

        cur.execute("SELECT SUM(price * sold) FROM products")
        total_sales = cur.fetchone()[0] or 0

        cur.execute("SELECT SUM((price - cost) * sold) FROM products")
        profit = cur.fetchone()[0] or 0

        cur.execute("SELECT product FROM products ORDER BY sold DESC LIMIT 1")
        best = cur.fetchone()
        best_product = best["product"] if best else "No product data"

        answer = f"""
        Business Summary:
        Total Products: {total_products}
        Total Sales: ₹{total_sales}
        Gross Profit: ₹{profit}
        Best Selling Product: {best_product}

        AI Suggestion:
        Focus on best-selling products, reduce dead stock, and restock low quantity items.
        """

        cur.execute("""
        INSERT INTO chat_history(question, answer, created_at)
        VALUES (?, ?, ?)
        """, (
            question,
            answer,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))

        conn.commit()
        conn.close()

    return render_template("ai.html", answer=answer)


# ---------------- LOGOUT ----------------

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# ---------------- RUN ----------------

if __name__ == "__main__":
    app.run(debug=True)
