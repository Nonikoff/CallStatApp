/**
 * Google Apps Script client for CallStatApp
 *
 * Sensitive data (host/base URL and API key) have been removed from the code.
 * Configure the following Script Properties in your Apps Script project:
 *  - API_BASE_URL  (e.g., https://your.api.host)
 *  - API_VERSION   (e.g., v1)
 *  - API_KEY       (your token or UUID)
 *
 * The helper functions getConfig_() and buildApiUrl_() will compose full URLs.
 */

// Global function that can be called from a button
function showDatePickerAndRunQuery() {
  // Create a custom UI prompt
  var ui = SpreadsheetApp.getUi();
  var result = ui.prompt(
    'Enter Date',
    'Please enter date in YYYY-MM-DD format:',
    ui.ButtonSet.OK_CANCEL);

  // Process the result
  var button = result.getSelectedButton();
  var dateText = result.getResponseText();

  if (button == ui.Button.OK) {
    // Validate date format (basic validation)
    var dateRegex = new RegExp('^\\d{4}-\\d{2}-\\d{2}$');
    if (dateRegex.test(dateText)) {
      // Call the function with the date parameter
      importCallStats(dateText);
    } else {
      ui.alert('Invalid date format. Please use YYYY-MM-DD format.');
    }
  }
}


function importCallStats(dateParam) {
  // Build API URL with dynamic date parameter
  var url = buildApiUrl_('callstat', { date: dateParam });

  // Make the HTTP request
  var response = UrlFetchApp.fetch(url);

  // Parse the JSON response
  var json = JSON.parse(response.getContentText());

  // Get the active sheet
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();

  // Put the requested date in cell B2
  sheet.getRange("B2").setValue(dateParam);
  sheet.getRange("B3").clearContent();

  // Check if the response contains the data array
  if (json.data && Array.isArray(json.data)) {
    // Prepare data array for batch update
    var dataToImport = [];

    // For each item in the data array
    json.data.forEach(function(item) {
      // Filter for cnum between 2000 and 3999
      var cnumValue = parseInt(item.cnum);
      if (cnumValue >= 2000 && cnumValue <= 3999) {
        // Create a row with the specific fields in the REORDERED sequence
        var row = [
          item.cnum,                        // Column A: cnum
          item.cnam,                        // Column B: cnam
          item.call_count,                  // Column C: call_count          
          item.total_call_time_minutes,     // Column D: total_call_time_minutes
          item.unique_calls,                // Column E: unique_calls                    
          item.long_calls_count,            // Column F: long_calls_count
          item.total_long_calls_minutes     // Column G:
        ];
        dataToImport.push(row);
      }
    });

    // Clear previous data (optional)
    // If you have existing data from row 7 onwards, clear it first
    var lastRow = sheet.getLastRow();
    if (lastRow >= 7) {
      sheet.getRange(7, 1, lastRow - 6, 7).clearContent();
    }

    // If we have data to import
    if (dataToImport.length > 0) {
      // Write all data at once starting at A7
      sheet.getRange(7, 1, dataToImport.length, 7).setValues(dataToImport);

      // Optional: Show a success message
      showAlertSafe('Data imported successfully for date: ' + dateParam + '\nFiltered to extensions 2000-3999 only.');
    } else {
      showAlertSafe('No data found for the selected date within extension range 2000-3999.');
    }
  } else {
    showAlertSafe('No data found in the API response or unexpected format');
  }
}

// Automatically imports today's data without asking for a date (Used for "Today's results" button and in "Triggers" for automatic update)
function autoImportCallStats() {
  var today = new Date();
  var year = today.getFullYear();
  var month = ('0' + (today.getMonth() + 1)).slice(-2); // Month is zero-indexed
  var day = ('0' + today.getDate()).slice(-2);
  var formattedDate = year + '-' + month + '-' + day;

  importCallStats(formattedDate);
}

// Safe alert: shows a UI alert when available, falls back to Logger/console otherwise.
function showAlertSafe(message) {
  try {
    SpreadsheetApp.getUi().alert(message);
  } catch (err) {
    // Background context (trigger or Web App) — just log it
    try {
      console.log(message);
    } catch (e) {
      Logger.log(message);
    }
  }
}

