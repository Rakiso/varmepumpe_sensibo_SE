# Standard library imports
from datetime import datetime, timezone, timedelta
import logging
import os
import json
from functools import wraps
from typing import Optional, Dict, Any

# Third party imports
from flask import Flask, jsonify, request, render_template, session, redirect, url_for
from flask_cors import CORS
import requests
import pytz
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration constants
SENSIBO_API_KEY = os.getenv('SENSIBO_API_KEY')
SENSIBO_DEVICE_ID = os.getenv('SENSIBO_DEVICE_ID')
SENSIBO_API_BASE = "https://home.sensibo.com/api/v2"
PRIS_KLASSE = os.getenv('PRIS_KLASSE', 'SE3')
MIN_TEMP = int(os.getenv('MIN_TEMP', 10))
DEFAULT_TEMP = int(os.getenv('DEFAULT_TEMP', 22))
THRESHOLD_FILE = 'threshold.json'

# Configure Flask app
app = Flask(__name__)
CORS(app)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', os.urandom(24))
app.config['SESSION_COOKIE_SECURE'] = False

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s: %(message)s',
    handlers=[logging.StreamHandler(), logging.FileHandler('app.log')]
)
logger = logging.getLogger(__name__)

# Helper functions
def get_cet_time() -> datetime:
    """Get current time in CET/CEST timezone"""
    try:
        utc_now = datetime.now(timezone.utc)
        cet_tz = pytz.timezone('Europe/Stockholm')
        return utc_now.astimezone(cet_tz)
    except Exception as e:
        logger.error(f"Error getting CET time: {e}")
        return datetime.now()

def load_threshold() -> float:
    """Load price threshold from file"""
    try:
        if os.path.exists(THRESHOLD_FILE):
            with open(THRESHOLD_FILE, 'r') as f:
                data = json.load(f)
                return data.get("price_threshold", 5.0)
        else:
            return 5.0
    except Exception as e:
        logger.error(f"Error loading threshold: {e}")
        return 5.0

def save_threshold(price_threshold: float) -> None:
    """Save price threshold to file"""
    try:
        threshold = {"price_threshold": price_threshold}
        with open(THRESHOLD_FILE, 'w') as f:
            json.dump(threshold, f)
        logger.info("Threshold saved successfully.")
    except Exception as e:
        logger.error(f"Error saving threshold: {e}")

def control_heat_pump(turn_on: bool) -> bool:
    """Control the heat pump via Sensibo API."""
    try:
        if not SENSIBO_API_KEY or not SENSIBO_DEVICE_ID:
            logger.error("Missing Sensibo API credentials")
            return False

        url = f"{SENSIBO_API_BASE}/pods/{SENSIBO_DEVICE_ID}/acStates"
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        params = {'apiKey': SENSIBO_API_KEY}

        # Increase timeout and add retries for reliability
        session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(max_retries=2)
        session.mount('https://', adapter)
        
        # Build payload
        payload = {
            'acState': {
                'on': turn_on,
                'targetTemperature': DEFAULT_TEMP if turn_on else MIN_TEMP,
                'mode': 'heat' if turn_on else 'fan',
                'fanLevel': 'auto',
                'swing': 'stopped'
            }
        }

        logger.debug(f"Sending request to Sensibo API: {url}")
        
        # Increased timeout to 30 seconds
        response = session.post(
            url, 
            headers=headers,
            params=params, 
            json=payload,
            timeout=30
        )
        
        response.raise_for_status()
        logger.info(f"Heat pump turned {'on' if turn_on else 'off'}.")
        return True
        
    except requests.exceptions.Timeout:
        logger.error("Timeout while connecting to Sensibo API - increased timeout might be needed")
        return False
    except requests.exceptions.ConnectionError:
        logger.error("Connection error while connecting to Sensibo API")
        return False
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error controlling heat pump: {str(e)}")
        return False

def check_price_and_control_heat_pump(current_price: float) -> None:
    """Check the current price against the threshold and control the heat pump."""
    price_threshold = load_threshold()

    if price_threshold is None:
        logger.error("Invalid threshold price")
        return

    if current_price <= price_threshold:
        control_heat_pump(True)
    else:
        control_heat_pump(False)

# Authentication decorator
def login_required(func):
    @wraps(func)
    def decorated_view(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return func(*args, **kwargs)
    return decorated_view

# Routes - Authentication
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form.get('password') == os.getenv('ADMIN_PASSWORD'):
            session['logged_in'] = True
            return redirect(url_for('index'))
        return render_template('login.html', error=True)
    return render_template('login.html', error=False)

# Routes - Main views
@app.route('/')
@login_required
def index():
    return render_template('index.html')

# Routes - API endpoints
@app.route('/api/strompris', methods=['GET'])
@login_required
def strompris():
    try:
        # Fetch the current electricity price
        price = get_current_price()
        if price is not None:
            check_price_and_control_heat_pump(price)
            return jsonify({"pris": price})
        else:
            return jsonify({"error": "Failed to fetch electricity price"}), 500
    except Exception as e:
        logger.error(f"Error fetching electricity price: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/api/get_threshold', methods=['GET'])
@login_required
def get_threshold():
    try:
        threshold = load_threshold()
        return jsonify({"price_threshold": threshold})
    except Exception as e:
        logger.error(f"Error fetching threshold: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/api/set_threshold', methods=['POST'])
@login_required
def set_threshold():
    try:
        data = request.get_json()
        price_threshold = data.get('price_threshold')
        if price_threshold is not None:
            save_threshold(price_threshold)
            return jsonify({"status": "Threshold updated"})
        else:
            return jsonify({"error": "Invalid input"}), 400
    except Exception as e:
        logger.error(f"Error setting threshold: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/api/turn_on', methods=['POST'])
@login_required
def turn_on():
    try:
        success = control_heat_pump(True)
        if success:
            return jsonify({"status": "Heat pump turned on"})
        else:
            return jsonify({"error": "Failed to turn on heat pump"}), 500
    except Exception as e:
        logger.error(f"Error turning on heat pump: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/api/turn_off', methods=['POST'])
@login_required
def turn_off():
    try:
        success = control_heat_pump(False)
        if success:
            return jsonify({"status": "Heat pump turned off"})
        else:
            return jsonify({"error": "Failed to turn off heat pump"}), 500
    except Exception as e:
        logger.error(f"Error turning off heat pump: {e}")
        return jsonify({"error": "Internal server error"}), 500

# Ensure this is part of your app.py

# Function to get the current electricity price
def get_current_price() -> Optional[float]:
    try:
        dato = get_cet_time()
        år = dato.year
        måned = f"{dato.month:02d}"
        dag = f"{dato.day:02d}"
        time = dato.hour

        pris_url = f"https://www.elprisetjustnu.se/api/v1/prices/{år}/{måned}-{dag}_{PRIS_KLASSE}.json"
        logger.debug(f"Fetching price from: {pris_url}")
        
        respons = requests.get(pris_url, timeout=10)
        respons.raise_for_status()
        
        strømpriser = respons.json()
        
        if isinstance(strømpriser, list) and len(strømpriser) > time:
            nåværende_pris = strømpriser[time]["SEK_per_kWh"]
            nåværende_pris = round(nåværende_pris * 100, 2)  # Convert to øre/kWh
            logger.info(f"Current price: {nåværende_pris:.2f} øre/kWh")
            return nåværende_pris
        else:
            logger.error(f"No price data for hour {time}")
            return None
            
    except Exception as e:
        logger.error(f"Error fetching price: {e}")
        return None

if __name__ == '__main__':
    app.run(debug=True, port=5001)