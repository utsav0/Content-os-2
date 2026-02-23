from flask import Flask, current_app, flash, render_template, request, jsonify, session, redirect, url_for, send_file, after_this_request
from flask_cors import CORS
import mysql.connector
from contextlib import contextmanager
import os
from dotenv import load_dotenv
import logging
from logging.handlers import RotatingFileHandler
import sys
import statistics
import file_handler
import ask_ai
import subprocess
from werkzeug.utils import secure_filename
import threading


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

read_only_db_config = {
    "host": os.getenv("DB_HOST"),
    "user": os.getenv("READ_ONLY_DB_USER"),
    "password": os.getenv("READ_ONLY_DB_PASSWORD"),
    "database": os.getenv("DB_NAME"),
}

@contextmanager
def get_read_only_db_connection():
    conn = None
    try:
        conn = mysql.connector.connect(**read_only_db_config)
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

@app.route("/topics")
def topics_list():
    return render_template("topics.html")

# Individual post details page
@app.route("/post/<int:post_id>")
def show_post_details(post_id):
    app.logger.info(f"Request received for post ID: {post_id}")
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            
            # Fetch the main post
            cursor.execute("SELECT * FROM posts WHERE post_id = %s", (post_id,))
            post = cursor.fetchone()

            if not post:
                return "Post not found", 404

            if post and post.get('post_datetime'):
                post['post_datetime'] = post['post_datetime'].strftime('%d %B %Y')

            # Fetch topics for the current post
            cursor.execute("""
                SELECT t.id, t.name
                FROM topics t
                JOIN topic_posts tp ON t.id = tp.topic_id
                WHERE tp.post_id = %s
            """, (post_id,))
            topics = cursor.fetchall()

            # Fetch similar posts
            cursor.execute("""
                SELECT p.post_id, p.media_url, p.caption, p.impressions, p.likes, p.comments, p.reposts
                FROM posts p
                JOIN topic_posts tp ON p.post_id = tp.post_id
                WHERE tp.topic_id IN (
                    SELECT topic_id FROM topic_posts WHERE post_id = %s
                ) AND p.post_id != %s
                GROUP BY p.post_id
                ORDER BY p.post_datetime DESC
                LIMIT 10
            """, (post_id, post_id))
            similar_posts = cursor.fetchall()

            # Fetch the most recent post date among similar posts
            most_recent_post_info = None
            if similar_posts:
                cursor.execute("""
                    SELECT p.post_id, p.post_datetime
                    FROM posts p
                    JOIN topic_posts tp ON p.post_id = tp.post_id
                    WHERE tp.topic_id IN (
                        SELECT topic_id FROM topic_posts WHERE post_id = %s
                    )
                    ORDER BY p.post_datetime DESC
                    LIMIT 1
                """, (post_id,))
                most_recent_post_info = cursor.fetchone()
                if most_recent_post_info and most_recent_post_info.get('post_datetime'):
                    most_recent_post_info['post_datetime'] = most_recent_post_info['post_datetime'].strftime('%d %B %Y')

            return render_template('individual_post.html', post=post, topics=topics, similar_posts=similar_posts, most_recent_post_info=most_recent_post_info)

    except mysql.connector.Error as err:
        app.logger.error(f"Database error: {err}")
        return "Database error", 500

@app.route("/add-post", methods=['GET', 'POST'])
def add_post():
    error = None
    if request.method == 'POST':
        files = request.files.getlist('file-upload')
        if not files or not files[0].filename:
            error = "No file selected."
        else:
            try:
                upload_folder = os.path.join(app.root_path, 'temp_uploads', 'user_uploads')
                os.makedirs(upload_folder, exist_ok=True)

                post_files_queue = []

                for file in files:
                    if file.filename:
                        filename = secure_filename(file.filename)
                        save_path = os.path.join(upload_folder, filename)
                        file.save(save_path)
                        post_files_queue.append(filename)

                session['post_files_queue'] = post_files_queue
                session.modified = True
                
                return redirect(url_for('confirm_upload_post'))

            except Exception as e:
                app.logger.error(f"Error saving files: {e}")
                error = "An error occurred while saving your files."
    return render_template("add_post.html", error=error)