// Function to import weekly call stats
function importWeeklyCallStats() {
  // Build API URL for weekly data
  var url = buildApiUrl_('callstat', { date: 'week' });

  // Make the HTTP request
  var response = UrlFetchApp.fetch(url);

  // Parse the JSON response
  var json = JSON.parse(response.getContentText());

  // Get the active sheet
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();

  // Put "Last Week" in cell B2
  sheet.getRange("B2").setValue("Last Week");

  // Check if the response contains the data array
  if (json.data && Array.isArray(json.data)) {
    // Prepare data array for batch update
    var dataToImport = [];

    // For each item in the data array
    json.data.forEach(function(item) {
      // Filter is no longer needed as API already filters, but keeping for safety
      var cnumValue = parseInt(item.cnum);
      if (cnumValue >= 2000 && cnumValue <= 3999) {
        // Create a row with the specific fields in the REORDERED sequence
        var row = [
          item.cnum,                        // Column A: cnum
          item.cnam,                        // Column B: cnam
          item.call_count,                  // Column C: call_count          
          item.total_call_time_minutes,     // Column D: total_call_time_minutes
          item.unique_calls,                // Column E: unique_calls                    
          item.long_calls_count,            // Column F: long_calls_count
          item.total_long_calls_minutes     // Column G:
        ];
        dataToImport.push(row);
      }
    });

    // Clear previous data
    var lastRow = sheet.getLastRow();
    if (lastRow >= 7) {
      sheet.getRange(7, 1, lastRow - 6, 7).clearContent();
    }

    // If we have data to import
    if (dataToImport.length > 0) {
      // Write all data at once starting at A7
      sheet.getRange(7, 1, dataToImport.length, 7).setValues(dataToImport);

      // Optional: Show a success message
      showAlertSafe('Weekly call statistics imported successfully.');
    } else {
      showAlertSafe('No weekly call data found.');
    }
  } else {
    showAlertSafe('No data found in the API response or unexpected format');
  }
}
// Function to import monthly call stats
function importMonthlyCallStats() {
  // Build API URL for monthly data
  var url = buildApiUrl_('callstat', { date: 'month' });

  // Make the HTTP request
  var response = UrlFetchApp.fetch(url);

  // Parse the JSON response
  var json = JSON.parse(response.getContentText());

  // Get the active sheet
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();

  // Put "Last Month" in cell B2
  sheet.getRange("B2").setValue("Last Month");

  // Check if the response contains the data array
  if (json.data && Array.isArray(json.data)) {
    // Prepare data array for batch update
    var dataToImport = [];

    // For each item in the data array
    json.data.forEach(function(item) {
      // Filter is no longer needed as API already filters, but keeping for safety
      var cnumValue = parseInt(item.cnum);
      if (cnumValue >= 2000 && cnumValue <= 3999) {
        // Create a row with the specific fields in the REORDERED sequence
        var row = [
          item.cnum,                        // Column A: cnum
          item.cnam,                        // Column B: cnam
          item.call_count,                  // Column C: call_count          
          item.total_call_time_minutes,     // Column D: total_call_time_minutes
          item.unique_calls,                // Column E: unique_calls                    
          item.long_calls_count,            // Column F: long_calls_count
          item.total_long_calls_minutes     // Column G:
        ];
        dataToImport.push(row);
      }
    });

    // Clear previous data
    var lastRow = sheet.getLastRow();
    if (lastRow >= 7) {
      sheet.getRange(7, 1, lastRow - 6, 7).clearContent();
    }

    // If we have data to import
    if (dataToImport.length > 0) {
      // Write all data at once starting at A7
      sheet.getRange(7, 1, dataToImport.length, 7).setValues(dataToImport);

      // Optional: Show a success message
      showAlertSafe('Monthly call statistics imported successfully.');
    } else {
      showAlertSafe('No monthly call data found.');
    }
  } else {
    showAlertSafe('No data found in the API response or unexpected format');
  }
}

