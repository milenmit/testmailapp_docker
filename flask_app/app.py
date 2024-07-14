from flask import Flask, request, jsonify
from dbutils.pooled_db import PooledDB
import pymysql
import logging
import json
from datetime import datetime
from dotenv import load_dotenv
from functools import wraps
import html
import decimal
import os

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# Database connection pool
pool = PooledDB(
    creator=pymysql,
    host=os.getenv('DB_HOST'),
    user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD'),
    database=os.getenv('DB_NAME'),
    autocommit=True,
    charset=os.getenv('DB_CHARSET'),
    cursorclass=pymysql.cursors.DictCursor,
    blocking=True,
    maxconnections=int(os.getenv('DB_MAX_CONNECTIONS', 5))
)

# Enable logging
logging.basicConfig(level=logging.DEBUG)

API_KEY = os.getenv('API_KEY')  # This should be stored securely, e.g., in environment variables

def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        key = request.args.get('api_key')
        if key and key == API_KEY:
            return f(*args, **kwargs)
        else:
            return jsonify({"error": "Unauthorized access"}), 403
    return decorated_function

def escape_json_special_characters(data):
    """Escape special characters in JSON strings."""
    if isinstance(data, str):
        return data.replace('\\', '').replace('\n', ' ').replace('\t', ' ').replace('"', '')  # Remove \n, \t, ", and \
    if isinstance(data, list):
        return [escape_json_special_characters(item) for item in data]
    if isinstance(data, dict):
        return {key: escape_json_special_characters(value) for key, value in data.items()}
    return data

def decode_unicode_escape(data):
    """Decode Unicode escape sequences in strings."""
    if isinstance(data, str):
        # Replace HTML entities and remove newlines
        return html.unescape(data).replace('\n', '')
    if isinstance(data, list):
        return [decode_unicode_escape(item) for item in data]
    if isinstance(data, dict):
        return {key: decode_unicode_escape(value) for key, value in data.items()}
    return data

def replace_hyphens_in_keys(data):
    """Recursively replace hyphens with underscores in JSON keys."""
    if isinstance(data, dict):
        new_data = {}
        for key, value in data.items():
            new_key = key.replace('-', '_')
            new_data[new_key] = replace_hyphens_in_keys(value)
        return new_data
    elif isinstance(data, list):
        return [replace_hyphens_in_keys(item) for item in data]
    else:
        return data