@app.route("/confirm-upload-post", methods=['GET'])
def confirm_upload_post():
    post_files_queue = session.get('post_files_queue', [])

    if not post_files_queue:
        flash("All files processed! Upload more?")
        return redirect(url_for('add_post'))

    current_filename = post_files_queue[0]
    upload_folder = os.path.join(app.root_path, 'temp_uploads', 'user_uploads')
    file_path = os.path.join(upload_folder, current_filename)

    if not os.path.exists(file_path):
        post_files_queue.pop(0)
        session['post_files_queue'] = post_files_queue
        session.modified = True
        return redirect(url_for('confirm_upload_post'))

    try:
        parsed_data = file_handler.handle_file(file_path)
    except Exception as e:
        app.logger.error(f"Error parsing file: {e}")
        parsed_data = {"error": "Could not parse file data"}

    return render_template(
        "confirm_upload_post.html", 
        filename=current_filename, 
        parsed_data=parsed_data,
        queue_count=len(post_files_queue)
    )

@app.route("/video-to-gif", methods=['GET', 'POST'])
def video_to_gif_page():
    if request.method == 'POST':
        if 'file' not in request.files:
            return render_template('video_to_gif.html', error='No file part')
        
        file = request.files['file']
        if file.filename == '':
            return render_template('video_to_gif.html', error='No selected file')

        if file:
            try:
                filename = secure_filename(file.filename)
                # Create a temporary directory if it doesn't exist
                temp_dir = os.path.join(app.root_path, 'temp_uploads')
                os.makedirs(temp_dir, exist_ok=True)
                
                input_path = os.path.join(temp_dir, filename)
                file.save(input_path)

                base_name = os.path.splitext(input_path)[0]
                palette_path = f"{base_name}_palette.png"
                output_gif_path = f"{base_name}.gif"

                # Step 1: Generate optimal palette
                palette_cmd = [
                    "ffmpeg", "-y", "-i", input_path,
                    "-vf", "fps=15,scale=iw:ih:flags=lanczos,palettegen=stats_mode=full",
                    palette_path
                ]

                # Step 2: Create GIF using palette
                gif_cmd = [
                    "ffmpeg", "-y", "-i", input_path, "-i", palette_path,
                    "-filter_complex", "fps=15,scale=iw:ih:flags=lanczos[x];[x][1:v]paletteuse=dither=sierra2_4a",
                    output_gif_path
                ]

                subprocess.run(palette_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                subprocess.run(gif_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

                # Schedule cleanup of files after the response is sent
                @after_this_request
                def cleanup(response):
                    try:
                        if os.path.exists(input_path): os.remove(input_path)
                        if os.path.exists(palette_path): os.remove(palette_path)
                        if os.path.exists(output_gif_path): os.remove(output_gif_path)
                    except Exception as e:
                        app.logger.error(f"Error cleaning up temp files: {e}")
                    return response

                return send_file(
                    output_gif_path, 
                    as_attachment=True, 
                    download_name=f"{os.path.splitext(filename)[0]}.gif",
                    mimetype='image/gif'
                )

            except subprocess.CalledProcessError:
                app.logger.error("FFmpeg failed to convert video")
                return render_template('video_to_gif.html', error="Error processing video. Please ensure FFmpeg is installed and the video file is valid.")
            except Exception as e:
                app.logger.error(f"Unexpected error: {e}")
                return render_template('video_to_gif.html', error=f"An error occurred: {str(e)}")

    return render_template('video_to_gif.html')

@app.route("/ask-ai", methods=['GET'])
def ask_ai_page():
    return render_template("ask_ai.html")

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

@app.route("/api/topics-list")
def api_topics_list():
    try:
        offset = int(request.args.get("offset", 0))
        limit = int(request.args.get("limit", 20))
        sort_by = request.args.get("sort_by", "last_posted")
        sort_order = request.args.get("sort_order", "desc").upper()

        impressions_min = request.args.get("impressions_min")
        impressions_max = request.args.get("impressions_max")
        likes_min = request.args.get("likes_min")
        likes_max = request.args.get("likes_max")
        comments_min = request.args.get("comments_min")
        comments_max = request.args.get("comments_max")
        date_from = request.args.get("date_from")
        date_to = request.args.get("date_to")

        valid_sort_columns = ["post_count", "median_impressions", "median_likes", "median_comments", "last_posted"]
        if sort_by not in valid_sort_columns:
            sort_by = "last_posted"
        if sort_order not in ["ASC", "DESC"]:
            sort_order = "DESC"

        with get_db_connection() as conn:
            cursor = conn.cursor(dictionary=True)

            query = """
                SELECT
                    t.id,
                    t.name,
                    COUNT(p.post_id) AS post_count,
                    MAX(p.post_datetime) AS last_posted,
                    GROUP_CONCAT(p.impressions ORDER BY p.impressions) AS all_impressions,
                    GROUP_CONCAT(p.likes ORDER BY p.likes) AS all_likes,
                    GROUP_CONCAT(p.comments ORDER BY p.comments) AS all_comments
                FROM topics t
                JOIN topic_posts tp ON t.id = tp.topic_id
                JOIN posts p ON tp.post_id = p.post_id
                GROUP BY t.id, t.name
            """

            cursor.execute(query)
            rows = cursor.fetchall()

            def median_from_csv(csv_str):
                if not csv_str:
                    return None
                vals = [int(v) for v in csv_str.split(',') if v]
                n = len(vals)
                if n == 0:
                    return None
                mid = n // 2
                if n % 2 == 0:
                    return (vals[mid - 1] + vals[mid]) / 2
                return vals[mid]

            topics = []
            for row in rows:
                topic = {
                    'id': row['id'],
                    'name': row['name'],
                    'post_count': row['post_count'],
                    'last_posted': row['last_posted'].strftime('%d %B %Y') if row['last_posted'] else None,
                    'last_posted_raw': row['last_posted'],
                    'median_impressions': median_from_csv(row['all_impressions']),
                    'median_likes': median_from_csv(row['all_likes']),
                    'median_comments': median_from_csv(row['all_comments'])
                }
                topics.append(topic)

            if impressions_min:
                topics = [t for t in topics if t['median_impressions'] is not None and t['median_impressions'] >= float(impressions_min)]
            if impressions_max:
                topics = [t for t in topics if t['median_impressions'] is not None and t['median_impressions'] <= float(impressions_max)]
            if likes_min:
                topics = [t for t in topics if t['median_likes'] is not None and t['median_likes'] >= float(likes_min)]
            if likes_max:
                topics = [t for t in topics if t['median_likes'] is not None and t['median_likes'] <= float(likes_max)]
            if comments_min:
                topics = [t for t in topics if t['median_comments'] is not None and t['median_comments'] >= float(comments_min)]
            if comments_max:
                topics = [t for t in topics if t['median_comments'] is not None and t['median_comments'] <= float(comments_max)]
            if date_from:
                topics = [t for t in topics if t['last_posted_raw'] and str(t['last_posted_raw']) >= date_from]
            if date_to:
                topics = [t for t in topics if t['last_posted_raw'] and str(t['last_posted_raw']) <= date_to]

            reverse = sort_order == "DESC"
            sort_field = 'last_posted_raw' if sort_by == 'last_posted' else sort_by
            def sort_key(t):
                val = t.get(sort_field)
                if val is None:
                    return (0, '') if reverse else (1, '')
                return (1, val) if reverse else (0, val)
            topics.sort(key=sort_key, reverse=reverse)

            page = topics[offset:offset + limit]

            for t in page:
                t.pop('last_posted_raw', None)

            return jsonify(page)

    except mysql.connector.Error as err:
        app.logger.error(f"Database error in topics list: {err}")
        return jsonify({"error": "Database error"}), 500
    except Exception as e:
        app.logger.error(f"Error in topics list: {e}")
        return jsonify({"error": "Server error"}), 500

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

@app.route("/topic/<int:topic_id>")
def show_topic_details(topic_id):
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor(dictionary=True)

            # Fetch topic details
            cursor.execute("SELECT * FROM topics WHERE id = %s", (topic_id,))
            topic = cursor.fetchone()

            if not topic:
                return "Topic not found", 404

            # Fetch all posts for this topic
            cursor.execute("""
                SELECT p.*
                FROM posts p
                JOIN topic_posts tp ON p.post_id = tp.post_id
                WHERE tp.topic_id = %s
                ORDER BY p.post_datetime DESC
            """, (topic_id,))
            posts = cursor.fetchall()

            # Fetch relevant topics
            cursor.execute("""
                SELECT t.id, t.name, COUNT(t.id) as post_count
                FROM topics t
                JOIN topic_posts tp ON t.id = tp.topic_id
                WHERE tp.post_id IN (
                    SELECT post_id FROM topic_posts WHERE topic_id = %s
                ) AND t.id != %s
                GROUP BY t.id, t.name
                ORDER BY post_count DESC
                LIMIT 10
            """, (topic_id, topic_id))
            relevant_topics = cursor.fetchall()

            total_posts = len(posts)
            last_post_date = ""
            if posts:
                last_post_date = posts[0]['post_datetime'].strftime('%d %B %Y')

            # Calculate stats
            likes = [p['likes'] for p in posts if p['likes'] is not None]
            impressions = [p['impressions'] for p in posts if p['impressions'] is not None]
            comments = [p['comments'] for p in posts if p['comments'] is not None]

            stats = {
                'avg_likes': statistics.mean(likes) if likes else 0,
                'median_likes': statistics.median(likes) if likes else 0,
                'avg_impressions': statistics.mean(impressions) if impressions else 0,
                'median_impressions': statistics.median(impressions) if impressions else 0,
                'avg_comments': statistics.mean(comments) if comments else 0,
                'median_comments': statistics.median(comments) if comments else 0,
            }

            return render_template('topic.html',
                                   topic=topic,
                                   posts=posts,
                                   total_posts=total_posts,
                                   last_post_date=last_post_date,
                                   stats=stats,
                                   relevant_topics=relevant_topics)

    except mysql.connector.Error as err:
        app.logger.error(f"Database error in topic details: {err}")
        return "Database error", 500

#Download all the post data as JSON
@app.route("/download")
def download_data():
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor(dictionary=True)

            # Fetch all posts
            cursor.execute("SELECT * FROM posts")
            posts = cursor.fetchall()

            # Fetch all topics and group them by post_id
            cursor.execute("""
                SELECT tp.post_id, t.name
                FROM topics t
                JOIN topic_posts tp ON t.id = tp.topic_id
            """)
            topic_data = cursor.fetchall()
            
            topics_by_post = {}
            for row in topic_data:
                post_id = row['post_id']
                if post_id not in topics_by_post:
                    topics_by_post[post_id] = []
                topics_by_post[post_id].append(row['name'])

            # Combine posts with their topics
            for post in posts:
                post_id = post['post_id']
                post['topics'] = topics_by_post.get(post_id, [])
                if post.get('post_datetime'):
                    post['post_datetime'] = post['post_datetime'].isoformat()

            # Create a JSON response
            response = jsonify(posts)
            response.headers['Content-Disposition'] = 'attachment; filename=posts.json'
            return response

    except mysql.connector.Error as err:
        app.logger.error(f"Database error: {err}")
        return jsonify({"error": "Database error"}), 500

#Get topic suggestions for confirm post: 
@app.route("/api/topics")
def api_topics():
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT id, name FROM topics")
            topics = cursor.fetchall()
            return jsonify(topics)
    except mysql.connector.Error as err:
        app.logger.error(f"Database error: {err}")
        return jsonify({"error": "Database error"}), 500

#Save post after confirmation
@app.route("/api/save-post", methods=['POST'])
def save_post():
    data = request.get_json()
    post_data = data.get('post_data')
    tags = data.get('tags')

    if not post_data or not tags:
        return jsonify({"error": "Missing data"}), 400

    def cleanup_current_file():
        try:
            queue = session.get('post_files_queue', [])
            if queue:
                filename = queue.pop(0)
                session['post_files_queue'] = queue
                session.modified = True
                
                upload_folder = os.path.join(current_app.root_path, 'temp_uploads', 'user_uploads')
                file_path = os.path.join(upload_folder, filename)
                if os.path.exists(file_path):
                    os.remove(file_path)
                    current_app.logger.info(f"Cleaned up file: {filename}")
        except Exception as e:
            current_app.logger.error(f"Error during file cleanup: {e}")

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            conn.start_transaction()

            try:
                post_columns = [key for key in post_data.keys() if key != 'media_url']
                post_values = [post_data[key] for key in post_columns]
                
                if 'media_url' in post_data and post_data['media_url']:
                    post_columns.append('media_url')
                    post_values.append(post_data['media_url'])

                query = f"INSERT INTO posts ({', '.join(post_columns)}) VALUES ({', '.join(['%s'] * len(post_columns))})"
                cursor.execute(query, post_values)
                post_id = post_data['post_id']

                topic_ids = []
                for tag in tags:
                    cursor.execute("SELECT id FROM topics WHERE name = %s", (tag,))
                    result = cursor.fetchone()
                    if result:
                        topic_ids.append(result[0])
                    else:
                        cursor.execute("INSERT INTO topics (name) VALUES (%s)", (tag,))
                        topic_ids.append(cursor.lastrowid)

                for topic_id in topic_ids:
                    cursor.execute("INSERT INTO topic_posts (post_id, topic_id) VALUES (%s, %s)", (post_id, topic_id))

                conn.commit()
                
                cleanup_current_file()
                return jsonify({"success": True, "post_id": post_id}), 201

            except mysql.connector.Error as err:
                conn.rollback()
                
                if err.errno == 1062: # 1062 is the standard MySQL code for Duplicate Entry
                    app.logger.warning(f"Duplicate post skipped: {err}")
                    cleanup_current_file() 
                    return jsonify({"error": "Post already exists in database. File skipped.", "code": "DUPLICATE"}), 409
                
                # --- OTHER DB ERRORS ---
                app.logger.error(f"Database transaction error: {err}")
                return jsonify({"error": "Database error during transaction"}), 500

    except mysql.connector.Error as err:
        app.logger.error(f"Database connection error: {err}")
        return jsonify({"error": "Database connection error"}), 500

@app.route("/api/ask-ai-query", methods=['POST'])
def ask_ai_query():
    data = request.get_json()
    user_question = data.get("question")

    if not user_question:
        return jsonify({"error": "No question provided"}), 400

    sql_query = None
    try:
        query_info = ask_ai.generate_query(user_question)
        query_type = query_info.get("type", "simple")
        sql_query = query_info.get("sql", "")
        
        clean_query = sql_query.strip().lstrip('(').lstrip().upper()
        allowed_starts = ("SELECT", "WITH", "SHOW", "DESCRIBE", "EXPLAIN")
        
        if not clean_query.startswith(allowed_starts):
            return jsonify({
                "error": "The AI generated an invalid query.", 
                "sql": sql_query
            }), 400

        with get_read_only_db_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(sql_query)
            results = cursor.fetchall()

            #Convert big numbers to string to avoid precision loss
            for row in results:
                for key, value in row.items():
                    if key == 'post_id' and value is not None:
                        row[key] = str(value)
                    elif isinstance(value, int) and value > 9007199254740991:
                        row[key] = str(value)
            
            response_data = {
                "type": query_type,
                "sql": sql_query,
                "data": results
            }

            if query_type == "analytical":
                try:
                    analysis = ask_ai.analyze_results(user_question, sql_query, results)
                    response_data["analysis"] = analysis
                except Exception as e:
                    app.logger.error(f"Analysis generation failed: {e}")
                    response_data["analysis"] = "Could not generate analysis, but here is the raw data."

            return jsonify(response_data)

    except mysql.connector.Error as err:
        app.logger.error(f"Read-Only Database error: {err}")
        return jsonify({"error": str(err), "sql": sql_query}), 500
    except Exception as e:
        app.logger.error(f"AI/Server Error: {e}")
        return jsonify({"error": "Failed to process the question with AI."}), 500

def run_media_sync(app_instance):
    with app_instance.app_context():
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor(dictionary=True)
                cursor.execute("SELECT post_id, post_url FROM posts WHERE post_datetime > '2025-12-10 23:59:59'")
                # Hardcoded date for now, but you can change it as needed.
                rows = cursor.fetchall()

                media_dir = os.path.join(app_instance.root_path, 'static', 'media')
                if not os.path.exists(media_dir):
                    os.makedirs(media_dir)

                existing_files = os.listdir(media_dir)

                for row in rows:
                    p_id = str(row['post_id'])
                    if not any(f.startswith(p_id) for f in existing_files):
                        app_instance.logger.info(f"Downloading missing media for: {p_id}")
                        file_handler.download_media_by_id(row['post_url'], p_id)
            
            app_instance.logger.info("Sync Complete.")
        except Exception as e:
            app_instance.logger.error(f"Sync failed: {e}")

@app.route("/api/sync-media")
def sync_media():
    thread = threading.Thread(target=run_media_sync, args=(app,)) 
    thread.daemon = True
    thread.start()
    return jsonify({"message": "Sync started in background. Check your terminal logs."}), 202

@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Not found"}), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({"error": "Internal server error"}), 500

#Server entry point
if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)

    