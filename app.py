from flask import Flask, render_template
from flask_cors import CORS
import mysql.connector
from contextlib import contextmanager
import os
from dotenv import load_dotenv
import logging
from logging.handlers import RotatingFileHandler
import sys

# Load environment
load_dotenv()

# Flask app setup
app = Flask(__name__)
CORS(app)

# For session storage
app.secret_key = os.getenv("SECRET_KEY")

# Logging
logging.basicConfig(
    level=logging.INFO,
    handlers=[
        RotatingFileHandler("app.log", maxBytes=100000, backupCount=3),
        logging.StreamHandler(sys.stdout)
    ]
)

# Database config
db_config = {
    "host": os.getenv("DB_HOST"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME"),
}

@contextmanager
def get_db_connection():
    conn = None
    try:
        conn = mysql.connector.connect(**db_config)
        yield conn
    finally:
        if conn and conn.is_connected():
            conn.close()

@app.route("/")
def home():
    return render_template("home.html")


#Server entry point
if __name__ == "__main__":
    app.run(debug=True)
