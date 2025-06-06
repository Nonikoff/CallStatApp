# Asterisk Call Statistics API

This API provides call statistics from an Asterisk CDR database.

## Setup

1. Install the required packages:

`pip install -r requirements`

2. Create a `.env` file with your database credentials and API token.

3. Run the application:
   

`   gunicorn app:app`


## API Endpoints

### Get Call Statistics


GET /api/v1/{token}/callstat?date=YYYY-MM-DD


Parameters:
- `token`: Your API authentication token
- `date`: (Optional) The date for which to retrieve statistics (default: current date)

Response:
`json
[
  {
    "src": "1234",
    "cnam": "John Doe",
    "unique_calls": 5,
    "call_count": 10,
    "formatted_total_time_minutes": 45.5
  },
  ...
]`