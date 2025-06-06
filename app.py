from flask import Flask, request, jsonify
import pymysql
import os
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Database configuration
db_config = {
    'host': os.getenv('DB_HOST'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'db': os.getenv('DB_NAME'),
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

# API authentication token
API_TOKEN = os.getenv('API_TOKEN')

def get_connection():
    """Create a database connection"""
    return pymysql.connect(**db_config)

@app.route('/api/v1/<token>/callstat', methods=['GET'])
def get_call_stats(token):
    """Get call statistics for a specific date"""
    # Validate token
    if token != API_TOKEN:
        return jsonify({'error': 'Invalid token'}), 401

    # Get date parameter
    date_param = request.args.get('date')

    # Validate date format
    try:
        if date_param:
            datetime.strptime(date_param, '%Y-%m-%d')
        else:
            # Use current date if no date provided
            date_param = datetime.now().strftime('%Y-%m-%d')
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400

    try:
        # Connect to the database
        connection = get_connection()
        with connection.cursor() as cursor:
            # Execute the query
            query = """
            SELECT
                src,
                IFNULL(cnam, '') as cnam,
                COUNT(DISTINCT dst) AS unique_calls,
                COUNT(*) AS call_count,
                ROUND(SUM(billsec) / 60, 2) AS formatted_total_time_minutes
            FROM
                cdr
            WHERE
                DATE(calldate) = %s
                AND lastapp = 'Dial'
                AND disposition = 'ANSWERED'
            GROUP BY
                src
            ORDER BY
                SUM(billsec) DESC
            """
            cursor.execute(query, (date_param,))
            results = cursor.fetchall()

            # Convert Decimal objects to float for JSON serialization
            for row in results:
                if 'formatted_total_time_minutes' in row:
                    row['formatted_total_time_minutes'] = float(row['formatted_total_time_minutes'])

            return jsonify(results)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

    finally:
        if 'connection' in locals() and connection.open:
            connection.close()
if __name__ == '__main__':
    # For development only
    app.run(debug=True)
