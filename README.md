# NTES Client Documentation

Complete Python interface for India's National Train Enquiry System (NTES)

---

## Overview

NTES Client is an unofficial Python library that provides programmatic access to Indian Railways' National Train Enquiry System. It handles all the complexity of encrypted communication, request formatting, and response parsing.

**Key Features:**
- 🔐 Automatic encryption/decryption handling
- 🚂 Full train search and tracking capabilities
- 📍 Live station boards
- ⏱️ Real-time train status
- 🚉 Route planning between stations
- 🎫 PNR status checking with auto-captcha solving
- 🔄 Automatic retry logic
- 🎯 Clean, minimal API surface

---

## Installation

```bash
pip install ntes-client
```

**Dependencies:**
- `requests` - HTTP client
- `pycryptodome` - Encryption support

Both are installed automatically.

---

## Quick Start

```python
from ntes import NTESClient

# Initialize client
client = NTESClient()

# Search for trains
trains = client.search("rajdhani")

# Get live train status
status = client.live_status("12301", "02-May-2026")

# Check station departures
departures = client.station_live("NDLS", hours=4)

# Find trains between two stations
trains_list = client.trains_between("LKO", "GZB")

# Check PNR status
pnr = client.pnr_status("8106636505")
```

---

## API Reference

### Client Initialization

```python
NTESClient(timeout=10, retries=2)
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `timeout` | `int` | `10` | Request timeout in seconds |
| `retries` | `int` | `2` | Number of retry attempts on failure |

**Example:**
```python
# Default settings
client = NTESClient()

