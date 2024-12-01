from flask import Flask, jsonify, request, render_template, session, redirect, url_for
from flask_cors import CORS
import requests
import datetime
import logging
from dotenv import load_dotenv
from functools import wraps
import os

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)

# Sensibo API configuration from env
SENSIBO_API_KEY = os.getenv('SENSIBO_API_KEY')
SENSIBO_DEVICE_ID = os.getenv('SENSIBO_DEVICE_ID')
SENSIBO_API_BASE = "https://home.sensibo.com/api/v2"

# Configuration from env
MIN_TEMP = int(os.getenv('MIN_TEMP', 10))
DEFAULT_TEMP = int(os.getenv('DEFAULT_TEMP', 22))
pris_start = int(os.getenv('PRIS_START', 5))  # Change default here
pris_stopp = int(os.getenv('PRIS_STOPP', 10))
PRIS_KLASSE = os.getenv('PRIS_KLASSE', 'SE3')

# Add secret key for sessions
app.secret_key = os.environ.get('FLASK_SECRET_KEY', os.urandom(24))

# Login decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def set_ac_state(state: bool, temperature: int = DEFAULT_TEMP):
    """Helper function to control AC state using Sensibo API"""
    try:
        headers = {
            'Accept-Encoding': 'gzip, deflate',
            'Content-Type': 'application/json'
        }
        
        # First verify device exists and get current temperature
        verify_url = f"{SENSIBO_API_BASE}/users/me/pods"
        params = {
            "apiKey": SENSIBO_API_KEY,
            "fields": "*"
        }
        verify_response = requests.get(
            verify_url, 
            params=params, 
            headers=headers, 
            timeout=5
        )
        verify_response.raise_for_status()
        
        # Check current temperature before starting
        if state and temperature < MIN_TEMP:
            logger.warning(f"Temperature {temperature}°C below minimum {MIN_TEMP}°C - not starting")
            return False
            
        # Set AC state using correct device ID
        url = f"{SENSIBO_API_BASE}/pods/{SENSIBO_DEVICE_ID}/acStates"
        data = {
            "acState": {
                "on": state,
                "targetTemperature": temperature if state else DEFAULT_TEMP
            }
        }
        
        response = requests.post(
            url, 
            params={"apiKey": SENSIBO_API_KEY}, 
            json=data,
            headers=headers,
            timeout=5
        )
        response.raise_for_status()
        logger.info(f"Successfully set AC state to: {state} at {temperature}°C")
        return True
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to set AC state to {state}: {e}")
        if hasattr(e, 'response') and e.response:
            logger.error(f"Response content: {e.response.text}")
        return False

# Add new function for temperature control
def set_ac_temperature(temperature: int):
    """Helper function to control AC temperature"""
    try:
        headers = {
            'Accept-Encoding': 'gzip, deflate',
            'Content-Type': 'application/json'
        }
        
        url = f"{SENSIBO_API_BASE}/pods/{SENSIBO_DEVICE_ID}/acStates"
        data = {
            "acState": {
                "on": True,  # Ensure AC is on when setting temperature
                "targetTemperature": temperature
            }
        }
        
        response = requests.post(
            url, 
            params={"apiKey": SENSIBO_API_KEY}, 
            json=data,
            headers=headers,
            timeout=5
        )
        response.raise_for_status()
        logger.info(f"Successfully set temperature to: {temperature}°C")
        return True
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to set temperature to {temperature}: {e}")
        if hasattr(e, 'response') and e.response:
            logger.error(f"Response content: {e.response.text}")
        return False

def hent_strompris():
    time = datetime.datetime.now().hour
    dato = datetime.datetime.now()
    år = dato.year
    måned = f"{dato.month:02d}"
    dag = f"{dato.day:02d}"

    pris_url = f"https://www.elprisetjustnu.se/api/v1/prices/{år}/{måned}-{dag}_{PRIS_KLASSE}.json"
    logger.debug(f"Fetching price from: {pris_url}")
    
    try:
        respons = requests.get(pris_url, timeout=10)
        respons.raise_for_status()
        
        strømpriser = respons.json()
        
        if isinstance(strømpriser, list) and len(strømpriser) > time:
            nåværende_pris = strømpriser[time]["SEK_per_kWh"]
            nåværende_pris = round(nåværende_pris * 100, 2)  # Convert to öre/kWh
            logger.info(f"Current price: {nåværende_pris:.2f} öre/kWh")
            
            # Check price against thresholds
            if nåværende_pris > pris_stopp:
                logger.info(f"Price {nåværende_pris:.2f} exceeds stop threshold {pris_stopp}")
                if slå_av_varmepumpe():
                    logger.info("Heat pump stopped due to high price")
            elif nåværende_pris < pris_start:
                logger.info(f"Price {nåværende_pris:.2f} below start threshold {pris_start}")
                if slå_på_varmepumpe():
                    logger.info("Heat pump started due to low price")
            
            return nåværende_pris
        else:
            logger.error(f"No price data for hour {time}")
            return None
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed: {e}")
        return None

