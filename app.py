from flask import Flask, request, jsonify
import pymysql
import os
from dotenv import load_dotenv
from datetime import datetime
import logging
from collections import OrderedDict  # Add this import

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.json.sort_keys = False  # This ensures that jsonify doesn't sort the keys alphabetically

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
        'charset': 'utf8mb4',
        'cursorclass': pymysql.cursors.DictCursor
    },
    {
        'name': 'DB2',
        'host': os.getenv('DB2_HOST'),
        'port': int(os.getenv('DB2_PORT', 3306)),
        'user': os.getenv('DB2_USER'),
        'password': os.getenv('DB2_PASSWORD'),
        'charset': 'utf8mb4',
        'cursorclass': pymysql.cursors.DictCursor
    },
    {
        'name': 'DB3',
        'host': os.getenv('DB3_HOST'),
        'port': int(os.getenv('DB3_PORT', 3306)),
        'user': os.getenv('DB3_USER'),
        'password': os.getenv('DB3_PASSWORD'),
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
            # Determine which query to use based on date_param
            if date_param.lower() == 'week':
                query = """
                SELECT
                    cdr.cnum,
                    IFNULL(cdr.cnam, '') AS cnam,
                    COUNT(DISTINCT cdr.dst) AS unique_calls,
                    COUNT(DISTINCT cdr.uniqueid) AS call_count,
                    ROUND(SUM(CASE
                        WHEN cdr.lastapp = 'Dial' AND cdr.disposition = 'ANSWERED'
                        THEN cdr.billsec
                        ELSE 0
                    END) / 60, 2) AS total_call_time_minutes,
                    COUNT(DISTINCT CASE
                        WHEN cdr.lastapp = 'Dial' AND cdr.disposition = 'ANSWERED' AND cdr.billsec > 90
                        THEN cdr.uniqueid
                        ELSE NULL
                    END) AS long_calls_count,
                    ROUND(SUM(CASE
                        WHEN cdr.lastapp = 'Dial' AND cdr.disposition = 'ANSWERED' AND cdr.billsec > 90
                        THEN cdr.billsec
                        ELSE 0
                    END) / 60, 2) AS total_long_calls_minutes
                FROM
                    asteriskcdrdb.cdr
                WHERE
                    calldate >= DATE_SUB(CURRENT_DATE, INTERVAL WEEKDAY(CURRENT_DATE) + 7 DAY)
                    AND calldate < DATE_SUB(CURRENT_DATE, INTERVAL WEEKDAY(CURRENT_DATE) + 2 DAY)
                    AND cdr.cnum >= 2000 AND cdr.cnum <= 3999
                    AND cdr.lastapp IN ('Dial', 'Busy', 'Congestion')
                    AND cdr.disposition != 'FAILED'
                    AND cdr.dst NOT REGEXP '^[0-9]{4}$'
                GROUP BY
                    cdr.cnum, cdr.cnam
                ORDER BY
                    total_call_time_minutes DESC
                """
                cursor.execute(query)
            elif date_param.lower() == 'month':
                query = """
                SELECT
                    cdr.cnum,
                    IFNULL(cdr.cnam, '') AS cnam,
                    COUNT(DISTINCT cdr.dst) AS unique_calls,
                    COUNT(DISTINCT cdr.uniqueid) AS call_count,
                    ROUND(SUM(CASE
                        WHEN cdr.lastapp = 'Dial' AND cdr.disposition = 'ANSWERED'
                        THEN cdr.billsec
                        ELSE 0
                    END) / 60, 2) AS total_call_time_minutes,
                    COUNT(DISTINCT CASE
                        WHEN cdr.lastapp = 'Dial' AND cdr.disposition = 'ANSWERED' AND cdr.billsec > 90
                        THEN cdr.uniqueid
                        ELSE NULL
                    END) AS long_calls_count,
                    ROUND(SUM(CASE
                        WHEN cdr.lastapp = 'Dial' AND cdr.disposition = 'ANSWERED' AND cdr.billsec > 90
                        THEN cdr.billsec
                        ELSE 0
                    END) / 60, 2) AS total_long_calls_minutes
                FROM
                    asteriskcdrdb.cdr
                WHERE
                    calldate >= DATE_FORMAT(DATE_SUB(CURRENT_DATE, INTERVAL 1 MONTH), '%Y-%m-01')
                    AND calldate < DATE_FORMAT(CURRENT_DATE, '%Y-%m-01')
                    AND cdr.cnum >= 2000 AND cdr.cnum <= 3999
                    AND cdr.lastapp IN ('Dial', 'Busy', 'Congestion')
                    AND cdr.disposition != 'FAILED'
                    AND cdr.dst NOT REGEXP '^[0-9]{4}$'
                GROUP BY
                    cdr.cnum, cdr.cnam
                ORDER BY
                    total_call_time_minutes DESC
                """
                cursor.execute(query)
            else:
                # Original query for specific date
                query = """
                SELECT
                    cdr.cnum,
                    IFNULL(cdr.cnam, '') AS cnam,
                    COUNT(DISTINCT cdr.dst) AS unique_calls,
                    COUNT(DISTINCT cdr.uniqueid) AS call_count,
                    ROUND(SUM(CASE
                        WHEN cdr.lastapp = 'Dial' AND cdr.disposition = 'ANSWERED'
                        THEN cdr.billsec
                        ELSE 0
                    END) / 60, 2) AS total_call_time_minutes,
                    COUNT(DISTINCT CASE
                        WHEN cdr.lastapp = 'Dial' AND cdr.disposition = 'ANSWERED' AND cdr.billsec > 90
                        THEN cdr.uniqueid
                        ELSE NULL
                    END) AS long_calls_count,
                    ROUND(SUM(CASE
                        WHEN cdr.lastapp = 'Dial' AND cdr.disposition = 'ANSWERED' AND cdr.billsec > 90
                        THEN cdr.billsec
                        ELSE 0
                    END) / 60, 2) AS total_long_calls_minutes
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
                    total_call_time_minutes DESC
                """
                cursor.execute(query, (date_param,))

            results = cursor.fetchall()

            # Convert Decimal objects to float for JSON serialization and ensure 2 decimal places
            stats_by_cnum = {}
            for row in results:
                if 'total_call_time_minutes' in row:
                    row['total_call_time_minutes'] = round(float(row['total_call_time_minutes']), 2)
                if 'total_long_calls_minutes' in row:
                    row['total_long_calls_minutes'] = round(float(row['total_long_calls_minutes']), 2)

                # Index stats by extension for later merge with extension list
                stats_by_cnum[row['cnum']] = row

            # --- Get full extension list from asterisk.sip and add zero-stat rows where needed ---
            ext_query = """
                SELECT
                    id AS cnum,
                    SUBSTRING_INDEX(SUBSTRING_INDEX(data, ',', -1), '<', 1) AS cnam
                FROM asterisk.sip
                WHERE keyword = 'callerid'
                  AND id >= 2000
                  AND id <= 3999
            """
            cursor.execute(ext_query)
            extensions = cursor.fetchall()

            final_rows = []
            for ext in extensions:
                cnum = ext['cnum']
                ext_name = ext.get('cnam') or ''

                if cnum in stats_by_cnum:
                    row = stats_by_cnum[cnum]
                    # Prefer non-empty name from sip if cnam is empty in stats
                    if not row.get('cnam') and ext_name:
                        row['cnam'] = ext_name
                else:
                    # No stats for this extension on the requested date/period – add zero stats
                    row = {
                        'cnum': cnum,
                        'cnam': ext_name,
                        'unique_calls': 0,
                        'call_count': 0,
                        'total_call_time_minutes': 0.00,
                        'long_calls_count': 0,
                        'total_long_calls_minutes': 0.00,
                    }

                final_rows.append(row)

            return {
                'status': 'success',
                'data': final_rows
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
                    'call_count': 0,
                    'total_call_time_minutes': 0,
                    'long_calls_count': 0,
                    'total_long_calls_minutes': 0,
                    'unique_calls': 0
                }

            combined[cnum]['unique_calls'] += row['unique_calls']
            combined[cnum]['call_count'] += row['call_count']
            combined[cnum]['total_call_time_minutes'] += row['total_call_time_minutes']
            combined[cnum]['long_calls_count'] += row['long_calls_count']
            combined[cnum]['total_long_calls_minutes'] += row['total_long_calls_minutes']

            # Use the non-empty cnam if available
            if not combined[cnum]['cnam'] and row['cnam']:
                combined[cnum]['cnam'] = row['cnam']

    # Convert to list and sort by total time
    combined_list = list(combined.values())

    # Ensure all total_call_time_minutes are rounded to exactly 2 decimal places
    for item in combined_list:
        item['total_call_time_minutes'] = round(item['total_call_time_minutes'], 2)
        item['total_long_calls_minutes'] = round(item['total_long_calls_minutes'], 2)

    combined_list.sort(key=lambda x: x['total_call_time_minutes'], reverse=True)

    return combined_list, errors


@app.route('/api/v1/<token>/callstat', methods=['GET'])
def get_call_stats(token):
    """Get call statistics from multiple databases for a specific date, week, or month"""
    # Validate token
    if token != API_TOKEN:
        return jsonify({'error': 'Invalid token'}), 401

    # Get date parameter
    date_param = request.args.get('date')

    # Validate date format or special keywords
    if not date_param:
        # Use current date if no date provided
        date_param = datetime.now().strftime('%Y-%m-%d')
    elif date_param.lower() not in ['week', 'month']:
        try:
            datetime.strptime(date_param, '%Y-%m-%d')
        except ValueError:
            return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD or "week" or "month"'}), 400

    # Query all databases
    all_results = {}
    for db_config in db_configs:
        all_results[db_config['name']] = query_database(db_config, date_param)

    # Combine results
    combined_data, errors = combine_results(all_results)
    
    # Reorder fields in each record using OrderedDict
    reordered_data = []
    for item in combined_data:
        reordered_item = OrderedDict([
            ('cnum', item['cnum']),
            ('cnam', item['cnam']),
            ('call_count', item['call_count']),
            ('total_call_time_minutes', item['total_call_time_minutes']),
            ('long_calls_count', item['long_calls_count']),
            ('total_long_calls_minutes', item['total_long_calls_minutes']),
            ('unique_calls', item['unique_calls'])
        ])
        reordered_data.append(reordered_item)
    
    # Prepare response with OrderedDict
    response = OrderedDict([
        ('data', reordered_data),
        ('date', date_param)
    ])

    if errors:
        response['errors'] = errors

    return jsonify(response)


if __name__ == '__main__':
    # For development only
    app.run(debug=False)