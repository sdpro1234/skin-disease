import os
import sqlite3
import base64
from flask import Flask, render_template, request, redirect, session, jsonify
import google.generativeai as genai
from PIL import Image
from io import BytesIO

app = Flask(__name__)
app.secret_key = "super_secret_key"

# ==================================
# Gemini API Configuration
# ==================================

GEMINI_API_KEY = "AIzaSyCxwy1Ua89BIceGjL9pZLYJCs3XkwYZXik"
genai.configure(api_key=GEMINI_API_KEY)

model = genai.GenerativeModel("gemini-2.5-flash-lite")

# ==================================
# Database
# ==================================

def init_db():
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            email TEXT UNIQUE,
            password TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# ==================================
# Routes
# ==================================

@app.route("/")
def home():
    return redirect("/login")

# ---------------- Register ----------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not username or not email or not password:
            return "All fields are required", 400
        
        if password != confirm_password:
            return "Passwords do not match", 400

        conn = sqlite3.connect("users.db")
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
                           (username, email, password))
            conn.commit()
            return redirect("/login")
        except sqlite3.IntegrityError:
            return "Username or email already exists!", 400
        finally:
            conn.close()

    return render_template("register.html")

# ---------------- Login ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect("users.db")
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username=? AND password=?",
                       (username, password))
        user = cursor.fetchone()
        conn.close()

        if user:
            session["user"] = username
            return redirect("/dashboard")
        else:
            return "Invalid credentials"

    return render_template("login.html")

# ---------------- Dashboard ----------------
@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/login")
    return render_template("dashboard.html")

# ---------------- AI Prediction ----------------
@app.route("/predict", methods=["POST"])
def predict():
    if "user" not in session:
        return jsonify({"error": "Unauthorized"})

    data = request.json["image"]

    # Remove header
    image_data = data.split(",")[1]
    image_bytes = base64.b64decode(image_data)

    img = Image.open(BytesIO(image_bytes))

    prompt = """
    Analyze this skin image and provide:
    1. Disease Name
    2. Severity Level (Mild / Moderate / Severe)
    3. Health Recommendation
    4. Preventive Measures

    Give answer clearly structured.
    """

    response = model.generate_content([prompt, img])
    result = response.text

    return jsonify({"result": result})

# ---------------- Logout ----------------
@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect("/login")

# ---------------- Run ----------------
if __name__ == "__main__":
    app.run(debug=True, port=8000)
