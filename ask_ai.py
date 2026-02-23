import os
import json
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
Your job is to translate user questions into valid MySQL queries AND classify the question type.

Here is the database schema:
{DB_SCHEMA}

RULES:
1. You MUST return ONLY a valid JSON object with exactly two keys: "type" and "sql".
2. "type" must be either "simple" or "analytical".
   - "simple": Direct lookup, filter, or ranking questions where showing the resulting table IS the answer.
     Examples: "which post got the most likes?", "show me all posts from January", "top 5 posts by impressions"
   - "analytical": Comparative, trend, or reasoning questions where the raw data needs interpretation to actually answer.
     Examples: "do I get more clicks when I post once or twice a day?", "what day of the week performs best?", "is there a correlation between caption length and likes?"
3. "sql" must be a valid MySQL SELECT query that fetches the data needed to answer the question.
4. DO NOT wrap the JSON in markdown formatting.
5. DO NOT include any text outside the JSON object.
6. If a question is unrelated to the database, return: {{"type": "simple", "sql": "SELECT 'I can only answer questions about the database.' AS error;"}}
"""

ANALYSIS_PROMPT = """
You are a data analyst. The user asked a question about their social media posts database.
You have been given their original question, the SQL query that was used, and the resulting data.

Your job is to analyze the data and provide a clear, concise, natural-language answer to the user's question.

RULES:
1. Be direct and answer the question first, then explain with supporting numbers.
2. Keep the answer concise — 2-4 sentences max.
3. Use actual numbers from the data to support your answer.
4. Do NOT include any SQL or code in your response.
5. Do NOT repeat the raw data — just interpret it.
"""

def generate_query(user_question):
    client = genai.Client()

    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        temperature=0.1
    )

    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=user_question,
        config=config
    )

    raw = response.text.strip()
    if raw.startswith("```json"):
        raw = raw[7:]
    if raw.startswith("```"):
        raw = raw[3:]
    if raw.endswith("```"):
        raw = raw[:-3]
    raw = raw.strip()

    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        return {"type": "simple", "sql": raw}

    if "type" not in result or "sql" not in result:
        return {"type": "simple", "sql": result.get("sql", raw)}

    return result


def analyze_results(user_question, sql_query, data):
    client = genai.Client()

    data_for_analysis = data[:50] if len(data) > 50 else data

    user_content = (
        f"Original question: {user_question}\n\n"
        f"SQL used: {sql_query}\n\n"
        f"Data returned ({len(data)} rows, showing up to 50):\n"
        f"{json.dumps(data_for_analysis, default=str, indent=2)}"
    )

    config = types.GenerateContentConfig(
        system_instruction=ANALYSIS_PROMPT,
        temperature=0.3
    )

    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=user_content,
        config=config
    )

    return response.text.strip()