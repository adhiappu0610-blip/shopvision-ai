from flask import Flask, render_template, request, redirect, session, flash, make_response
import sqlite3
import csv
import os
from datetime import datetime
from io import StringIO

import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression

app = Flask(__name__)
app.secret_key = "shopvision_ai_secret_key"

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
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS products(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product TEXT NOT NULL,
        category TEXT,
        price REAL DEFAULT 0,
        cost REAL DEFAULT 0,
        stock INTEGER DEFAULT 0,
        sold INTEGER DEFAULT 0,
        branch TEXT DEFAULT 'Main'
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS bills(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer TEXT,
        phone TEXT,
        subtotal REAL,
        gst REAL,
        grand_total REAL,
        payment_method TEXT,
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


def check_login():
    return "user_id" in session


def money(value):
    return f"{float(value or 0):,.2f}"


app.jinja_env.filters["money"] = money


def predict_future_sales():
    try:
        conn = db()
        df = pd.read_sql_query("SELECT sold FROM products ORDER BY id", conn)
        conn.close()

        if len(df) < 2:
            return 0

        X = np.array(range(len(df))).reshape(-1, 1)
        y = df["sold"]

        model = LinearRegression()
        model.fit(X, y)

        future = model.predict([[len(df) + 1]])
        return round(float(future[0]), 2)

    except:
        return 0


def get_stats():
    conn = db()
    cur = conn.cursor()

    cur.execute("SELECT SUM(price * sold) FROM products")
    total_sales = cur.fetchone()[0] or 0

    cur.execute("SELECT SUM((price - cost) * sold) FROM products")
    gross_profit = cur.fetchone()[0] or 0

    cur.execute("SELECT SUM(amount) FROM expenses")
    expenses = cur.fetchone()[0] or 0

    cur.execute("SELECT COUNT(*) FROM products")
    products_count = cur.fetchone()[0] or 0

    cur.execute("SELECT COUNT(*) FROM products WHERE stock <= 10")
    low_stock = cur.fetchone()[0] or 0

    cur.execute("SELECT COUNT(*) FROM products WHERE sold = 0")
    dead_stock = cur.fetchone()[0] or 0

    cur.execute("SELECT COUNT(*) FROM bills")
    bills_count = cur.fetchone()[0] or 0

    cur.execute("SELECT COUNT(*) FROM customers")
    customers_count = cur.fetchone()[0] or 0

    cur.execute("SELECT product FROM products ORDER BY sold DESC LIMIT 1")
    best = cur.fetchone()
    best_product = best["product"] if best else "No Data"

    conn.close()

    return {
        "total_sales": total_sales,
        "gross_profit": gross_profit,
        "expenses": expenses,
        "net_profit": gross_profit - expenses,
        "products_count": products_count,
        "low_stock": low_stock,
        "dead_stock": dead_stock,
        "bills_count": bills_count,
        "customers_count": customers_count,
        "best_product": best_product
    }


@app.route("/")
def home():
    if check_login():
        return redirect("/dashboard")
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]

        conn = db()
        cur = conn.cursor()

        try:
            cur.execute(
                "INSERT INTO users(name,email,password) VALUES(?,?,?)",
                (name, email, password)
            )
            conn.commit()
            flash("Registration successful. Please login.", "success")
            return redirect("/login")

        except:
            flash("Email already exists.", "danger")

        finally:
            conn.close()

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = db()
        cur = conn.cursor()

        cur.execute(
            "SELECT * FROM users WHERE email=? AND password=?",
            (email, password)
        )

        user = cur.fetchone()
        conn.close()

        if user:
            session["user_id"] = user["id"]
            session["name"] = user["name"]
            session["cart"] = []
            return redirect("/dashboard")

        flash("Invalid email or password.", "danger")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully.", "success")
    return redirect("/")


@app.route("/dashboard")
def dashboard():
    if not check_login():
        return redirect("/login")

    stats = get_stats()
    future_sales = predict_future_sales()

    conn = db()
    cur = conn.cursor()

    cur.execute("SELECT product, sold FROM products ORDER BY sold DESC LIMIT 6")
    chart_data = cur.fetchall()

    cur.execute("SELECT * FROM products WHERE stock <= 10 ORDER BY stock ASC LIMIT 6")
    low_stock_items = cur.fetchall()

    cur.execute("SELECT * FROM bills ORDER BY id DESC LIMIT 5")
    recent_bills = cur.fetchall()

    conn.close()

    labels = [r["product"] for r in chart_data]
    values = [r["sold"] for r in chart_data]

    return render_template(
        "dashboard.html",
        stats=stats,
        future_sales=future_sales,
        labels=labels,
        values=values,
        low_stock_items=low_stock_items,
        recent_bills=recent_bills
    )


@app.route("/inventory")
def inventory():
    if not check_login():
        return redirect("/login")

    search = request.args.get("search", "")

    conn = db()
    cur = conn.cursor()

    if search:
        cur.execute("""
        SELECT * FROM products
        WHERE product LIKE ? OR category LIKE ? OR branch LIKE ?
        ORDER BY stock ASC
        """, (f"%{search}%", f"%{search}%", f"%{search}%"))
    else:
        cur.execute("SELECT * FROM products ORDER BY stock ASC")

    products = cur.fetchall()
    conn.close()

    return render_template("inventory.html", products=products, search=search)


@app.route("/add_product", methods=["POST"])
def add_product():
    if not check_login():
        return redirect("/login")

    conn = db()
    cur = conn.cursor()

    cur.execute("""
    INSERT INTO products(product, category, price, cost, stock, sold, branch)
    VALUES(?,?,?,?,?,?,?)
    """, (
        request.form["product"],
        request.form["category"],
        float(request.form["price"]),
        float(request.form["cost"]),
        int(request.form["stock"]),
        int(request.form.get("sold", 0)),
        request.form.get("branch", "Main")
    ))

    conn.commit()
    conn.close()

    flash("Product added successfully.", "success")
    return redirect("/inventory")


@app.route("/update_product/<int:product_id>", methods=["POST"])
def update_product(product_id):
    if not check_login():
        return redirect("/login")

    conn = db()
    cur = conn.cursor()

    cur.execute("""
    UPDATE products
    SET product=?, category=?, price=?, cost=?, stock=?, sold=?, branch=?
    WHERE id=?
    """, (
        request.form["product"],
        request.form["category"],
        float(request.form["price"]),
        float(request.form["cost"]),
        int(request.form["stock"]),
        int(request.form["sold"]),
        request.form["branch"],
        product_id
    ))

    conn.commit()
    conn.close()

    flash("Product updated successfully.", "success")
    return redirect("/inventory")


@app.route("/delete_product/<int:product_id>")
def delete_product(product_id):
    if not check_login():
        return redirect("/login")

    conn = db()
    cur = conn.cursor()

    cur.execute("DELETE FROM products WHERE id=?", (product_id,))

    conn.commit()
    conn.close()

    flash("Product deleted successfully.", "success")
    return redirect("/inventory")


@app.route("/billing")
def billing():
    if not check_login():
        return redirect("/login")

    conn = db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM products ORDER BY product ASC")
    products = cur.fetchall()

    conn.close()

    cart = session.get("cart", [])

    subtotal = sum(item["total"] for item in cart)
    gst = round(subtotal * 0.05, 2)
    grand_total = round(subtotal + gst, 2)

    return render_template(
        "billing.html",
        products=products,
        cart=cart,
        subtotal=round(subtotal, 2),
        gst=gst,
        grand_total=grand_total
    )


@app.route("/add_to_bill", methods=["POST"])
def add_to_bill():
    if not check_login():
        return redirect("/login")

    product_id = request.form["product_id"]
    qty = int(request.form["qty"])

    conn = db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM products WHERE id=?", (product_id,))
    product = cur.fetchone()

    conn.close()

    if not product:
        flash("Invalid product.", "danger")
        return redirect("/billing")

    if qty <= 0:
        flash("Quantity must be greater than zero.", "danger")
        return redirect("/billing")

    if product["stock"] < qty:
        flash(f"Only {product['stock']} stock available for {product['product']}.", "danger")
        return redirect("/billing")

    cart = session.get("cart", [])

    already_qty = 0
    for item in cart:
        if item["product_id"] == product["id"]:
            already_qty += item["qty"]

    if already_qty + qty > product["stock"]:
        flash(f"Stock limit exceeded for {product['product']}.", "danger")
        return redirect("/billing")

    found = False

    for item in cart:
        if item["product_id"] == product["id"]:
            item["qty"] += qty
            item["total"] = round(item["qty"] * item["price"], 2)
            found = True
            break

    if not found:
        cart.append({
            "product_id": product["id"],
            "product": product["product"],
            "qty": qty,
            "price": product["price"],
            "total": round(product["price"] * qty, 2)
        })

    session["cart"] = cart
    session.modified = True

    flash("Product added to bill.", "success")
    return redirect("/billing")


@app.route("/remove_bill_item/<int:index>")
def remove_bill_item(index):
    if not check_login():
        return redirect("/login")

    cart = session.get("cart", [])

    if 0 <= index < len(cart):
        cart.pop(index)
        session["cart"] = cart
        session.modified = True
        flash("Product removed.", "success")

    return redirect("/billing")


@app.route("/clear_bill")
def clear_bill():
    if not check_login():
        return redirect("/login")

    session["cart"] = []
    session.modified = True

    flash("Bill cleared.", "success")
    return redirect("/billing")


@app.route("/generate_bill", methods=["POST"])
def generate_bill():
    if not check_login():
        return redirect("/login")

    cart = session.get("cart", [])

    if not cart:
        flash("Please add at least one product.", "danger")
        return redirect("/billing")

    customer = request.form["customer"]
    phone = request.form.get("phone", "")
    payment_method = request.form.get("payment_method", "Cash")

    subtotal = sum(item["total"] for item in cart)
    gst = round(subtotal * 0.05, 2)
    grand_total = round(subtotal + gst, 2)
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = db()
    cur = conn.cursor()

    for item in cart:
        cur.execute("SELECT stock FROM products WHERE id=?", (item["product_id"],))
        stock = cur.fetchone()["stock"]

        if stock < item["qty"]:
            conn.close()
            flash(f"Not enough stock for {item['product']}.", "danger")
            return redirect("/billing")

    cur.execute("""
    INSERT INTO bills(customer, phone, subtotal, gst, grand_total, payment_method, created_at)
    VALUES(?,?,?,?,?,?,?)
    """, (
        customer,
        phone,
        subtotal,
        gst,
        grand_total,
        payment_method,
        created_at
    ))

    bill_id = cur.lastrowid

    for item in cart:
        cur.execute("""
        INSERT INTO bill_items(bill_id, product_id, product, qty, price, total)
        VALUES(?,?,?,?,?,?)
        """, (
            bill_id,
            item["product_id"],
            item["product"],
            item["qty"],
            item["price"],
            item["total"]
        ))

        cur.execute("""
        UPDATE products
        SET stock = stock - ?, sold = sold + ?
        WHERE id=?
        """, (
            item["qty"],
            item["qty"],
            item["product_id"]
        ))

    cur.execute("""
    INSERT INTO customers(name, phone, created_at)
    VALUES(?,?,?)
    """, (
        customer,
        phone,
        created_at
    ))

    conn.commit()
    conn.close()

    session["cart"] = []
    session.modified = True

    flash("Bill generated successfully.", "success")
    return redirect(f"/invoice/{bill_id}")


@app.route("/invoice/<int:bill_id>")
def invoice(bill_id):
    if not check_login():
        return redirect("/login")

    conn = db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM bills WHERE id=?", (bill_id,))
    bill = cur.fetchone()

    cur.execute("SELECT * FROM bill_items WHERE bill_id=?", (bill_id,))
    items = cur.fetchall()

    conn.close()

    if not bill:
        flash("Invoice not found.", "danger")
        return redirect("/reports")

    return render_template("invoice.html", bill=bill, items=items)


@app.route("/analytics")
def analytics():
    if not check_login():
        return redirect("/login")

    stats = get_stats()

    conn = db()
    cur = conn.cursor()

    cur.execute("""
    SELECT *,
    ROUND((price-cost),2) AS profit_per_unit,
    ROUND((price-cost)*sold,2) AS total_profit
    FROM products
    ORDER BY sold DESC
    """)
    products = cur.fetchall()

    cur.execute("""
    SELECT category, SUM(price*sold) AS sales, SUM((price-cost)*sold) AS profit
    FROM products
    GROUP BY category
    ORDER BY sales DESC
    """)
    category_rows = cur.fetchall()

    conn.close()

    labels = [r["category"] for r in category_rows]
    sales = [round(r["sales"] or 0, 2) for r in category_rows]
    profit = [round(r["profit"] or 0, 2) for r in category_rows]

    return render_template(
        "analytics.html",
        products=products,
        stats=stats,
        labels=labels,
        sales=sales,
        profit=profit
    )


@app.route("/reports")
def reports():
    if not check_login():
        return redirect("/login")

    conn = db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM bills ORDER BY id DESC")
    bills = cur.fetchall()

    cur.execute("""
    SELECT strftime('%Y-%m', created_at) AS month, SUM(grand_total) AS total
    FROM bills
    GROUP BY month
    ORDER BY month DESC
    """)
    monthly = cur.fetchall()

    conn.close()

    return render_template("reports.html", bills=bills, monthly=monthly)


@app.route("/export_bills")
def export_bills():
    if not check_login():
        return redirect("/login")

    conn = db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM bills ORDER BY id DESC")
    bills = cur.fetchall()

    conn.close()

    output = StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "Bill ID", "Customer", "Phone", "Subtotal",
        "GST", "Grand Total", "Payment", "Date"
    ])

    for b in bills:
        writer.writerow([
            b["id"],
            b["customer"],
            b["phone"],
            b["subtotal"],
            b["gst"],
            b["grand_total"],
            b["payment_method"],
            b["created_at"]
        ])

    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = "attachment; filename=bills_report.csv"
    response.headers["Content-Type"] = "text/csv"

    return response


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
        q = question.lower()

        matched = None

        for p in products:
            if p["product"].lower() in q:
                matched = p
                break

        if matched:
            p = matched
            profit_per_unit = round(p["price"] - p["cost"], 2)
            total_profit = round((p["price"] - p["cost"]) * p["sold"], 2)

            if "stock" in q:
                answer = f"{p['product']} stock is {p['stock']} units."
            elif "price" in q:
                answer = f"{p['product']} price is ₹{p['price']}."
            elif "profit" in q:
                answer = f"{p['product']} profit per unit is ₹{profit_per_unit}. Total profit is ₹{total_profit}."
            elif "predict" in q:
                answer = f"{p['product']} next month predicted sales may reach {int(p['sold'] * 1.15)} units."
            else:
                answer = f"{p['product']} details: price ₹{p['price']}, stock {p['stock']}, sold {p['sold']}."

        elif "best" in q:
            if products:
                best = max(products, key=lambda x: x["sold"])
                answer = f"Best selling product is {best['product']} with {best['sold']} units sold."
            else:
                answer = "No product data."

        elif "low stock" in q:
            low = [p for p in products if p["stock"] <= 10]
            answer = ", ".join([p["product"] for p in low]) if low else "No low stock items."

        elif "forecast" in q or "ml" in q:
            answer = f"ML Linear Regression forecast: future sales may reach {predict_future_sales()} units."

        else:
            answer = "Ask like: stock of milk, price of rice, profit of oil, best selling product, low stock items, sales forecast."

        cur.execute("""
        INSERT INTO chat_history(question, answer, created_at)
        VALUES(?,?,?)
        """, (
            question,
            answer,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))

        conn.commit()

    cur.execute("SELECT * FROM chat_history ORDER BY id DESC LIMIT 5")
    history = cur.fetchall()

    conn.close()

    return render_template("ai.html", answer=answer, history=history)


init_db()
import_csv_once()

if __name__ == "__main__":
    app.run(debug=True)
