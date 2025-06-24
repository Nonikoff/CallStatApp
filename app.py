from flask import Flask, request, jsonify
import pymysql
import os
from dotenv import load_dotenv
from datetime import datetime
import logging

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database configurations
db_configs = [
    {
        'name': 'DB1',
        'host': os.getenv('DB1_HOST'),
        'port': int(os.getenv('DB1_PORT', 3306)),
        'user': os.getenv('DB1_USER'),
        'password': os.getenv('DB1_PASSWORD'),
        'db': os.getenv('DB1_NAME'),
        'charset': 'utf8mb4',
        'cursorclass': pymysql.cursors.DictCursor
    },
    {
        'name': 'DB2',
        'host': os.getenv('DB2_HOST'),
        'port': int(os.getenv('DB2_PORT', 3306)),
        'user': os.getenv('DB2_USER'),
        'password': os.getenv('DB2_PASSWORD'),
        'db': os.getenv('DB2_NAME'),
        'charset': 'utf8mb4',
        'cursorclass': pymysql.cursors.DictCursor
    },
    {
        'name': 'DB3',
        'host': os.getenv('DB3_HOST'),
        'port': int(os.getenv('DB3_PORT', 3306)),
        'user': os.getenv('DB3_USER'),
        'password': os.getenv('DB3_PASSWORD'),
        'db': os.getenv('DB3_NAME'),
        'charset': 'utf8mb4',
        'cursorclass': pymysql.cursors.DictCursor
    }
]

# API authentication token
API_TOKEN = os.getenv('API_TOKEN')

def get_connection(db_config):
    """Create a database connection"""
    try:
        logger.info(f"Connecting to database {db_config['name']} at {db_config['host']}:{db_config['port']}")
        return pymysql.connect(
            host=db_config['host'],
            port=db_config['port'],
            user=db_config['user'],
            password=db_config['password'],
            db=db_config['db'],
            charset=db_config['charset'],
            cursorclass=db_config['cursorclass']
        )
    except Exception as e:
        logger.error(f"Failed to connect to {db_config['name']}: {str(e)}")
        return None
def query_database(db_config, date_param):
    """Query a single database for call statistics"""
    connection = get_connection(db_config)
    if not connection:
        return {
            'error': f"Failed to connect to {db_config['name']} at {db_config['host']}:{db_config['port']}"
        }

    try:
        with connection.cursor() as cursor:
            query = """
                SELECT
    cdr.cnum,
    IFNULL(cdr.cnam, '') AS cnam,
    COUNT(DISTINCT cdr.dst) AS unique_calls,
    COUNT(*) AS call_count,
    ROUND(SUM(CASE
        WHEN cdr.lastapp = 'Dial' AND cdr.disposition = 'ANSWERED'
        THEN cdr.billsec
        ELSE 0
    END) / 60, 2) AS formatted_total_time_minutes
FROM
    asteriskcdrdb.cdr
WHERE
    DATE(cdr.calldate) = %s
    AND cdr.cnum >= 2000 AND cdr.cnum <= 3999
    AND cdr.lastapp IN ('Dial', 'Busy', 'Congestion')
    AND cdr.disposition != 'FAILED'
    AND cdr.dst NOT REGEXP '^[0-9]{4}$'
GROUP BY
    cdr.cnum, cdr.cnam
ORDER BY
    formatted_total_time_minutes DESC;
            """
            cursor.execute(query, (date_param,))
            results = cursor.fetchall()

            # Convert Decimal objects to float for JSON serialization
            for row in results:
                if 'formatted_total_time_minutes' in row:
                    row['formatted_total_time_minutes'] = float(row['formatted_total_time_minutes'])

            return {
                'status': 'success',
                'data': results
            }

    except Exception as e:
        logger.error(f"Error querying {db_config['name']}: {str(e)}")
        return {
            'error': f"Error querying {db_config['name']}: {str(e)}"
        }

    finally:
        if connection and connection.open:
            connection.close()

def combine_results(all_results):
    """Combine results from multiple databases by cnum"""
    combined = {}
    errors = []

    for db_name, result in all_results.items():
        if 'error' in result:
            errors.append({db_name: result['error']})
            continue

        for row in result['data']:
            cnum = row['cnum']
            if cnum not in combined:
                combined[cnum] = {
                    'cnum': cnum,
                    'cnam': row['cnam'],
                    'unique_calls': 0,
                    'call_count': 0,
                    'formatted_total_time_minutes': 0
                }

            combined[cnum]['unique_calls'] += row['unique_calls']
            combined[cnum]['call_count'] += row['call_count']
            combined[cnum]['formatted_total_time_minutes'] += row['formatted_total_time_minutes']

            # Use the non-empty cnam if available
            if not combined[cnum]['cnam'] and row['cnam']:
                combined[cnum]['cnam'] = row['cnam']

    # Convert to list and sort by total time
    combined_list = list(combined.values())
    combined_list.sort(key=lambda x: x['formatted_total_time_minutes'], reverse=True)

    return combined_list, errors
@app.route('/api/v1/<token>/callstat', methods=['GET'])
def get_call_stats(token):
    """Get call statistics from multiple databases for a specific date"""
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

    # Query all databases
    all_results = {}
    for db_config in db_configs:
        all_results[db_config['name']] = query_database(db_config, date_param)

    # Combine results
    combined_data, errors = combine_results(all_results)

    # Prepare response
    response = {
        'data': combined_data,
        'date': date_param
    }

    if errors:
        response['errors'] = errors

    return jsonify(response)

if __name__ == '__main__':
    # For development only
    app.run(debug=False)
