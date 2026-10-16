
from flask import Flask, render_template, request, redirect, url_for, jsonify
import requests
import sqlite3
from pathlib import Path

app = Flask(__name__)
DB_PATH = Path(__file__).with_name("jobs.db")


def connect_db():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    return db


def initialize_db():
    with connect_db() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                location TEXT NOT NULL,
                salary TEXT NOT NULL,
                employer TEXT NOT NULL,
                description TEXT NOT NULL
            )
        """)

        count = db.execute(
            "SELECT COUNT(*) FROM jobs"
        ).fetchone()[0]

        if count == 0:
            db.execute("""
                INSERT INTO jobs
                (title, location, salary, employer, description)
                VALUES (?, ?, ?, ?, ?)
            """, (
                "Electrician",
                "Hyderabad",
                "₹800 per day",
                "Demo Employer",
                "Electrical repair work. Contact employer to verify details."
            ))


@app.route("/")
def home():
    with connect_db() as db:
        jobs = db.execute(
            "SELECT * FROM jobs ORDER BY id DESC"
        ).fetchall()
    return render_template("index.html", jobs=jobs)


@app.route("/search")
def search():
    query = request.args.get("q", "").strip()

    with connect_db() as db:
        if query:
            pattern = f"%{query}%"
            jobs = db.execute("""
                SELECT * FROM jobs
                WHERE title LIKE ?
                   OR location LIKE ?
                   OR description LIKE ?
                ORDER BY id DESC
            """, (pattern, pattern, pattern)).fetchall()
        else:
            jobs = db.execute(
                "SELECT * FROM jobs ORDER BY id DESC"
            ).fetchall()

    return render_template("index.html", jobs=jobs)


@app.route("/post", methods=["POST"])
def post_job():
    fields = [
        request.form.get(name, "").strip()
        for name in ("title", "location", "salary", "employer", "description")
    ]

    if not all(fields):
        return "Please fill in every field.", 400

    with connect_db() as db:
        db.execute("""
            INSERT INTO jobs
            (title, location, salary, employer, description)
            VALUES (?, ?, ?, ?, ?)
        """, fields)

    return redirect(url_for("home"))


@app.route("/test-ai")
def test_ai():
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "gemma3:1b",
                "prompt": "Explain a voice-first job board in one sentence.",
                "stream": False
            },
            timeout=60
        )
        response.raise_for_status()
        return jsonify({"answer": response.json()["response"]})
    except requests.RequestException:
        return jsonify({"error": "Could not connect to Ollama."}), 503
@app.route("/ai-search")
def ai_search():
    user_query = request.args.get("q", "").strip()
    if not user_query:
        return jsonify({"error": "Please enter a job search."}), 400

    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "gemma3:1b",
                "prompt": (
                    "Extract the job title and location from the user's job request. "
                    "The request may be in Telugu, Hindi, or English. "
                    "Return only two lines in English:\n"
                    "Job: <job title>\n"
                    "Location: <location or Unknown>\n"
                    f"User request: {user_query}"
                ),
                "stream": False
            },
            timeout=60
        )
        response.raise_for_status()
        answer = response.json().get("response", "")
        return jsonify({"query": user_query, "ai_result": answer})

    except requests.RequestException:
        return jsonify({"error": "Could not connect to Ollama. Check that Ollama is running."}), 503
initialize_db()

if __name__ == "__main__":
    app.run(debug=True)