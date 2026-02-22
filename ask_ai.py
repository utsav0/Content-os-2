import os
from google import genai
from google.genai import types

DB_SCHEMA = """
Table: posts
Columns: 
  - post_id (bigint) PRIMARY KEY
  - post_url (varchar(500))
  - media_url (varchar(500))
  - post_datetime (datetime)
  - caption (longtext)
  - likes (int)
  - comments (int)
  - impressions (int)
  - members_reached (int)
  - total_clicks (int)
  - main_ebook_clicks (int)
  - lead_magnet_clicks (int)
  - profile_viewers (int)
  - followers_gained (int)
  - reactions (int)
  - reposts (int)
  - saves (int)
  - sends (int)
  - created_at (timestamp)
  - main_ebook_ctr (decimal(6,2))

Table: topics
Columns:
  - id (int) PRIMARY KEY, AUTO_INCREMENT
  - name (varchar(255)) UNIQUE
  - created_at (timestamp)

Table: topic_posts
Columns:
  - topic_id (int) COMPOSITE PRIMARY KEY
  - post_id (bigint) COMPOSITE PRIMARY KEY
"""

SYSTEM_PROMPT = f"""
You are an expert MySQL SQL generator. 
Your job is to translate user questions into strictly valid MySQL queries.

Here is the database schema:
{DB_SCHEMA}

RULES:
1. ONLY return the raw SQL query.
2. DO NOT wrap the SQL in markdown formatting (e.g., no ```sql ... ```).
3. DO NOT include any explanations, greetings, or text other than the query itself.
4. If a question is unrelated to the database, return "SELECT 'I can only answer questions about the database.' AS error;"
"""

def generate_sql(user_question):
    client = genai.Client()
    
    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        temperature=0.1 # Keep this low so the AI is highly factual and less "creative"
    )

    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=user_question,
        config=config
    )
    
    raw_sql = response.text.strip()
    if raw_sql.startswith("```sql"):
        raw_sql = raw_sql[6:]
    if raw_sql.startswith("```"):
        raw_sql = raw_sql[3:]
    if raw_sql.endswith("```"):
        raw_sql = raw_sql[:-3]
        
    return raw_sql.strip()