def json_serial(obj):
    """JSON serializer for objects not serializable by default json code."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, decimal.Decimal):
        return float(obj)
    raise TypeError("Type not serializable")

@app.route('/emails', methods=['GET'])
@require_api_key
def get_emails():
    to_email = request.args.get('to_email')
    sort_order = request.args.get('sort', 'DESC').upper()
    limit = request.args.get('limit')
    offset = request.args.get('offset', 0)

    if not to_email:
        return jsonify({"error": "to_email parameter is required"}), 400

    if sort_order not in ['ASC', 'DESC']:
        return jsonify({"error": "Invalid sort order. Use 'ASC' or 'DESC'"}), 400

    try:
        limit = int(limit) if limit else None
        offset = int(offset)
    except ValueError:
        return jsonify({"error": "Limit and offset must be integers"}), 400

    logging.debug(f"to_email: {to_email}, sort_order: {sort_order}, limit: {limit}, offset: {offset}")

    connection = pool.connection()
    try:
        with connection.cursor() as cursor:
            # Query to get the total count of emails
            count_sql = "SELECT COUNT(*) as count FROM emails WHERE to_email = %s"
            cursor.execute(count_sql, (to_email,))
            total_count = cursor.fetchone()['count']

            # Query to get emails with sorting, limit, and offset
            sql = f"SELECT * FROM emails WHERE to_email = %s ORDER BY received_time {sort_order}"
            query_params = [to_email]

            if limit is not None:
                sql += " LIMIT %s OFFSET %s"
                query_params.extend([limit, offset])
            elif offset:
                sql += " LIMIT 18446744073709551615 OFFSET %s"  # MySQL's maximum limit
                query_params.append(offset)

            cursor.execute(sql, query_params)
            emails = cursor.fetchall()

            if not emails:
                return jsonify({"message": "No emails found for the given to_email"}), 404

            email_data = []
            for email in emails:
                email_id = email['id']

                # Query to get email parts
                sql_parts = "SELECT * FROM email_parts WHERE email_id = %s"
                cursor.execute(sql_parts, (email_id,))
                parts = cursor.fetchall()

                # Query to get email attachments
                sql_attachments = "SELECT * FROM email_attachments WHERE email_id = %s"
                cursor.execute(sql_attachments, (email_id,))
                attachments = cursor.fetchall()

                # Ensure raw_headers and parts headers are correctly formatted
                email['raw_headers'] = escape_json_special_characters(json.loads(email['raw_headers']))
                email['raw_headers']['to'] = escape_json_special_characters(email['raw_headers'].get('to', ''))
                for part in parts:
                    part['headers'] = escape_json_special_characters(json.loads(part['headers']))
                    part['content'] = decode_unicode_escape(part['content'])

                email_info = {
                    "email": replace_hyphens_in_keys(email),
                    "parts": replace_hyphens_in_keys(parts),
                    "attachments": replace_hyphens_in_keys(attachments)
                }
                email_data.append(email_info)

            response_data = {
                "count": total_count,
                "limit": limit,
                "offset": offset,
                "emails": email_data
            }

            response = app.response_class(
                response=json.dumps(response_data, default=json_serial, indent=4),
                mimetype='application/json'
            )
            return response
    finally:
        connection.close()

@app.route('/emails/<int:email_id>', methods=['DELETE'])
@require_api_key
def delete_email(email_id):
    connection = pool.connection()
    try:
        with connection.cursor() as cursor:
            # Delete email, parts, and attachments for the given email_id
            sql_delete_email = "DELETE FROM emails WHERE id = %s"
            sql_delete_parts = "DELETE FROM email_parts WHERE email_id = %s"
            sql_delete_attachments = "DELETE FROM email_attachments WHERE email_id = %s"

            cursor.execute(sql_delete_parts, (email_id,))
            cursor.execute(sql_delete_attachments, (email_id,))
            cursor.execute(sql_delete_email, (email_id,))

            connection.commit()

            if cursor.rowcount == 0:
                return jsonify({"message": "No email found with the given ID"}), 404

            return jsonify({"message": f"Email with ID {email_id} deleted successfully"}), 200
    finally:
        connection.close()

@app.route('/emails', methods=['DELETE'])
@require_api_key
def delete_all_emails():
    connection = pool.connection()
    try:
        with connection.cursor() as cursor:
            # Delete all emails, parts, and attachments
            cursor.execute("DELETE FROM email_parts")
            cursor.execute("DELETE FROM email_attachments")
            cursor.execute("DELETE FROM emails")

            connection.commit()

            return jsonify({"message": "All emails deleted successfully"}), 200
    finally:
        connection.close()

@app.route('/emails/stats', methods=['GET'])
@require_api_key
def get_email_stats():
    connection = pool.connection()
    try:
        with connection.cursor() as cursor:
            # Query to get the total email count in the database
            total_email_count_sql = "SELECT COUNT(*) as total_email_count FROM emails"
            cursor.execute(total_email_count_sql)
            total_email_count = cursor.fetchone()['total_email_count']

            # Query to get the size of the database in MB
            database_size_sql = """
            SELECT table_schema AS database_name,
                   ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) AS size_mb
            FROM information_schema.tables
            WHERE table_schema = 'emails'
            GROUP BY table_schema
            """
            cursor.execute(database_size_sql)
            database_size = cursor.fetchone()['size_mb']

            stats = {
                "total_email_count": total_email_count,
                "database_size_mb": database_size
            }

            response = app.response_class(
                response=json.dumps(stats, default=json_serial, indent=4),
                mimetype='application/json'
            )
            return response
    finally:
        connection.close()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