# Custom configuration
client = NTESClient(timeout=15, retries=3)
```

---

### Methods

#### `search(query: str)`

Search for trains by number, name, or keyword.

**Parameters:**
- `query` (str): Search term (train number, name, or partial match)

**Returns:** Dict containing matching trains

**Example:**
```python
result = client.search("rajdhani")
# Returns:
# {
#   "Trains": [
#     {
#       "TrainNumber": "12301",
#       "TrainName": "KOLKATA RAJDHANI",
#       "Source": "NDLS",
#       "Destination": "HWH",
#       "SourceName": "NEW DELHI",
#       "DestinationName": "HOWRAH JN"
#     }
#   ],
#   "TrainNoName": "RAJDHANI"
# }
```

**Use Cases:**
- Find train number from partial name
- Discover trains on specific routes
- Validate train existence

---

#### `train_info(train_no: str)`

Get detailed information about a specific train.

**Parameters:**
- `train_no` (str): 5-digit train number

**Returns:** Dict with train details and instances

**Example:**
```python
info = client.train_info("12301")
# Returns:
# {
#   "TrainNo": "12301",
#   "TrainName": "KOLKATA RAJDHANI",
#   "Src": "NDLS",
#   "Dstn": "HWH",
#   "vInstanceList": [
#     {
#       "trainStatus": 0,
#       "trainPosition": "Yet to start from its source",
#       "startDate": "02-May-2026"
#     }
#   ]
# }
```

**Response Fields:**
- `TrainNo`: Train number
- `TrainName`: Full train name
- `Src`: Source station code
- `Dstn`: Destination station code
- `vInstanceList`: Recent/upcoming train instances

---

#### `schedule(train_no: str, start_date: str = "")`

Retrieve complete train schedule with all stops.

**Parameters:**
- `train_no` (str): 5-digit train number
- `start_date` (str, optional): Date in `DD-MMM-YYYY` format (e.g., "02-May-2026")

**Returns:** Dict with schedule details

**Example:**
```python
schedule = client.schedule("12301")
# Returns:
# {
#   "TrainNumber": "12301",
#   "TravelTime": "17:30",
#   "DaysOfRun": "Daily",
#   "stations": [
#     {
#       "StationCode": "NDLS",
#       "StationName": "NEW DELHI",
#       "STA": "Source",
#       "STD": "16:35",
#       "Distance": "0",
#       "Day": "1"
#     },
#     {
#       "StationCode": "CNB",
#       "StationName": "KANPUR CENTRAL",
#       "STA": "22:00",
#       "STD": "22:05",
#       "Distance": "441",
#       "Day": "1"
#     }
#   ]
# }
```

**Response Fields:**
- `TravelTime`: Total journey duration
- `DaysOfRun`: Operating days
- `stations[]`: List of all stops
  - `STA`: Scheduled Time of Arrival
  - `STD`: Scheduled Time of Departure
  - `Distance`: From source (km)
  - `Day`: Journey day number

---

#### `station_live(station_code: str, hours: int = 2)`

Get live train movements at a station.

**Parameters:**
- `station_code` (str): 3-5 character station code (e.g., "NDLS", "LKO")
- `hours` (int, optional): Time window in hours (default: 2)

**Returns:** Dict with arriving/departing trains

**Example:**
```python
live = client.station_live("NDLS", hours=4)
# Returns:
# {
#   "TrainsAtStation": [
#     {
#       "TrainNumber": "12301",
#       "TrainName": "KOLKATA RAJDHANI",
#       "ETA": "16:30",
#       "ETD": "16:35",
#       "Platform": "16",
#       "DelayArr": "On Time",
#       "DelayDep": "On Time"
#     }
#   ]
# }
```

**Response Fields:**
- `ETA`: Expected Time of Arrival
- `ETD`: Expected Time of Departure
- `Platform`: Platform number
- `DelayArr`: Arrival delay status
- `DelayDep`: Departure delay status

---

#### `live_status(train_no: str, start_date: str)`

Track real-time position and status of a running train.

**Parameters:**
- `train_no` (str): 5-digit train number
- `start_date` (str): Journey start date in `DD-MMM-YYYY` format

**Returns:** Dict with current train status

**Example:**
```python
status = client.live_status("12301", "02-May-2026")
# Returns:
# {
#   "TrainNo": "12301",
#   "TrainName": "KOLKATA RAJDHANI",
#   "CurrentStation": "CNB",
#   "CurrentStationName": "KANPUR CENTRAL",
#   "LastUpdate": "Train has departed from KANPUR CENTRAL",
#   "DelayDep": "On Time",
#   "Platform": "4",
#   "NextStationCode": "ALD",
#   "NextStationName": "ALLAHABAD JN"
# }
```

**Common Status Messages:**
- `"Yet to start from its source"`
- `"Train has departed from [STATION]"`
- `"Train has arrived at [STATION]"`
- `"Train is running late by [X] minutes"`

---

#### `exceptions(train_no: str)`

Get cancellation, diversion, or rescheduling information.

**Parameters:**
- `train_no` (str): 5-digit train number

**Returns:** Dict with exception details or alert message

**Example:**
```python
exc = client.exceptions("12301")
# Returns (no exceptions):
# {
#   "AlertMsg": "No Exceptional Details found for train 12301 !!!"
# }