@app.route('/api/slå_av_varmepumpe', methods=['POST'])
def slå_av_varmepumpe():
    if set_ac_state(False):
        return jsonify({"status": "Varmepumpen er slått av"})
    return jsonify({"error": "Kunne ikke slå av varmepumpen"}), 500

@app.route('/api/slå_på_varmepumpe', methods=['POST'])
def slå_på_varmepumpe():
    if set_ac_state(True):
        return jsonify({"status": "Varmepumpen er slått på"})
    return jsonify({"error": "Kunne ikke slå på varmepumpen"}), 500

@app.route('/api/set_terskel', methods=['POST'])
def set_terskel():
    global pris_start, pris_stopp
    data = request.get_json()
    
    if not data or 'pris_start' not in data or 'pris_stopp' not in data:
        return jsonify({"error": "Missing price thresholds"}), 400
        
    try:
        new_start = float(data['pris_start'])
        new_stopp = float(data['pris_stopp'])
        
        if new_start <= 0 or new_stopp <= 0:
            return jsonify({"error": "Thresholds must be positive"}), 400
        if new_start >= new_stopp:
            return jsonify({"error": "Start price must be lower than stop price"}), 400
            
        pris_start = new_start
        pris_stopp = new_stopp
        logger.info(f"New thresholds set: start={pris_start}, stop={pris_stopp} öre/kWh")
        return jsonify({
            "status": "Thresholds updated", 
            "start": pris_start,
            "stop": pris_stopp
        })
        
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid threshold values"}), 400

@app.route('/api/device-info', methods=['GET'])
def get_device_info():
    try:
        url = f"{SENSIBO_API_BASE}/pods/{SENSIBO_DEVICE_ID}"  # Base device info endpoint
        params = {"apiKey": SENSIBO_API_KEY, "fields": "measurements,acState"}  # Request specific fields
        response = requests.get(url, params=params)
        response.raise_for_status()
        return jsonify(response.json())
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to get device info: {e}")
        return jsonify({"error": "Could not fetch device info"}), 500

@app.route('/api/strompris', methods=['GET'])
def strompris():
    try:
        logger.debug("Received request for strompris")
        nåværende_pris = hent_strompris()
        
        if nåværende_pris is not None:
            logger.info(f"Retrieved price: {nåværende_pris}")
            return jsonify({"pris": nåværende_pris})
            
        logger.error("Failed to get price")
        return jsonify({"error": "Kunne ikke hente strømpris"}), 500
    except Exception as e:
        logger.error(f"Error in strompris: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

# Add new route for temperature control
@app.route('/api/set_temperature', methods=['POST'])
def set_temperature():
    try:
        data = request.get_json()
        if not data or 'temperature' not in data:
            return jsonify({"error": "Missing temperature parameter"}), 400
            
        temperature = int(data['temperature'])
        if not (16 <= temperature <= 30):  # Common AC temperature range
            return jsonify({"error": "Temperature must be between 16 and 30"}), 400
            
        if set_ac_temperature(temperature):
            return jsonify({"status": f"Temperature set to {temperature}°C"})
        return jsonify({"error": "Could not set temperature"}), 500
        
    except ValueError:
        return jsonify({"error": "Invalid temperature value"}), 400

# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    app.logger.debug(f"Login route accessed, method: {request.method}")
    
    if request.method == 'POST':
        entered_password = request.form.get('password')
        correct_password = os.getenv('ADMIN_PASSWORD')
        
        app.logger.debug("Checking password")
        
        if entered_password == correct_password:
            app.logger.info("Login successful")
            session['logged_in'] = True
            session.permanent = True  # Make session persistent
            return redirect(url_for('index'))
        
        app.logger.warning("Invalid password attempt")
        return render_template('login.html', error=True)
    
    return render_template('login.html', error=False)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# Protected main route
@app.route('/')
@login_required
def index():
    if 'logged_in' not in session:
        app.logger.debug("No session found, redirecting to login")
        return redirect(url_for('login'))
    app.logger.debug("Session found, rendering index")
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True, port=5001)