function importAsrStats() {
  // Build API URL for ASR statistics
  var url = buildApiUrl_('asrstat');

  try {
    // Make the HTTP request
    var response = UrlFetchApp.fetch(url);
    var json = JSON.parse(response.getContentText());

    // Get the active sheet
    var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
    
    // --- HANDLE FILTERS ---
    // Check if a filter exists and remove it to avoid the "already has a filter" error
    var existingFilter = sheet.getFilter();
    if (existingFilter) {
      existingFilter.remove();
    }

    // --- CLEAR OLD DATA ---
    // Clear everything from row 7 downwards before importing new data
    var lastRow = sheet.getLastRow();
    if (lastRow >= 7) {
      sheet.getRange(7, 1, lastRow - 6, 8).clear(); // Clear content and formatting
    }

    var today = new Date();
    var year = today.getFullYear();
    var month = ('0' + (today.getMonth() + 1)).slice(-2);
    var day = ('0' + today.getDate()).slice(-2);
    var formattedDate = year + '-' + month + '-' + day;
    var dateParam = formattedDate;

    // Put the requested date in cell B2
    sheet.getRange("B2").setValue(dateParam);

    if (json.databases && typeof json.databases === 'object') {
      var allDataToImport = [];

      for (var dbName in json.databases) {
        if (json.databases.hasOwnProperty(dbName)) {
          var dbResult = json.databases[dbName];
          if (dbResult.error) continue;

          if (dbResult.data && Array.isArray(dbResult.data)) {
            dbResult.data.forEach(function(item) {
              var row = [
                dbName,
                item.country_code || "",
                item.country || "",
                item.answered_calls || 0,
                item.total_calls || 0,
                item.asr_percentage || 0,
                item.unique_destinations || 0,
                item.total_talk_minutes || 0
              ];
              allDataToImport.push(row);
            });
          }
        }
      }

      if (allDataToImport.length > 0) {
        var headers = [
          "Database", "Country Code", "Country", "Answered Calls", 
          "Total Calls", "ASR %", "Unique Destinations", "Total Talk Minutes"
        ];

        // Write headers in row 7
        var headerRange = sheet.getRange(7, 1, 1, headers.length);
        headerRange.setValues([headers]);
        headerRange.setFontWeight("bold");
        headerRange.setBackground("#d3d3d3");

        // Write all data starting at row 8
        sheet.getRange(8, 1, allDataToImport.length, headers.length).setValues(allDataToImport);

        // --- APPLY NEW FILTER ---
        // Range covers header (row 7) plus all data rows
        var filterRange = sheet.getRange(7, 1, allDataToImport.length + 1, headers.length);
        filterRange.createFilter();

        showAlertSafe('ASR statistics imported successfully for date: ' + dateParam + '\nTotal rows: ' + allDataToImport.length);
      } else {
        showAlertSafe('No valid data found in the API response.');
      }
    } else {
      showAlertSafe('No databases found in the API response or unexpected format');
    }
  } catch (error) {
    showAlertSafe('Error importing ASR statistics: ' + error.toString());
    Logger.log('Error details: ' + error);
  }
}