# Returns (with exceptions):
# {
#   "Exceptions": [
#     {
#       "ExceptionDate": "05-May-2026",
#       "ExceptionType": "CANCELLED"
#     }
#   ]
# }
```

---

#### `pnr_status(pnr: str)`

Check PNR (Passenger Name Record) booking status with automatic captcha solving.

**Parameters:**
- `pnr` (str): 10-digit PNR number

**Returns:** Dict with booking details and passenger status

**Important Notes:**
- Uses a different endpoint (`indianrail.gov.in`) than other NTES methods
- Automatically solves captcha challenges
- May require multiple retry attempts due to captcha validation
- Subject to higher failure rates than standard NTES endpoints

**Example (Success):**
```python
pnr = client.pnr_status("8106636505")
# Returns:
# {
#   "PNR": "8106636505",
#   "status": "successful",
#   "train": [
#     {
#       "trainName": "XYZ EXPRESS",
#       "trainNumber": "12345",
#       "sourceStation": "NDLS",
#       "destinationStation": "BCT",
#       "dateOfJourney": "03-05-2026"
#     }
#   ],
#   "passengers": [
#     {
#       "bookingStatus": "CNF-12",
#       "currentStatus": "CNF-12",
#       "passengerSerialNumber": "1"
#     }
#   ],
#   "other_info": [
#     {"bookingFare": "450"},
#     {"chartStatus": "Prepared"}
#   ]
# }
```

**Common Error Responses:**

Invalid PNR:
```python
# {
#   "errorMessage": "PNR No. is not valid",
#   "serverId": "appserver",
#   "generatedTimeStamp": {
#     "year": 2026,
#     "month": 5,
#     "day": 3,
#     "hour": 2,
#     "minute": 35,
#     "second": 32
#   }
# }
```

Flushed/Old PNR:
```python
# {
#   "errorMessage": "FLUSHED PNR / PNR NOT YET GENERATED"
# }
```

Captcha Failed (retries automatically):
```python
# {
#   "errorMessage": "Captcha not matched"
# }
```

**Booking Status Codes:**
- `CNF`: Confirmed (with berth/seat number)
- `RAC`: Reservation Against Cancellation
- `WL`: Waitlisted
- `RLWL`: Remote Location Waiting List
- `PQWL`: Pooled Quota Waiting List

**Chart Status:**
- `Not Prepared`: Chart not yet prepared
- `Prepared`: Final chart published

---

#### `trains_between(from_station: str, to_station: str)`

Find all trains running between two stations with schedule and timing details.

**Parameters:**
- `from_station` (str): Source station code (e.g., "LKO", "NDLS")
- `to_station` (str): Destination station code (e.g., "GZB", "HWH")

**Returns:** Dict with list of trains and station information

**Example:**
```python
trains = client.trains_between("LKO", "GZB")
# Returns:
# {
#   "Trains": [
#     {
#       "TrainNumber": "12419",
#       "TrainName": "GOMTI EXPRESS",
#       "Source": "LKO",
#       "Destination": "NDLS",
#       "FromStation": "LKO",
#       "toStation": "GZB",
#       "FromStationName": "LUCKNOW JN.",
#       "ToStationName": "GHAZIABAD",
#       "DepTimeFrom": "05:45",
#       "ArrTimeTo": "14:13",
#       "TravelTime": "08:28",
#       "DayOfRun": "Daily",
#       "TrainType": "SUF",
#       "TrainTypeDesc": "Superfast",
#       "ClassOfTravel": ""
#     }
#   ],
#   "StationFrom": "LUCKNOW JN.",
#   "StationFromCode": "LKO",
#   "StationTo": "GHAZIABAD",
#   "StationToCode": "GZB",
#   "TotalTrains": 40
# }
```

**Response Fields:**
- `Trains[]`: List of trains with detailed information
  - `TrainNumber`: Train number
  - `TrainName`: Train name
  - `Source`: Journey origin station
  - `Destination`: Journey final station
  - `FromStation`: Your boarding station
  - `toStation`: Your destination station
  - `DepTimeFrom`: Departure time from boarding station
  - `ArrTimeTo`: Arrival time at destination station
  - `TravelTime`: Duration between stations (HH:MM)
  - `DayOfRun`: Operating days (e.g., "Daily", "Mon,Wed,Fri")
  - `TrainType`: Train category code (SUF, MEX, etc.)
  - `ClassOfTravel`: Available classes (e.g., "1A,2A,3A,SL")
- `TotalTrains`: Number of trains found
- `StationFrom/To`: Station names and codes

**Use Cases:**
- Plan journeys between two cities
- Compare train options and timings
- Find fastest or most convenient trains
- Check available train types and classes

**Train Type Codes:**
- `SUF`: Superfast
- `MEX`: Mail Express
- `SHT`: Shatabdi
- `RAJ`: Rajdhani
- `TEJ`: Tejas
- `AMTB`: Amrit Bharat
- `TOD`: Train On Demand

---

## Error Handling

The library uses custom exceptions for clear error categorization.

### Exception Types

```python
from ntes import NTESError, NTESCryptoError

# NTESError - General API/network errors
# NTESCryptoError - Encryption/decryption failures
```

### Error Handling Pattern

```python
from ntes import NTESClient, NTESError

client = NTESClient()

try:
    data = client.train_info("99999")
except NTESError as e:
    print(f"Error: {e}")
    # Handle gracefully
