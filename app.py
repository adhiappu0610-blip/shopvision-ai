from flask import Flask, render_template, request, redirect, session, url_for
import sqlite3
import os

app = Flask(__name__)
app.secret_key = "shopvision_secret_key"

DATABASE = "shopvision.db"


# =========================
# DATABASE
# =========================

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        password TEXT
    )
    """)

    conn.commit()
    conn.close()


init_db()


# =========================
# LANDING PAGE
# =========================

@app.route("/")
def landing():
    return render_template("landing.html")


# =========================
# REGISTER
# =========================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        conn = get_db()
        cur = conn.cursor()

        cur.execute(
            "INSERT INTO users(username,password) VALUES(?,?)",
            (username, password)
        )

        conn.commit()
        conn.close()

        return redirect("/login")

    return render_template("register.html")


# =========================
# LOGIN
# =========================

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

        else:
            return render_template(
                "login.html",
                error="Invalid Username or Password"
            )

    return render_template("login.html")


# =========================
# DASHBOARD
# =========================

@app.route("/dashboard")
def dashboard():

    if "user" not in session:
        return redirect("/login")

    return render_template("dashboard.html")


# =========================
# INVENTORY
# =========================

@app.route("/inventory")
def inventory():

    if "user" not in session:
        return redirect("/login")

    return render_template("inventory.html")


# =========================
# BILLING
# =========================

@app.route("/billing")
def billing():

    if "user" not in session:
        return redirect("/login")

    return render_template("billing.html")


# =========================
# ANALYTICS
# =========================

@app.route("/analytics")
def analytics():

    if "user" not in session:
        return redirect("/login")

    return render_template("analytics.html")


# =========================
# REPORTS
# =========================

@app.route("/reports")
def reports():

    if "user" not in session:
        return redirect("/login")

    return render_template("reports.html")


# =========================
# AI ASSISTANT
# =========================

@app.route("/ai")
def ai():

    if "user" not in session:
        return redirect("/login")

    return render_template("ai.html")


# =========================
# LOGOUT
# =========================

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")


# =========================
# RUN APP
# =========================

if __name__ == "__main__":
    app.run(debug=True)
