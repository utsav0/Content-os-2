from flask import Flask, render_template, request, jsonify, session
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

# Page routes

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/posts")
def posts():
    return render_template("posts.html")


# API routes

# Search suggestions API
@app.route("/api/search-suggestions")
def search_suggestions():
    query = request.args.get("query", "")
    if not query:
        return jsonify({"topics": [], "posts": []})
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor(dictionary=True)

            # Search for topics
            cursor.execute("SELECT id, name FROM topics WHERE name LIKE %s", (f"%{query}%",))
            topics = cursor.fetchall()

            # Search for posts
            cursor.execute(
                "SELECT p.post_id, p.caption FROM posts p "
                "WHERE p.caption LIKE %s OR p.post_id LIKE %s",
                (f"%{query}%", f"%{query}%")
            )

            posts = cursor.fetchall()
            
            topics_suggestions = [{"id": topic['id'], "name": topic['name']} for topic in topics]
            posts_suggestions = [{"post_id": str(post['post_id']), "caption": post['caption']} for post in posts]

            return jsonify({
                "topics": topics_suggestions,
                "posts": posts_suggestions
            })
        
    except mysql.connector.Error as err:
        app.logger.error(f"Database error: {err}")
        return jsonify({"error": "Database error"}), 500

# Fetch posts for posts page
@app.route("/api/posts")
def api_posts():
    try:
        offset = int(request.args.get("offset", 0))
        limit = int(request.args.get("limit", 20))
        sort_by = request.args.get("sort_by", "post_datetime")
        sort_order = request.args.get("sort_order", "desc").upper()
        date_from = request.args.get("date_from")
        date_to = request.args.get("date_to")
        likes_min = request.args.get("likes_min")
        likes_max = request.args.get("likes_max")
        impressions_min = request.args.get("impressions_min")
        impressions_max = request.args.get("impressions_max")
        comments_min = request.args.get("comments_min")
        comments_max = request.args.get("comments_max")
        latest_date_from = request.args.get("latest_date_from")
        latest_date_to = request.args.get("latest_date_to")

        valid_sort_columns = ["post_datetime", "likes", "comments", "impressions", "main_ebook_ctr", "main_ebook_clicks", "latest_post_datetime"]
        if sort_by not in valid_sort_columns:
            sort_by = "post_datetime"
        if sort_order not in ["ASC", "DESC"]:
            sort_order = "DESC"

        query = """SELECT post_id, caption, impressions, likes, comments, post_datetime, main_ebook_ctr, main_ebook_clicks,
                   (SELECT MAX(p2.post_datetime) 
                    FROM posts p2 
                    JOIN topic_posts tp2 ON p2.post_id = tp2.post_id 
                    WHERE tp2.topic_id IN (
                        SELECT tp1.topic_id 
                        FROM topic_posts tp1 
                        WHERE tp1.post_id = posts.post_id
                    )) as latest_post_datetime
                   FROM posts WHERE 1=1"""
        params = []

        if date_from:
            query += " AND post_datetime >= %s"
            params.append(date_from)
        if date_to:
            query += " AND post_datetime <= %s"
            params.append(date_to)
        if likes_min:
            query += " AND likes >= %s"
            params.append(likes_min)
        if likes_max:
            query += " AND likes <= %s"
            params.append(likes_max)
        if impressions_min:
            query += " AND impressions >= %s"
            params.append(impressions_min)
        if impressions_max:
            query += " AND impressions <= %s"
            params.append(impressions_max)
        if comments_min:
            query += " AND comments >= %s"
            params.append(comments_min)
        if comments_max:
            query += " AND comments <= %s"
            params.append(comments_max)

        having_clauses = []
        if latest_date_from:
            having_clauses.append("latest_post_datetime >= %s")
            params.append(latest_date_from)
        if latest_date_to:
            having_clauses.append("latest_post_datetime <= %s")
            params.append(latest_date_to)

        if having_clauses:
            query += " HAVING " + " AND ".join(having_clauses)

        query += f" ORDER BY {sort_by} {sort_order} LIMIT %s OFFSET %s"
        params.extend([limit, offset])

        with get_db_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query, params)
            posts = cursor.fetchall()

            for post in posts:
                if "post_id" in post and post["post_id"] is not None:
                    post["post_id"] = str(post["post_id"])

                if post.get("post_datetime"):
                    post["post_datetime"] = post["post_datetime"].strftime("%d %B %Y")
                
                if post.get("latest_post_datetime"):
                    post["latest_post_datetime"] = post["latest_post_datetime"].strftime("%d %B %Y")
                else:
                    post["latest_post_datetime"] = "-"

            return jsonify(posts)

    except mysql.connector.Error as err:
        app.logger.error(f"Database error: {err}")
        return jsonify({"error": "Database error"}), 500

#Server entry point
if __name__ == "__main__":
    app.run(debug=True)