```

### Common Error Scenarios

| Error | Cause | Solution |
|-------|-------|----------|
| `"empty response"` | NTES server issue | Retry after delay |
| `"invalid json response"` | Malformed data | Report as bug |
| `"request failed"` | Network timeout | Check connectivity |
| Train/station alerts | Invalid code | Verify input |

### Best Practices

```python
import time
from ntes import NTESClient, NTESError

def fetch_with_retry(client, train_no, max_attempts=3):
    """Robust fetching with exponential backoff"""
    for attempt in range(max_attempts):
        try:
            return client.train_info(train_no)
        except NTESError as e:
            if attempt == max_attempts - 1:
                raise
            time.sleep(2 ** attempt)  # 1s, 2s, 4s
    
client = NTESClient(timeout=15, retries=3)
data = fetch_with_retry(client, "12301")
```

---

## Advanced Usage

### Batch Operations

```python
train_numbers = ["12301", "12302", "12951", "12952"]

results = []
for train_no in train_numbers:
    try:
        info = client.train_info(train_no)
        results.append(info)
    except NTESError:
        continue  # Skip failed requests
```

### Custom Session Headers

```python
client = NTESClient()

# Add custom headers
client.session.headers.update({
    "X-Custom-Header": "value"
})
```

### Parsing Nested Responses

```python
# Extract specific data from complex responses
schedule = client.schedule("12301")

station_names = [
    station["StationName"] 
    for station in schedule.get("stations", [])
]

total_distance = schedule.get("stations", [])[-1].get("Distance", "0")
```

### Date Formatting Helper

```python
from datetime import datetime, timedelta

def format_ntes_date(dt):
    """Convert datetime to NTES format"""
    return dt.strftime("%d-%b-%Y")

# Get status for tomorrow
tomorrow = datetime.now() + timedelta(days=1)
status = client.live_status("12301", format_ntes_date(tomorrow))
```

---

## Response Field Reference

### Common Patterns

**Unavailable Data:**
```python
"**UA**"  # Data unavailable
""        # Empty/missing
"Source"  # At origin station
"Destination"  # At final station
```

**Station Codes:**
- `NDLS` - New Delhi
- `HWH` - Howrah Junction
- `CSTM` - Mumbai CST
- `MAS` - Chennai Central
- `LKO` - Lucknow

**Date Format:**
- Input/Output: `DD-MMM-YYYY` (e.g., `02-May-2026`)
- Day names: Full lowercase (`monday`) or abbreviated (`Mon,Tue`)

---

## Real-World Examples

### 1. Track Multiple Trains

```python
from ntes import NTESClient

client = NTESClient()

trains_to_track = {
    "12301": "Rajdhani",
    "12951": "Superfast",
    "22691": "Express"
}

for train_no, name in trains_to_track.items():
    try:
        status = client.live_status(train_no, "02-May-2026")
        print(f"{name}: {status.get('LastUpdate')}")
    except Exception as e:
        print(f"{name}: Error - {e}")
```

### 2. Station Departure Board

```python
def get_departures(station_code, hours=4):
    client = NTESClient()
    data = client.station_live(station_code, hours)
    
    trains = data.get("TrainsAtStation", [])
    for train in trains:
        print(f"{train['TrainNumber']} - {train['TrainName']}")
        print(f"Departs: {train['ETD']} | Platform: {train['Platform']}")
        print(f"Status: {train.get('DelayDep', 'N/A')}\n")

get_departures("NDLS")
```

### 3. Journey Planner

```python
def plan_journey(train_no, from_station, to_station):
    client = NTESClient()
    schedule = client.schedule(train_no)
    
    stations = schedule.get("stations", [])
    route = []
    
    capture = False
    for station in stations:
        if station["StationCode"] == from_station:
            capture = True
        
        if capture:
            route.append({
                "station": station["StationName"],
                "arrival": station.get("STA", "N/A"),
                "departure": station.get("STD", "N/A"),
                "distance": station["Distance"]
            })
        
        if station["StationCode"] == to_station:
            break
    
    return route

journey = plan_journey("12301", "NDLS", "CNB")
for stop in journey:
    print(f"{stop['station']} - Arr: {stop['arrival']} Dep: {stop['departure']}")