// Global function that can be called from a button
function showDateTimePickerAndRunQuery() {
  // Create an HTML modal dialog
  var html = HtmlService.createHtmlOutput(`
    <style>
      body {
        font-family: Arial, sans-serif;
        padding: 20px;
      }
      .form-group {
        margin-bottom: 15px;
      }
      label {
        display: block;
        margin-bottom: 5px;
        font-weight: bold;
      }
      input {
        width: 100%;
        padding: 8px;
        box-sizing: border-box;
        border: 1px solid #ccc;
        border-radius: 4px;
      }
      .button-group {
        margin-top: 20px;
        display: flex;
        gap: 10px;
        justify-content: flex-end;
      }
      button {
        padding: 10px 20px;
        border: none;
        border-radius: 4px;
        cursor: pointer;
        font-size: 14px;
      }
      .ok-button {
        background-color: #4285f4;
        color: white;
      }
      .ok-button:hover {
        background-color: #357ae8;
      }
      .cancel-button {
        background-color: #f5f5f5;
        color: #333;
      }
      .cancel-button:hover {
        background-color: #e8e8e8;
      }
      .error {
        color: #d33b27;
        font-size: 12px;
        margin-top: 5px;
        display: none;
      }
    </style>

    <h2>Import Call Statistics</h2>
    
    <div class="form-group">
      <label for="startDate">Start Date (YYYY-MM-DD):</label>
      <input type="date" id="startDate" required>
    </div>

    <div class="form-group">
      <label for="startTime">Start Time (HH:MM) 24-hour - Optional:</label>
      <input type="text" id="startTime" placeholder="00:00" maxlength="5" pattern="([01]?[0-9]|2[0-3]):[0-5][0-9]">
    </div>

    <div class="form-group">
      <label for="endDate">End Date (YYYY-MM-DD):</label>
      <input type="date" id="endDate" required>
    </div>

    <div class="form-group">
      <label for="endTime">End Time (HH:MM) 24-hour - Optional:</label>
      <input type="text" id="endTime" placeholder="23:59" maxlength="5" pattern="([01]?[0-9]|2[0-3]):[0-5][0-9]">
    </div>

    <div class="error" id="errorMsg"></div>

    <div class="button-group">
      <button class="cancel-button" onclick="google.script.host.closeDialog()">Cancel</button>
      <button class="ok-button" onclick="submitForm()">OK</button>
    </div>

    <script>
      // Format time input to HH:MM (24-hour format)
      function formatTime(input) {
        var value = input.value.replace(/[^0-9:]/g, '');
        
        if (value.length > 0) {
          var parts = value.split(':');
          var hours = parts[0] || '0';
          var minutes = parts[1] || '0';
          
          // Remove leading zeros for processing
          hours = parseInt(hours, 10);
          minutes = parseInt(minutes, 10);
          
          // Validate hours (0-23) and minutes (0-59)
          if (isNaN(hours)) hours = 0;
          if (isNaN(minutes)) minutes = 0;
          if (hours < 0) hours = 0;
          if (hours > 23) hours = 23;
          if (minutes < 0) minutes = 0;
          if (minutes > 59) minutes = 59;
          
          // Format with leading zeros
          input.value = String(hours).padStart(2, '0') + ':' + String(minutes).padStart(2, '0');
        }
      }

      document.getElementById('startTime').addEventListener('blur', function() {
        formatTime(this);
      });

      document.getElementById('endTime').addEventListener('blur', function() {
        formatTime(this);
      });

      function submitForm() {
        var startDate = document.getElementById('startDate').value;
        var startTime = document.getElementById('startTime').value;
        var endDate = document.getElementById('endDate').value;
        var endTime = document.getElementById('endTime').value;
        var errorMsg = document.getElementById('errorMsg');

        // Validate inputs
        if (!startDate || !endDate) {
          errorMsg.textContent = 'Start and End dates are required';
          errorMsg.style.display = 'block';
          return;
        }

        // Validate time format if provided
        var timeRegex = /^([01]?[0-9]|2[0-3]):[0-5][0-9]$/;
        if (startTime && !timeRegex.test(startTime)) {
          errorMsg.textContent = 'Start time must be in HH:MM format (00:00 to 23:59)';
          errorMsg.style.display = 'block';
          return;
        }
        if (endTime && !timeRegex.test(endTime)) {
          errorMsg.textContent = 'End time must be in HH:MM format (00:00 to 23:59)';
          errorMsg.style.display = 'block';
          return;
        }

        // Format dates and times
        var startString = startDate + (startTime ? ' ' + startTime : ' 00:00');
        var endString = endDate + (endTime ? ' ' + endTime : ' 23:59');

        // Validate date range
        var startDateTime = new Date(startDate + 'T' + (startTime || '00:00'));
        var endDateTime = new Date(endDate + 'T' + (endTime || '23:59'));

        if (startDateTime > endDateTime) {
          errorMsg.textContent = 'Start date/time must be before End date/time';
          errorMsg.style.display = 'block';
          return;
        }

        // Close dialog and call the import function
        google.script.host.closeDialog();
        google.script.run.importCallStatsWithDateRange(startString, endString);
      }
    </script>
  `)
  .setWidth(400)
  .setHeight(450);

  SpreadsheetApp.getUi().showModalDialog(html, 'Import Call Statistics');
}

