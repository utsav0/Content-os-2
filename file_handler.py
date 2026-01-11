import pandas as pd
from flask import current_app
from datetime import datetime
import json
import requests
from bs4 import BeautifulSoup
import re
import os

def _to_int(value):
    try:
        if pd.isna(value):
            return 0
    except Exception:
        pass
    if isinstance(value, (int, float)):
        try:
            return int(value)
        except Exception:
            return 0
    if isinstance(value, str):
        v = value.strip()
        if v == "" or v.lower() in ("nan", "none", "n/a", "-", "—"):
            return 0
        v = v.replace(',', '')
        m = re.search(r'-?\d+', v)
        return int(m.group()) if m else 0
    return 0

def handle_file(file_path):
    if not os.path.exists(file_path):
        return {"error": "File not found."}

    filename = os.path.basename(file_path)

    try:
        if filename.endswith('.csv'):
            df = pd.read_csv(file_path, header=None, names=['key', 'value'])
        elif filename.endswith('.xlsx'):
            df = pd.read_excel(file_path, header=None, names=['key', 'value'])
        else:
            return {"error": f"Unsupported file type: {filename}. Please upload a .csv or .xlsx file."}

        df.dropna(subset=['value'], inplace=True)
        df = df[~df['key'].str.startswith('top-', na=False)]
        data = df.set_index('key')['value'].to_dict()

        post_url = data.get('Post URL')
        if not post_url:
            return {"error": f"'Post URL' not found in the uploaded file {filename}."}

        post_id = None
        m = re.search(r'urn:li:(?:share|ugcshare):(\d+)', post_url) or re.search(r'/(\d+)/?', post_url)
        if m:
            post_id = m.group(1)
        if not post_id:
            return {"error": f"Could not extract post ID from URL: {post_url}"}

        caption = None
        media_url = None
        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            resp = requests.get(post_url, headers=headers, timeout=10)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, 'html.parser')

            caption_tag = soup.find('p', class_='attributed-text-segment-list__content')
            if caption_tag:
                caption = caption_tag.get_text(separator='\n', strip=True)
            else:
                og_desc = soup.find('meta', property='og:description')
                caption = og_desc['content'].strip() if og_desc and og_desc.get('content') else None

            media_meta = soup.find('meta', property='og:image')
            media_url = media_meta['content'] if media_meta and media_meta.get('content') else None

            if media_url and post_id:
                media_response = requests.get(media_url, headers=headers, timeout=10)
                media_response.raise_for_status()

                content_type = media_response.headers.get('content-type', '').split(';')[0].lower()
                mapping = {
                    'image/gif': '.gif',
                    'image/png': '.png',
                    'image/jpeg': '.jpeg',
                    'image/jpg': '.jpeg',
                    'video/mp4': '.mp4',
                    'image/webp': '.webp'
                }
                ext = mapping.get(content_type)
                if not ext:
                    ext = os.path.splitext(media_url.split('?')[0])[-1].lower() or '.jpeg'
                if not ext.startswith('.'):
                    ext = '.' + ext

                save_dir = os.path.join('static', 'media')
                os.makedirs(save_dir, exist_ok=True)
                save_path = os.path.join(save_dir, f"{post_id}{ext}")
                with open(save_path, 'wb') as f:
                    f.write(media_response.content)
                media_url = f"{post_id}{ext}"

        except requests.exceptions.RequestException as e:
            return {"error": f"Error fetching post data from {post_url}: {e}"}
        except Exception as e:
            return {"error": f"Unexpected error while fetching post data: {e}"}

        post_date = data.get('Post Date')
        post_time = data.get('Post Publish Time')
        post_datetime = None
        if post_date and post_time:
            try:
                post_datetime = datetime.strptime(f"{post_date} {post_time}", '%b %d, %Y %I:%M %p')
            except ValueError as e:
                return {"error": f"Error parsing date/time: {e}"}
        else:
            return {"error": f"'Post Date' or 'Post Publish Time' not found in {filename}."}

        main_ebook_clicks_key = next(
            (k for k in data.keys() if isinstance(k, str) and k.startswith("https://flexicajourney.com/master-flexbox-and-grid")),
            None
        )
        main_ebook_clicks = _to_int(data.get(main_ebook_clicks_key, 0)) if main_ebook_clicks_key else 0
        impressions = _to_int(data.get('Impressions', 0))
        ctr = 0
        if impressions > 0:
            ctr = (main_ebook_clicks / impressions) * 100

        transformed_data = {
            'post_id': post_id,
            'post_url': post_url,
            'media_url': media_url,
            'caption': caption,
            'post_datetime': post_datetime.strftime('%Y-%m-%d %H:%M:%S'),
            'likes': _to_int(data.get('Reactions', 0)),
            'comments': _to_int(data.get('Comments', 0)),
            'impressions': _to_int(data.get('Impressions', 0)),
            'members_reached': _to_int(data.get('Members reached', 0)),
            'total_clicks': _to_int(data.get('Visits to links in this post', 0)),
            'main_ebook_clicks': main_ebook_clicks,
            'main_ebook_ctr': ctr,
            'lead_magnet_clicks': 0,
            'profile_viewers': _to_int(data.get('Profile viewers from this post', 0)),
            'followers_gained': _to_int(data.get('Followers gained from this post', 0)),
            'reactions': _to_int(data.get('Reactions', 0)),
            'reposts': _to_int(data.get('Reposts', 0)),
            'saves': _to_int(data.get('Saves', 0)),
            'sends': _to_int(data.get('Sends on LinkedIn', 0))
        }

        current_app.logger.info(json.dumps(transformed_data, indent=2, ensure_ascii=False))
        return transformed_data

    except Exception as e:
        current_app.logger.error(f"Error processing file {filename}: {e}")
        return {"error": f"An unexpected error occurred: {e}"}