```

### 4. Train Alert System

```python
import time
from datetime import datetime

def monitor_train(train_no, start_date, check_interval=300):
    """Monitor train and alert on delays"""
    client = NTESClient()
    
    while True:
        try:
            status = client.live_status(train_no, start_date)
            delay = status.get("DelayDep", "On Time")
            
            if delay != "On Time":
                print(f"ALERT: Train {train_no} - {delay}")
                # Send notification (email, SMS, etc.)
            else:
                print(f"Train {train_no}: {status.get('LastUpdate')}")
            
            time.sleep(check_interval)
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(60)

# Check every 5 minutes
monitor_train("12301", "02-May-2026", check_interval=300)
```

### 5. PNR Status Checker

```python
from ntes import NTESClient, NTESError

def check_pnr_with_details(pnr):
    """Check PNR and display formatted results"""
    client = NTESClient()
    
    try:
        result = client.pnr_status(pnr)
        
        # Check for errors
        if "errorMessage" in result:
            print(f"Error: {result['errorMessage']}")
            return None
        
        # Extract train info
        train = result.get("train", [{}])[0]
        print(f"\n{'='*50}")
        print(f"PNR: {result['PNR']}")
        print(f"Train: {train.get('trainNumber')} - {train.get('trainName')}")
        print(f"Route: {train.get('sourceStation')} → {train.get('destinationStation')}")
        print(f"Journey Date: {train.get('dateOfJourney')}")
        print(f"{'='*50}\n")
        
        # Display passenger details
        passengers = result.get("passengers", [])
        for i, passenger in enumerate(passengers, 1):
            print(f"Passenger {i}:")
            print(f"  Booking Status: {passenger.get('bookingStatus')}")
            print(f"  Current Status: {passenger.get('currentStatus')}")
            print()
        
        # Display other info
        other_info = result.get("other_info", [])
        for info_dict in other_info:
            for key, value in info_dict.items():
                print(f"{key}: {value}")
        
        return result
        
    except NTESError as e:
        print(f"Failed to check PNR: {e}")
        return None

# Usage
check_pnr_with_details("8106636505")
```

### 6. Batch PNR Checker

```python
def monitor_multiple_pnrs(pnr_list):
    """Check multiple PNRs and alert on status changes"""
    client = NTESClient()
    
    for pnr in pnr_list:
        try:
            result = client.pnr_status(pnr)
            
            if "errorMessage" in result:
                print(f"PNR {pnr}: {result['errorMessage']}")
                continue
            
            passengers = result.get("passengers", [])
            for p in passengers:
                booking = p.get("bookingStatus", "")
                current = p.get("currentStatus", "")
                
                # Alert if status improved
                if "CNF" in current and "CNF" not in booking:
                    print(f"✅ PNR {pnr}: CONFIRMED! {current}")
                elif "RAC" in current and "WL" in booking:
                    print(f"📈 PNR {pnr}: Moved to RAC - {current}")
                else:
                    print(f"PNR {pnr}: {current}")
        
        except Exception as e:
            print(f"Error checking PNR {pnr}: {e}")
        
        time.sleep(2)  # Be respectful with requests

pnrs = ["8106636505", "1234567890", "9876543210"]
monitor_multiple_pnrs(pnrs)
```

### 7. Route Finder & Comparison

```python
from ntes import NTESClient

def find_best_trains(from_station, to_station, preferred_time=None):
    """Find and rank trains by travel time"""
    client = NTESClient()
    
    result = client.trains_between(from_station, to_station)
    trains = result.get("Trains", [])
    
    if not trains:
        print(f"No trains found between {from_station} and {to_station}")
        return []
    
    print(f"\nFound {len(trains)} trains from {result['StationFrom']} to {result['StationTo']}\n")
    print(f"{'Train':<8} {'Name':<30} {'Depart':<8} {'Arrive':<8} {'Duration':<8} {'Days':<15}")
    print("="*90)
    
    # Sort by travel time
    sorted_trains = sorted(trains, key=lambda x: x.get('TravelTime', '99:99'))
    
    for train in sorted_trains[:10]:  # Show top 10
        print(f"{train['TrainNumber']:<8} {train['TrainName'][:28]:<30} "
              f"{train['DepTimeFrom']:<8} {train['ArrTimeTo']:<8} "
              f"{train['TravelTime']:<8} {train['DayOfRun']:<15}")
    
    return sorted_trains