function importCallStatsWithDateRange(startDateTime, endDateTime) {
  // Build API URL with dynamic start and end parameters
  var url = buildApiUrl_('callstat', {
    start: startDateTime,
    end: endDateTime
  });

  try {
    // Make the HTTP request
    var response = UrlFetchApp.fetch(url);
    
    // Parse the JSON response
    var json = JSON.parse(response.getContentText());

    // Get the active sheet
    var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();

    // Put the date range in cells B2 and B3
    sheet.getRange("B2").setValue(startDateTime);
    sheet.getRange("B3").setValue(endDateTime);

    // Check if the response contains the data array
    if (json.data && Array.isArray(json.data)) {
      // Prepare data array for batch update
      var dataToImport = [];

      // For each item in the data array
      json.data.forEach(function(item) {
        // Filter for cnum between 2000 and 3999
        var cnumValue = parseInt(item.cnum);
        if (cnumValue >= 2000 && cnumValue <= 3999) {
          // Create a row with the specific fields in the REORDERED sequence
          var row = [
            item.cnum,                        // Column A: cnum
            item.cnam,                        // Column B: cnam
            item.call_count,                  // Column C: call_count          
            item.total_call_time_minutes,     // Column D: total_call_time_minutes
            item.unique_calls,                // Column E: unique_calls                    
            item.long_calls_count,            // Column F: long_calls_count
            item.total_long_calls_minutes     // Column G: total_long_calls_minutes
          ];
          dataToImport.push(row);
        }
      });

      // Clear previous data (optional)
      // If you have existing data from row 7 onwards, clear it first
      var lastRow = sheet.getLastRow();
      if (lastRow >= 7) {
        sheet.getRange(7, 1, lastRow - 6, 7).clearContent();
      }

      // If we have data to import
      if (dataToImport.length > 0) {
        // Write all data at once starting at A7
        sheet.getRange(7, 1, dataToImport.length, 7).setValues(dataToImport);

        // Optional: Show a success message
        showAlertSafe('Data imported successfully for range:\n' + startDateTime + ' to ' + endDateTime + '\nFiltered to extensions 2000-3999 only.');
      } else {
        showAlertSafe('No data found for the selected date range within extension range 2000-3999.');
      }
    } else {
      showAlertSafe('No data found in the API response or unexpected format');
    }
  } catch (error) {
    showAlertSafe('Error fetching data: ' + error.toString());
  }
}

// (Removed duplicate definition of showAlertSafe; see unified version above.)

// =====================
// Helper functions
// =====================

/**
 * Reads and validates required configuration from Script Properties.
 * Required keys: API_BASE_URL, API_VERSION, API_KEY
 */
function getConfig_() {
  var props = PropertiesService.getScriptProperties();
  var base = (props.getProperty('API_BASE_URL') || '').trim();
  var version = (props.getProperty('API_VERSION') || '').trim();
  var key = (props.getProperty('API_KEY') || '').trim();

  if (!base || !version || !key) {
    throw new Error('Missing Script Properties. Please set API_BASE_URL, API_VERSION, and API_KEY in File > Project properties > Script properties.');
  }

  // Remove trailing slash to ensure consistent joining
  if (base.endsWith('/')) {
    base = base.slice(0, -1);
  }

  return { base: base, version: version, key: key };
}

/**
 * Builds full API URL using Script Properties and optional query parameters.
 * @param {string} resource - e.g., 'callstat' or 'asrstat'
 * @param {Object<string,string>=} query - key/value pairs for query string
 */
function buildApiUrl_(resource, query) {
  var cfg = getConfig_();
  var path = cfg.base + '/api/' + encodeURIComponent(cfg.version) + '/' + encodeURIComponent(cfg.key) + '/' + encodeURIComponent(resource);
  if (!query || Object.keys(query).length === 0) {
    return path;
  }
  var parts = [];
  for (var k in query) {
    if (query.hasOwnProperty(k) && query[k] !== undefined && query[k] !== null) {
      parts.push(encodeURIComponent(k) + '=' + encodeURIComponent(String(query[k])));
    }
  }
  return parts.length ? (path + '?' + parts.join('&')) : path;
}

function importLastShiftData() {
  try {
    // Calculate dates
    var today = new Date();
    var yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);

    // Format dates as YYYY-MM-DD
    var yesterdayStr = Utilities.formatDate(yesterday, Session.getTimeZone(), 'yyyy-MM-dd');
    var todayStr = Utilities.formatDate(today, Session.getTimeZone(), 'yyyy-MM-dd');

    // Build start and end strings
    var startDateTime = yesterdayStr + ' 08:00';  // Yesterday at 08:00
    var endDateTime = todayStr + ' 04:00';        // Today at 04:00

    // Call the import function
    importCallStatsWithDateRange(startDateTime, endDateTime);
  } catch (error) {
    showAlertSafe('Error: ' + error.toString());
  }
}