from flask import Flask, request, jsonify
import pymysql
import os
from dotenv import load_dotenv
from datetime import datetime
import logging
from collections import OrderedDict


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
        'name': os.getenv('DB1_HOST'),
        'host': os.getenv('DB1_HOST'),
        'port': int(os.getenv('DB1_PORT', 3306)),
        'user': os.getenv('DB1_USER'),
        'password': os.getenv('DB1_PASSWORD'),
        'charset': 'utf8mb4',
        'cursorclass': pymysql.cursors.DictCursor
    },
    {
        'name': os.getenv('DB2_HOST'),
        'host': os.getenv('DB2_HOST'),
        'port': int(os.getenv('DB2_PORT', 3306)),
        'user': os.getenv('DB2_USER'),
        'password': os.getenv('DB2_PASSWORD'),
        'charset': 'utf8mb4',
        'cursorclass': pymysql.cursors.DictCursor
    },
    {
        'name': os.getenv('DB3_HOST'),
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
def query_database(db_config, date_param=None, start_dt=None, end_dt=None):
    """Query a single database for call statistics

    Args:
        db_config: Database connection configuration.
        date_param: 'week' | 'month' | specific date string 'YYYY-MM-DD' (kept for backward compatibility).
        start_dt: start of range as 'YYYY-MM-DD HH:MM[:SS]'. Used when a custom date range is requested.
        end_dt: end of range as 'YYYY-MM-DD HH:MM[:SS]'. Used when a custom date range is requested.
    """
    connection = get_connection(db_config)
    if not connection:
        return {
            'error': f"Failed to connect to {db_config['name']} at {db_config['host']}:{db_config['port']}"
        }

    try:
        with connection.cursor() as cursor:
            # Determine which query to use based on date_param
            if date_param and date_param.lower() == 'week':
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
            elif date_param and date_param.lower() == 'month':
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
                # Query for specific date or custom date range
                if start_dt and end_dt:
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
                        cdr.calldate >= %s AND cdr.calldate <= %s
                        AND cdr.cnum >= 2000 AND cdr.cnum <= 3999
                        AND cdr.lastapp IN ('Dial', 'Busy', 'Congestion')
                        AND cdr.disposition != 'FAILED'
                        AND cdr.dst NOT REGEXP '^[0-9]{4}$'
                    GROUP BY
                        cdr.cnum, cdr.cnam
                    ORDER BY
                        total_call_time_minutes DESC
                    """
                    cursor.execute(query, (start_dt, end_dt))
                else:
                    # Backward-compatible: single date means whole day
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
    """Get call statistics from multiple databases for a specific date, week, month, or custom date-time range.

    New support:
      - Query params: start=YYYY-MM-DD[ HH:MM] and end=YYYY-MM-DD[ HH:MM]
      - If HH:MM missing: start defaults to 00:00, end defaults to 23:59
      - Validate start <= end
      - When date='week' or 'month' is provided, existing aggregation logic is used unchanged.
    """
    # Validate token
    if token != API_TOKEN:
        return jsonify({'error': 'Invalid token'}), 401

    # Get parameters
    date_param = request.args.get('date')
    start_param = request.args.get('start')
    end_param = request.args.get('end')

    # Helper to parse date or date-time with defaults for time
    def _parse_dt(value: str, is_start: bool):
        value = value.strip()
        fmts = ['%Y-%m-%d %H:%M', '%Y-%m-%d']
        last_exc = None
        for fmt in fmts:
            try:
                dt = datetime.strptime(value, fmt)
                # If format had no time (date only), set default time
                if fmt == '%Y-%m-%d':
                    if is_start:
                        dt = dt.replace(hour=0, minute=0)
                    else:
                        dt = dt.replace(hour=23, minute=59)
                return dt
            except ValueError as e:
                last_exc = e
        raise ValueError(str(last_exc) if last_exc else 'Invalid date-time')

    # Determine mode: week/month vs date range
    use_week_or_month = bool(date_param and date_param.lower() in ['week', 'month'])

    start_dt = None
    end_dt = None
    range_label = None

    if use_week_or_month:
        # No additional validation needed here; handled in query functions
        pass
    else:
        # Build a date range
        try:
            if start_param or end_param:
                if not start_param or not end_param:
                    return jsonify({'error': 'Both start and end must be provided when using a custom range'}), 400
                start_dt_obj = _parse_dt(start_param, is_start=True)
                end_dt_obj = _parse_dt(end_param, is_start=False)
            else:
                # Backward-compatible behavior with ?date=YYYY-MM-DD or missing both -> today
                if not date_param:
                    base_date = datetime.now().strftime('%Y-%m-%d')
                else:
                    # Validate plain date
                    try:
                        datetime.strptime(date_param, '%Y-%m-%d')
                    except ValueError:
                        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD, "week", or "month"'}), 400
                    base_date = date_param
                start_dt_obj = datetime.strptime(base_date + ' 00:00', '%Y-%m-%d %H:%M')
                end_dt_obj = datetime.strptime(base_date + ' 23:59', '%Y-%m-%d %H:%M')

            # Validate ordering
            if start_dt_obj > end_dt_obj:
                return jsonify({'error': 'Invalid range: start must be less than or equal to end'}), 400

            # Format as strings with seconds for MySQL
            start_dt = start_dt_obj.strftime('%Y-%m-%d %H:%M:%S')
            end_dt = end_dt_obj.strftime('%Y-%m-%d %H:%M:%S')
            range_label = f"{start_dt_obj.strftime('%Y-%m-%d %H:%M')} - {end_dt_obj.strftime('%Y-%m-%d %H:%M')}"
        except ValueError:
            return jsonify({'error': 'Invalid date-time format. Use YYYY-MM-DD HH:MM or YYYY-MM-DD'}), 400

    # Query all databases
    all_results = {}
    for db_config in db_configs:
        if use_week_or_month:
            all_results[db_config['name']] = query_database(db_config, date_param=date_param)
        else:
            all_results[db_config['name']] = query_database(db_config, date_param=None, start_dt=start_dt, end_dt=end_dt)

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
    if use_week_or_month:
        response = OrderedDict([
            ('data', reordered_data),
            ('date', date_param)
        ])
    else:
        response = OrderedDict([
            ('data', reordered_data),
            ('start', start_dt),
            ('end', end_dt),
            ('date', range_label)
        ])

    if errors:
        response['errors'] = errors

    return jsonify(response)

@app.route('/api/v1/<token>/asrstat', methods=['GET'])
def get_asr_stats(token):
        """Get ASR statistics by country code prefix from multiple databases"""
        # Validate token
        if token != API_TOKEN:
            return jsonify({'error': 'Invalid token'}), 401

        # Get date parameter
        date_param = request.args.get('date')

        # Validate date format
        if not date_param:
            # Use current date if no date provided
            date_param = datetime.now().strftime('%Y-%m-%d')
        elif date_param.lower() not in ['week', 'month']:
            try:
                datetime.strptime(date_param, '%Y-%m-%d')
            except ValueError:
                return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD, "week", or "month"'}), 400

        # Query all databases
        all_results = {}
        for db_config in db_configs:
            all_results[db_config['name']] = query_asr_database(db_config, date_param)

        # Prepare response with results from each database separately
        response = OrderedDict([
            ('date', date_param),
            ('databases', all_results)
        ])

        return jsonify(response)

def query_asr_database(db_config, date_param):
        """Query a single database for ASR statistics by country code prefix"""
        connection = get_connection(db_config)
        if not connection:
            return {
                'error': f"Failed to connect to {db_config['name']} at {db_config['host']}:{db_config['port']}"
            }

        try:
            with connection.cursor() as cursor:
                # Determine which query to use based on date_param
                if date_param.lower() == 'week':
                    cursor.execute("USE asteriskcdrdb")
                    query = """
                        SELECT 
                            get_country_code(cdr.dst) AS country_code,
                            cc.country,
                            COUNT(DISTINCT CASE WHEN cdr.disposition = 'ANSWERED' THEN cdr.uniqueid ELSE NULL END) AS answered_calls,
                            COUNT(DISTINCT cdr.uniqueid) AS total_calls,
                            ROUND((COUNT(DISTINCT CASE WHEN cdr.disposition = 'ANSWERED' THEN cdr.uniqueid ELSE NULL END) / 
                                   COUNT(DISTINCT cdr.uniqueid)) * 100, 2) AS asr_percentage,
                            COUNT(DISTINCT cdr.dst) AS unique_destinations,
                            ROUND(SUM(CASE WHEN cdr.disposition = 'ANSWERED' THEN cdr.billsec ELSE 0 END) / 60, 2) AS total_talk_minutes
                        FROM asteriskcdrdb.cdr
                        LEFT JOIN asteriskcdrdb.country_codes cc ON cc.code = get_country_code(cdr.dst)
                        WHERE calldate >= DATE_SUB(CURRENT_DATE, INTERVAL WEEKDAY(CURRENT_DATE) + 7 DAY)
                          AND calldate < DATE_SUB(CURRENT_DATE, INTERVAL WEEKDAY(CURRENT_DATE) + 2 DAY)
                          AND cdr.lastapp = 'Dial'
                          AND cdr.disposition IN ('ANSWERED', 'NO ANSWER', 'BUSY', 'FAILED')
                          AND cdr.dst NOT REGEXP '^[0-9]{4}$' -- Excluding 4-digit internal calls
                        GROUP BY get_country_code(cdr.dst), cc.country
                        ORDER BY total_calls DESC
                    """
                    cursor.execute(query)
                elif date_param.lower() == 'month':
                    cursor.execute("USE asteriskcdrdb")
                    query = """
                       SELECT 
                            get_country_code(cdr.dst) AS country_code,
                            cc.country,
                            COUNT(DISTINCT CASE WHEN cdr.disposition = 'ANSWERED' THEN cdr.uniqueid ELSE NULL END) AS answered_calls,
                            COUNT(DISTINCT cdr.uniqueid) AS total_calls,
                            ROUND((COUNT(DISTINCT CASE WHEN cdr.disposition = 'ANSWERED' THEN cdr.uniqueid ELSE NULL END) / 
                                   COUNT(DISTINCT cdr.uniqueid)) * 100, 2) AS asr_percentage,
                            COUNT(DISTINCT cdr.dst) AS unique_destinations,
                            ROUND(SUM(CASE WHEN cdr.disposition = 'ANSWERED' THEN cdr.billsec ELSE 0 END) / 60, 2) AS total_talk_minutes
                        FROM asteriskcdrdb.cdr
                        LEFT JOIN asteriskcdrdb.country_codes cc ON cc.code = get_country_code(cdr.dst)
                        WHERE calldate >= DATE_FORMAT(DATE_SUB(CURRENT_DATE, INTERVAL 1 MONTH), '%Y-%m-01')
                          AND calldate < DATE_FORMAT(CURRENT_DATE, '%Y-%m-01')
                          AND cdr.lastapp = 'Dial'
                          AND cdr.disposition IN ('ANSWERED', 'NO ANSWER', 'BUSY', 'FAILED')
                          AND cdr.dst NOT REGEXP '^[0-9]{4}$' -- Excluding 4-digit internal calls
                        GROUP BY get_country_code(cdr.dst), cc.country
                        ORDER BY total_calls DESC
                    """
                    cursor.execute(query)
                else:
                    cursor.execute("USE asteriskcdrdb")
                    # Query for specific date
                    query = """
                        SELECT 
                            get_country_code(cdr.dst) AS country_code,
                            cc.country,
                            COUNT(DISTINCT CASE WHEN cdr.disposition = 'ANSWERED' THEN cdr.uniqueid ELSE NULL END) AS answered_calls,
                            COUNT(DISTINCT cdr.uniqueid) AS total_calls,
                            ROUND((COUNT(DISTINCT CASE WHEN cdr.disposition = 'ANSWERED' THEN cdr.uniqueid ELSE NULL END) / 
                                   COUNT(DISTINCT cdr.uniqueid)) * 100, 2) AS asr_percentage,
                            COUNT(DISTINCT cdr.dst) AS unique_destinations,
                            ROUND(SUM(CASE WHEN cdr.disposition = 'ANSWERED' THEN cdr.billsec ELSE 0 END) / 60, 2) AS total_talk_minutes
                        FROM asteriskcdrdb.cdr
                        LEFT JOIN asteriskcdrdb.country_codes cc ON cc.code = get_country_code(cdr.dst)
                        WHERE DATE(cdr.calldate) = %s -- You can adjust this date range as needed
                          AND cdr.lastapp = 'Dial'
                          AND cdr.disposition IN ('ANSWERED', 'NO ANSWER', 'BUSY', 'FAILED')
                          AND cdr.dst NOT REGEXP '^[0-9]{4}$' -- Excluding 4-digit internal calls
                        GROUP BY get_country_code(cdr.dst), cc.country
                        ORDER BY total_calls DESC
                    """
                    cursor.execute(query, (date_param,))

                results = cursor.fetchall()

                # Convert Decimal objects to float for JSON serialization and add country name
                for row in results:
                    if 'answered_calls' in row:
                        row['answered_calls'] = int(row['answered_calls'])
                    if 'total_calls' in row:
                        row['total_calls'] = int(row['total_calls'])
                    if 'asr_percentage' in row:
                        row['asr_percentage'] = round(float(row['asr_percentage']), 2)
                    if 'unique_destinations' in row:
                        row['unique_destinations'] = int(row['unique_destinations'])
                    if 'total_talk_minutes' in row:
                        row['total_talk_minutes'] = round(float(row['total_talk_minutes']), 2)
                    if 'country_code' in row:
                        row['country_code'] = str(row['country_code'])

                return {
                    'status': 'success',
                    'data': results
                }

        except Exception as e:
            logger.error(f"Error querying {db_config['name']} for ASR stats: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {
                'error': f"Error querying {db_config['name']}: {str(e)}"
            }

        finally:
            if connection and connection.open:
                connection.close()

if __name__ == '__main__':
    # For development only
    app.run(debug=False)