# Usage
best_trains = find_best_trains("LKO", "NDLS")
```

### 8. Smart Journey Planner

```python
def plan_multi_city_journey(route):
    """Plan journey through multiple cities"""
    client = NTESClient()
    
    print("Multi-City Journey Planner\n")
    print("="*60)
    
    for i in range(len(route) - 1):
        from_station = route[i]
        to_station = route[i + 1]
        
        print(f"\nLeg {i+1}: {from_station} → {to_station}")
        print("-"*60)
        
        result = client.trains_between(from_station, to_station)
        trains = result.get("Trains", [])
        
        if not trains:
            print(f"⚠️  No direct trains found")
            continue
        
        # Find fastest train
        fastest = min(trains, key=lambda x: x.get('TravelTime', '99:99'))
        
        print(f"✓ Recommended: {fastest['TrainNumber']} - {fastest['TrainName']}")
        print(f"  Departure: {fastest['DepTimeFrom']} | Arrival: {fastest['ArrTimeTo']}")
        print(f"  Duration: {fastest['TravelTime']} | Runs: {fastest['DayOfRun']}")
        print(f"  Type: {fastest['TrainTypeDesc']}")

# Plan Delhi → Lucknow → Varanasi → Kolkata
route = ["NDLS", "LKO", "BSB", "HWH"]
plan_multi_city_journey(route)
```

### 9. Train Type Filter

```python
def find_trains_by_type(from_station, to_station, train_types):
    """Filter trains by type (Superfast, Rajdhani, etc.)"""
    client = NTESClient()
    
    result = client.trains_between(from_station, to_station)
    trains = result.get("Trains", [])
    
    # Filter by train type
    filtered = [t for t in trains if t.get('TrainType') in train_types]
    
    print(f"\n{len(filtered)} {'/'.join(train_types)} trains found:\n")
    
    for train in filtered:
        classes = train.get('ClassOfTravel', 'N/A')
        print(f"{train['TrainNumber']} - {train['TrainName']}")
        print(f"  {train['DepTimeFrom']} → {train['ArrTimeTo']} ({train['TravelTime']})")
        print(f"  Classes: {classes if classes else 'Check availability'}")
        print(f"  Runs: {train['DayOfRun']}\n")
    
    return filtered

# Find only Superfast and Rajdhani trains
superfast = find_trains_by_type("LKO", "NDLS", ["SUF", "RAJ"])

# Find only AC trains (Shatabdi, Rajdhani, Tejas)
premium = find_trains_by_type("LKO", "NDLS", ["SHT", "RAJ", "TEJ"])
```

### 10. Daily Commute Helper

```python
import datetime

def daily_commute_options(from_station, to_station, arrival_before="09:00"):
    """Find trains that get you to work on time"""
    client = NTESClient()
    
    result = client.trains_between(from_station, to_station)
    trains = result.get("Trains", [])
    
    # Get current day
    days_map = {
        0: "Mon", 1: "Tue", 2: "Wed", 3: "Thu",
        4: "Fri", 5: "Sat", 6: "Sun"
    }
    today = days_map[datetime.datetime.now().weekday()]
    
    # Filter trains running today and arriving before deadline
    suitable = []
    for train in trains:
        runs_today = ("Daily" in train['DayOfRun'] or 
                     today in train['DayOfRun'])
        arrives_on_time = train['ArrTimeTo'] < arrival_before
        
        if runs_today and arrives_on_time:
            suitable.append(train)
    
    print(f"\nTrains running today ({today}) arriving before {arrival_before}:\n")
    
    for train in sorted(suitable, key=lambda x: x['ArrTimeTo']):
        print(f"🚂 {train['TrainNumber']} {train['TrainName']}")
        print(f"   Depart: {train['DepTimeFrom']} → Arrive: {train['ArrTimeTo']}")
        print(f"   Duration: {train['TravelTime']}\n")
    
    return suitable

