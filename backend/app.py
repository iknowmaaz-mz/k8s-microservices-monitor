from flask import Flask, jsonify
import os
import psycopg2
from datetime import datetime
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

app = Flask(__name__)

REQUEST_COUNT = Counter("backend_requests_total", "Total requests", ["method", "endpoint"])
REQUEST_LATENCY = Histogram("backend_request_latency_seconds", "Request latency", ["endpoint"])

DB_HOST = os.getenv("DB_HOST", "postgres-service")
DB_NAME = os.getenv("DB_NAME", "appdb")
DB_USER = os.getenv("DB_USER", "appuser")
DB_PASS = os.getenv("DB_PASS", "apppassword")

def get_db():
    return psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS)

def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS visits (
            id SERIAL PRIMARY KEY,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    cur.close()
    conn.close()

@app.route("/api/visit", methods=["POST"])
@REQUEST_LATENCY.labels(endpoint="/api/visit").time()
def record_visit():
    REQUEST_COUNT.labels(method="POST", endpoint="/api/visit").inc()
    conn = get_db()
    cur = conn.cursor()
    cur.execute("INSERT INTO visits (timestamp) VALUES (%s)", (datetime.now(),))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"status": "recorded"}), 201

@app.route("/api/stats", methods=["GET"])
@REQUEST_LATENCY.labels(endpoint="/api/stats").time()
def get_stats():
    REQUEST_COUNT.labels(method="GET", endpoint="/api/stats").inc()
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM visits")
    count = cur.fetchone()[0]
    cur.execute("SELECT timestamp FROM visits ORDER BY id DESC LIMIT 5")
    recent = [row[0].strftime("%Y-%m-%d %H:%M:%S") for row in cur.fetchall()]
    cur.close()
    conn.close()
    return jsonify({"total_visits": count, "recent_visits": recent})

@app.route("/health")
def health():
    return jsonify({"status": "healthy"}), 200

@app.route("/metrics")
def metrics():
    return generate_latest(), 200, {"Content-Type": CONTENT_TYPE_LATEST}

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000)