# Find morning commute options
morning_trains = daily_commute_options("LKO", "GZB", "09:00")
```

---

## Technical Details

### Reverse Engineering Methodology

This library was created through reverse engineering of the official NTES Android application.

**Tools & Environment:**
- **Device:** Google Pixel 2
- **OS:** Android 11 (API Level 30)
- **Instrumentation:** Frida (dynamic analysis)
- **Proxy:** Burp Suite (traffic interception)

**Process:**
1. Instrumented the official app using Frida
2. Intercepted encrypted traffic via Burp Suite
3. Extracted encryption keys and algorithm from app binary
4. Reverse engineered request/response format
5. Implemented clean Python interface

This methodology is documented for transparency and educational purposes.

### Encryption

NTES uses a proprietary encryption scheme:

1. **Algorithm:** AES-128 (CBC mode)
2. **Encoding:** Base64 → Hex
3. **Signature:** MD5 hash with secret key

**Payload Structure:**
```
MD5(data + secret_key) # HEX(BASE64(AES_ENCRYPT(data)))
```

The library handles all encryption/decryption automatically.

**Keys (extracted from app):**
- AES Key: `8EA4DB2CC1EB3DC5`
- IV: `7DC5EB3BB4DB6EA8`
- Secret: `645fbc1e56e23365f2f3c204ae0899f6`

### Request Flow

```
User Code
    ↓
NTESClient.method()
    ↓
Encrypt payload
    ↓
HTTP POST to NTES
    ↓
Receive encrypted response
    ↓
Decrypt & parse JSON
    ↓
Return to user
```

### Network Configuration

**NTES Endpoints:**
- **Endpoint:** `https://enquiry.indianrail.gov.in/crisns/AppServAnd`
- **Method:** POST
- **Content-Type:** `application/json`
- **User-Agent:** Android client signature
- **Used for:** Train search, schedules, live status, station boards, exceptions

**PNR Endpoint:**
- **Endpoint:** `https://indianrail.gov.in/enquiry/CommonCaptcha`
- **Method:** GET
- **Authentication:** Captcha-based validation
- **Used for:** PNR status checking only
- **Note:** Higher failure rate due to captcha requirements

---

## Limitations & Caveats

### API Stability
- **Unofficial API:** No stability guarantees
- **Schema Changes:** Response format may change without notice
- **Downtime:** Backend may be unavailable during maintenance

### Data Quality
- **Inconsistent Fields:** Not all trains return same fields
- **Missing Data:** Some fields may be empty or `**UA**`
- **Delayed Updates:** Real-time data may lag by 5-10 minutes

### Rate Limiting
- No official rate limits documented
- Recommended: Max 60 requests/minute
- Implement backoff for production use

### Legal & Ethical
- Respect NTES terms of service
- Don't overload the system
- Use for personal/research purposes
- No commercial guarantees

---

## Troubleshooting

### Common Issues

**Problem:** `"empty response"` error
```python
# Solution: Increase timeout and retries
client = NTESClient(timeout=20, retries=3)
```

**Problem:** Train not found in search
```python
# Solution: Try variations
client.search("12301")  # Number
client.search("rajdhani")  # Name
client.search("kolkata")  # Route
```

**Problem:** Stale data in live_status
```python
# Solution: Verify date format and train schedule
# Ensure train runs on specified date
info = client.train_info("12301")
# Check vInstanceList for valid dates
```

**Problem:** Missing platform information
```python
# Solution: Platform may not be announced yet
# Check closer to departure time
```

### Debug Mode

```python
import logging

# Enable detailed logging
logging.basicConfig(level=logging.DEBUG)

client = NTESClient()
# Now see all HTTP requests/responses
```

---

## Performance Tips

1. **Reuse Client Instance**
   ```python
   # Good: One client for multiple requests
   client = NTESClient()
   for train in trains:
       client.train_info(train)
   
   # Bad: New client each time
   for train in trains:
       client = NTESClient()
       client.train_info(train)
   ```

2. **Cache Responses**
   ```python
   from functools import lru_cache
   
   @lru_cache(maxsize=100)
   def get_schedule(train_no):
       return client.schedule(train_no)
   ```

3. **Parallel Requests** (Use with caution)
   ```python
   from concurrent.futures import ThreadPoolExecutor
   
   with ThreadPoolExecutor(max_workers=5) as executor:
       results = executor.map(client.train_info, train_numbers)
   ```

---

## Migration Guide

### From Direct API Calls

**Before:**
```python
import requests
# Manual encryption, parsing, error handling...
```

**After:**
```python
from ntes import NTESClient
client = NTESClient()
data = client.search("rajdhani")
```

### From Other Libraries

Most train tracking libraries have similar patterns:

```python
# Other library
from other_lib import RailClient
rail = RailClient()
rail.get_train("12301")

# NTES Client
from ntes import NTESClient
client = NTESClient()
client.train_info("12301")
```

---

## Contributing

### Development Setup

```bash
# Clone repository
git clone https://github.com/yourusername/ntes-client.git
cd ntes-client

# Install dependencies
pip install -r requirements.txt

# Run tests
pytest -v
```

### Project Structure

```
ntes-client/
├── ntes/
│   ├── __init__.py      # Package exports
│   ├── client.py        # Main client class
│   ├── crypto.py        # Encryption layer
│   ├── pnr.py           # PNR captcha solver
│   ├── exceptions.py    # Custom exceptions
│   └── utils.py         # Helper functions
├── tests/
│   ├── test_client.py   # Client tests
│   └── test_crypto.py   # Crypto tests
├── README.md
├── setup.py
└── requirements.txt
```

### Code Style

- **PEP 8** compliance
- **Type hints** for all functions
- **Docstrings** for public methods
- **Minimal dependencies**

---

## FAQ

**Q: Is this library official?**  
A: No, this is an unofficial client reverse-engineered from the mobile app.

**Q: Can I use this in production?**  
A: Use at your own risk. No uptime or accuracy guarantees.

**Q: Why do some trains return incomplete data?**  
A: NTES data quality varies. Not all trains have complete information.

**Q: How often is data updated?**  
A: Live data updates every 5-10 minutes. Schedules are relatively static.

**Q: Can I get historical data?**  
A: No, NTES only provides current and near-future data.

**Q: What about PNR status?**  
A: PNR status checking is supported via the `pnr_status()` method. Note that it uses a different backend (indianrail.gov.in) with captcha solving, so it may have higher failure rates than standard NTES methods.

**Q: How do I find trains between two stations?**  
A: Use the `trains_between(from_station, to_station)` method. It returns all trains with timings, duration, train types, and operating days. You can filter results by travel time, train type, or availability on specific days.

**Q: How do I report bugs?**  
A: Open an issue on GitHub with reproduction steps.

---

## License

This library is provided as-is for educational and personal use.

**Disclaimer:** 
- Not affiliated with Indian Railways or CRIS
- Created through reverse engineering for educational purposes
- Use responsibly and at your own risk
- Respect Indian Railways terms of service
- No commercial guarantees or warranties

**Legal Note:** This library is intended for:
- Personal train tracking
- Educational exploration
- Research purposes
- Non-commercial automation

Not intended for:
- Commercial redistribution
- High-volume scraping
- Service disruption
- Terms of service violation

---

## Support

- **Documentation:** This file
- **Issues:** GitHub issue tracker
- **Updates:** Check repository for latest version

---

## Changelog

### Version 1.1.3 (Latest)
- Added `trains_between()` method for route planning
- Find all trains between two stations with timings and details
- Filter by train type, travel time, and operating days

### Version 1.1.2
- Added support for PNR Status checking
- Automatic captcha solving for PNR queries

### Version 1.1.0
- Added fallback import for Crypto / Cryptodome
- Fixes ModuleNotFoundError on some Linux/Termux setups

### Version 1.0.0
- Initial release
- Core API methods
- Encryption handling
- Error normalization
- Retry logic

---

## Acknowledgments

This library abstracts the NTES mobile API for easier Python integration.

Special thanks to the open-source community for cryptography libraries.

---

**Last Updated:** May 2026  
**Library Version:** 1.1.3  
**Python Compatibility:** 3.7+