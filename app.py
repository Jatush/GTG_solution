from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
import os
import sqlite3
import logging
import pandas as pd
import joblib
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
from math import radians, cos, sin, sqrt, atan2
from firebase_config import db
from firebase_admin import firestore


# Initialize Flask app
app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///healthcare.db'  # configured but SQLAlchemy not used here yet
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads/prescriptions'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload size

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize geolocator once
geolocator = Nominatim(user_agent="my_medicine_app", timeout=10)

# Load ML models once at startup
model_shortage = joblib.load('medicine_shortage_model.pkl')
model_price = joblib.load('medicine_price_spike_model.pkl')

# Region, medicine and season mappings
region_map = {'Mumbai': 0, 'Delhi': 1, 'Chennai': 2, 'Kolkata': 3, 'Banglore': 4}
medicine_map = {
    'Insulin': 0, 'Thyroxine': 1, 'Metformin': 2, 'Levothyroxine': 3, 'Paracetamol': 4,
    'Amoxicillin': 5, 'Aspirin': 6, 'Atorvastatin': 7, 'Omeprazole': 8, 'Amlodipine': 9,
    'Azithromycin': 10, 'Cetrizine': 11, 'Doxycycline': 12, 'Diclofenac': 13, 'Losartan': 14,
    'Salbutamol': 15, 'Clopidogrel': 16, 'Fluconazole': 17, 'Levocetirizine': 18, 'Metronidazole': 19,
    'Montelukast': 20, 'Ciprofloxacin': 21, 'Prednisolone': 22, 'Ranitidine': 23, 'Warfarin': 24,
    'Glimepiride': 25, 'Levamisole': 26, 'Betahistine': 27, 'Norfloxacin': 28, 'Famotidine': 29,
    'Hydrochlorothiazide': 30, 'Tramadol': 31, 'Cefixime': 32, 'Clindamycin': 33, 'Olmesartan': 34,
    'Methylprednisolone': 35, 'Tiotropium': 36, 'Enalapril': 37, 'Rifampicin': 38, 'Gabapentin': 39,
    'Paroxetine': 40, 'Clonazepam': 41, 'Dexamethasone': 42, 'Mefenamic Acid': 43, 'Baclofen': 44,
    'Ondansetron': 45, 'Tadalafil': 46, 'Valacyclovir': 47, 'Etoricoxib': 48, 'Esomeprazole': 49,
    'Phenylephrine': 50, 'Mirtazapine': 51, 'Amantadine': 52, 'Azathioprine': 53, 'Betamethasone': 54,
    'Nifedipine': 55, 'Nortriptyline': 56, 'Diazepam': 57, 'Fluoxetine': 58, 'Levofloxacin': 59,
    'Nystatin': 60, 'Pregabalin': 61, 'Rosuvastatin': 62, 'Sildenafil': 63
}
season_map = {'Winter': 1, 'Summer': 5, 'Monsoon': 8}

typical_avg_daily_demand = {
    ('Mumbai', 'Insulin', 'Winter'): 50,
    ('Mumbai', 'Insulin', 'Summer'): 90,
    ('Mumbai', 'Insulin', 'Monsoon'): 70,
    ('Mumbai', 'Atorvastatin', 'Winter'): 25,
    ('Mumbai', 'Atorvastatin', 'Summer'): 35,
    ('Mumbai', 'Atorvastatin', 'Monsoon'): 30,
    ('Delhi', 'Paracetamol', 'Winter'): 110,
    ('Delhi', 'Paracetamol', 'Summer'): 80,
    ('Delhi', 'Paracetamol', 'Monsoon'): 90,
    ('Chennai', 'Amoxicillin', 'Winter'): 45,
    ('Chennai', 'Amoxicillin', 'Summer'): 55,
    ('Chennai', 'Amoxicillin', 'Monsoon'): 50,
    ('Kolkata', 'Aspirin', 'Winter'): 40,
    ('Kolkata', 'Aspirin', 'Summer'): 30,
    ('Kolkata', 'Aspirin', 'Monsoon'): 35,
    ('Banglore', 'Metformin', 'Winter'): 70,
    ('Banglore', 'Metformin', 'Summer'): 65,
    ('Banglore', 'Metformin', 'Monsoon'): 75,
}
typical_stock_level = {
    ('Mumbai', 'Insulin', 'Winter'): 20,
    ('Mumbai', 'Insulin', 'Summer'): 14,
    ('Mumbai', 'Insulin', 'Monsoon'): 3,
    ('Mumbai', 'Atorvastatin', 'Winter'): 5,
    ('Mumbai', 'Atorvastatin', 'Summer'): 8,
    ('Mumbai', 'Atorvastatin', 'Monsoon'): 7,
    ('Delhi', 'Paracetamol', 'Winter'): 20,
    ('Delhi', 'Paracetamol', 'Summer'): 12,
    ('Delhi', 'Paracetamol', 'Monsoon'): 11,
    ('Chennai', 'Amoxicillin', 'Winter'): 20,
    ('Chennai', 'Amoxicillin', 'Summer'): 9,
    ('Chennai', 'Amoxicillin', 'Monsoon'): 22,
    ('Kolkata', 'Aspirin', 'Winter'): 15,
    ('Kolkata', 'Aspirin', 'Summer'): 1,
    ('Kolkata', 'Aspirin', 'Monsoon'): 12,
    ('Banglore', 'Metformin', 'Winter'): 35,
    ('Banglore', 'Metformin', 'Summer'): 2,
    ('Banglore', 'Metformin', 'Monsoon'): 17,
}
location_cache = {
    "mumbai": (19.0760, 72.8777),
    "delhi": (28.6139, 77.2090),
    "bangalore": (12.9716, 77.5946),
    "hyderabad": (17.3850, 78.4867),
    "kolkata": (22.5726, 88.3639),
    # Add more cities if needed
}



# ------------------------
# Database helper functions
def get_db_connection():
    conn = sqlite3.connect('healthcare.db')
    conn.row_factory = sqlite3.Row
    return conn

def execute_query(query, params=None):
    conn = get_db_connection()
    try:
        if params:
            result = conn.execute(query, params).fetchall()
        else:
            result = conn.execute(query).fetchall()
        conn.commit()
        return result
    except Exception as e:
        logger.error(f"Database error: {e}")
        return None
    finally:
        conn.close()

def execute_insert(query, params):
    conn = get_db_connection()
    try:
        cursor = conn.execute(query, params)
        conn.commit()
        return cursor.lastrowid
    except Exception as e:
        logger.error(f"Database insert error: {e}")
        return None
    finally:
        conn.close()

# Correct haversine distance function
def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # Earth radius in kilometers
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c

# Authentication decorators
from functools import wraps

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_type' not in session or session['user_type'] not in roles:
                flash('Access denied. Insufficient permissions.', 'error')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# ------------------------
# Routes and Views
@app.route('/')
def index():
    return render_template('index.html')


# @app.route('/login')
# def login():
#     return render_template('login.html')


@app.route('/api/search_pharmacies', methods=['POST'])
def api_search_pharmacies():
    data = request.get_json()
    user_lat = data.get('latitude')
    user_lon = data.get('longitude')
    medicines = [m.strip().lower() for m in data.get('medicines', [])]

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT p.id, p.pharmacy_name, p.latitude, p.longitude, pm.medicine_name, pm.price
        FROM pharmacies p
        JOIN pharmacy_medicines pm ON p.id = pm.pharmacy_id
    ''')

    rows = cursor.fetchall()
    conn.close()

    results = {}
    for pid, pname, plat, plon, med_name, price in rows:
        if med_name.lower() in medicines:
            distance = haversine(user_lat, user_lon, plat, plon)
            if distance <= 20:  # 20 km radius
                if pid not in results:
                    results[pid] = {
                        "pharmacy_name": pname,
                        "latitude": plat,
                        "longitude": plon,
                        "medicines": []
                    }
                results[pid]["medicines"].append({
                    "medicine_name": med_name,
                    "price": price
                })

    if not results:
        return jsonify({"message": "No pharmacies found nearby with requested medicines."}), 404

    return jsonify({"pharmacies": list(results.values())})


location_cache = {
    "Mumbai": (19.0760, 72.8777),
    "Delhi": (28.6139, 77.2090),
    "Bangalore":(12.97,77.59),
    "Kolkata":(22.57, 88.36),
    "Hyderabad": (17.38, 78.48)
    # Add more if needed
}

@app.route('/search_pharmacies')
def search_pharmacies():
    user_location_str = request.args.get('location')
    user_location_str = user_location_str.strip().lower()
    user_latlng = location_cache.get(user_location_str)
    medicines_str = request.args.get('medicines')
    
    
    if not user_location_str or not medicines_str:
        return jsonify({"error": "Missing parameters"}), 400

    user_location_str = user_location_str.strip().title()

    user_latlng = location_cache.get(user_location_str)
    if not user_latlng:
        return jsonify({"error": "Invalid location"}), 400

    requested_medicines = [m.strip().lower() for m in medicines_str.split(',')]

    # Expanded dummy pharmacy data
    dummy_pharmacies = [
        # Mumbai
        {
            "id": 1,
            "pharmacy_name": "Test Pharmacy Mumbai",
            "address": "123 Test St, Mumbai",
            "latitude": 19.07,
            "longitude": 72.88,
            "medicine_prices": {
                "insulin": 500,
                "thyroxine": 300,
                "paracetamol": 20
            }
        },
        {
            "id": 4,
            "pharmacy_name": "mumb Care Pharmacy",
            "address": "78 Shahdara, Delhi",
            "latitude": 19.07,
            "longitude": 72.88,
            "medicine_prices": {
                "thyroxine": 310,
                "paracetamol": 25
            }
        },
        {
            "id": 2,
            "pharmacy_name": "Another Pharmacy Mumbai",
            "address": "456 Sample Rd, Mumbai",
            "latitude": 19.09,
            "longitude": 72.86,
            "medicine_prices": {
                "insulin": 520,
                "amoxicillin": 40
            }
        },
        {
            "id": 6,
            "pharmacy_name": "HealthMart Pharmacy mira bhayandar",
            "address": "50 MG Road, mmr",
            "latitude": 19.07,
            "longitude": 72.88,
            "medicine_prices": {
                "insulin": 495,
                "thyroxine": 305,
                "amoxicillin": 45
            }
        },

        {
            "id": 7,
            "pharmacy_name": "Wellness Pharmacy navi mumbai",
            "address": "22 Park Street, mmr",
            "latitude": 19.07,
            "longitude": 72.88,
            "medicine_prices": {
                "paracetamol": 23,
                "thyroxine": 320
            }
        },

        # Delhi
        {
            "id": 3,
            "pharmacy_name": "Fortis Pharmacy Delhi",
            "address": "45 Connaught Place, Delhi",
            "latitude": 28.63,
            "longitude": 77.21,
            "medicine_prices": {
                "insulin": 510,
                "amoxicillin": 42,
                "paracetamol": 22
            }
        },
        
        {
            "id": 4,
            "pharmacy_name": "Delhi Care Pharmacy",
            "address": "78 Shahdara, Delhi",
            "latitude": 28.66,
            "longitude": 77.25,
            "medicine_prices": {
                "thyroxine": 310,
                "paracetamol": 25
            }
        },
        {
            "id": 5,
            "pharmacy_name": "CarePlus Pharmacy Newdelhi",
            "address": "78 Anna Salai, ncr",
            "latitude": 28.63,
            "longitude": 77.21,
            "medicine_prices": {
                "amoxicillin": 48,
                "paracetamol": 20
            }
        },

        {
            "id": 5,
            "pharmacy_name": "CarePlus Pharmacy ncr",
            "address": "78 Anna Salai, noida",
            "latitude": 28.63,
            "longitude": 77.21,
            "medicine_prices": {
                "amoxicillin": 48,
                "paracetamol": 20
            }
        },

        # Bangalore
        {
            "id": 6,
            "pharmacy_name": "HealthMart Pharmacy Bangalore",
            "address": "50 MG Road, Bangalore",
            "latitude": 12.97,
            "longitude": 77.59,
            "medicine_prices": {
                "insulin": 495,
                "thyroxine": 305,
                "amoxicillin": 45
            }
        },

        # Kolkata
        {
            "id": 7,
            "pharmacy_name": "Wellness Pharmacy Kolkata",
            "address": "22 Park Street, Kolkata",
            "latitude": 22.57,
            "longitude": 88.36,
            "medicine_prices": {
                "paracetamol": 23,
                "thyroxine": 320
            }
        },

        # Hyderabad
        {
            "id": 8,
            "pharmacy_name": "MediCare Pharmacy Hyderabad",
            "address": "90 Banjara Hills, Hyderabad",
            "latitude": 17.38,
            "longitude": 78.48,
            "medicine_prices": {
                "insulin": 485,
                "amoxicillin": 50
            }
        }
    ]

    max_distance_km = 15
    nearby_pharmacies = []

    for pharmacy in dummy_pharmacies:
        pharmacy_latlng = (pharmacy['latitude'], pharmacy['longitude'])
        dist = geodesic(user_latlng, pharmacy_latlng).km
        if dist <= max_distance_km:
            med_prices = {med: price for med, price in pharmacy['medicine_prices'].items() if med in requested_medicines}
            if med_prices:
                nearby_pharmacies.append({
                    "pharmacy_name": pharmacy['pharmacy_name'],
                    "address": pharmacy['address'],
                    "latitude": pharmacy['latitude'],
                    "longitude": pharmacy['longitude'],
                    "medicine_prices": med_prices,
                    "distance_km": round(dist, 2)
                })

    nearby_pharmacies.sort(key=lambda x: x['distance_km'])
    print("Nearby pharmacies found:", len(nearby_pharmacies))
    if not nearby_pharmacies:
        print("No pharmacies found nearby with requested medicines.")

    return jsonify({
        "user_location": {"lat": user_latlng[0], "lng": user_latlng[1]},
        "pharmacies": nearby_pharmacies
    })



@app.route('/map')
def map():
    try:
        conn = sqlite3.connect('database.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT pharmacy_name, address, latitude, longitude FROM pharmacies")
        pharmacies = [dict(row) for row in cursor.fetchall()]
        conn.close()
    except Exception as e:
        print(f"DB Error: {e}")
        pharmacies = []  # fallback to empty list so template rendering doesn't break

    return render_template('map.html', pharmacies=pharmacies)

# @app.errorhandler(404)
# def page_not_found(e):
#     return render_template('404.html'), 404

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page for all user types"""
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = execute_query(
            'SELECT * FROM users WHERE email = ? AND is_active = TRUE',
            (email,)
        )
        
        if user and check_password_hash(user[0]['password_hash'], password):
            session['user_id'] = user[0]['id']
            session['user_type'] = user[0]['user_type']
            session['full_name'] = user[0]['full_name']
            
            flash(f'Welcome back, {user[0]["full_name"]}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password', 'error')
    
    return render_template('login.html')
from datetime import datetime

@app.template_filter('datefmt')
def datefmt(value, format="%Y-%m-%d"):
    if not value:
        return ''
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except ValueError:
            return value  # return original string if parsing fails
    return value.strftime(format)

@app.route('/predict_medicine', methods=['GET', 'POST'])
def predict_medicine():
    if request.method == 'POST':
        region = request.form.get('region')
        medicine = request.form.get('medicine')
        season = request.form.get('season')

        # Validate inputs
        if region not in region_map or medicine not in medicine_map or season not in season_map:
            flash("Invalid input", "error")
            return render_template('predict_medicine.html')

        key = (region, medicine, season)
        avg_daily_demand = typical_avg_daily_demand.get(key, 100)  # default fallback
        stock_level = typical_stock_level.get(key, 50)             # default fallback

        X = pd.DataFrame([{
            'Month': season_map[season],
            'Region_Code': region_map[region],
            'Medicine_Code': medicine_map[medicine],
            'Avg_Daily_Demand': avg_daily_demand,
            'Stock_Level': stock_level,
        }])

        shortage_pred = model_shortage.predict(X)[0]
        price_spike_pred = model_price.predict(X)[0]

        result = {
            'region': region,
            'medicine': medicine,
            'season': season,
            'shortage': int(shortage_pred),
            'price_spike': int(price_spike_pred)
        }
        return render_template('predict_medicine.html', result=result)

    # GET request
    return render_template('predict_medicine.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    """Registration page for patients and pharmacies"""
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        user_type = request.form.get('user_type')
        full_name = request.form.get('full_name')
        phone = request.form.get('phone')

        # Check if user already exists (SQL)
        existing_user = execute_query(
            'SELECT id FROM users WHERE email = ? OR username = ?',
            (email, username)
        )

        if existing_user:
            flash('User with this email or username already exists', 'error')
        else:
            password_hash = generate_password_hash(password)

            # Insert into SQL DB
            user_id = execute_insert(
                '''INSERT INTO users (username, email, password_hash, user_type, full_name, phone)
                   VALUES (?, ?, ?, ?, ?, ?)''',
                (username, email, password_hash, user_type, full_name, phone)
            )

            if user_id:
                # Also save user data in Firebase Firestore
                try:
                    firebase_user = {
                        'username': username,
                        'email': email,
                        'user_type': user_type,
                        'full_name': full_name,
                        'phone': phone,
                        # Do NOT store password or password hash in Firestore for security reasons
                    }
                    db.collection('users').document(str(user_id)).set(firebase_user)
                except Exception as e:
                    print("Firebase error:", e)
                    # Optionally flash or log error but don’t block registration success

                flash('Registration successful! Please log in.', 'success')
                return redirect(url_for('login'))
            else:
                flash('Registration failed. Please try again.', 'error')

    # Get locations for dropdown
    locations = execute_query('SELECT * FROM locations ORDER BY name')
    return render_template('register.html', locations=locations)

@app.route('/dashboard')
@login_required
def dashboard():
    """Main dashboard - redirects to appropriate user dashboard"""
    user_type = session.get('user_type')
    
    if user_type == 'admin':
        return redirect(url_for('admin_dashboard'))
    elif user_type == 'pharmacy':
        return redirect(url_for('pharmacy_dashboard'))
    elif user_type == 'patient':
        return redirect(url_for('patient_dashboard'))
    elif user_type in ['government', 'ngo']:
        return redirect(url_for('authority_dashboard'))
    else:
        flash('Unknown user type', 'error')
        return redirect(url_for('login'))

@app.route('/admin/dashboard')
@login_required
@role_required(['admin'])
def admin_dashboard():
    """Admin dashboard with system overview"""
    # Get system statistics
    stats = {
        'total_users': execute_query('SELECT COUNT(*) as count FROM users')[0]['count'],
        'total_pharmacies': execute_query('SELECT COUNT(*) as count FROM pharmacies')[0]['count'],
        'total_medicines': execute_query('SELECT COUNT(*) as count FROM medicines')[0]['count'],
        'active_alerts': execute_query('SELECT COUNT(*) as count FROM shortage_alerts WHERE is_active = TRUE')[0]['count'],
        'total_reports': execute_query('SELECT COUNT(*) as count FROM patient_reports')[0]['count']
    }
    
    # Get recent alerts
    recent_alerts = execute_query('''
        SELECT sa.*, m.name as medicine_name, l.name as location_name
        FROM shortage_alerts sa
        JOIN medicines m ON sa.medicine_id = m.id
        JOIN locations l ON sa.location_id = l.id
        WHERE sa.is_active = TRUE
        ORDER BY sa.created_at DESC LIMIT 10
    ''')
    
    # Get recent reports
    recent_reports = execute_query('''
        SELECT pr.*, m.name as medicine_name, l.name as location_name, u.full_name as reporter_name
        FROM patient_reports pr
        JOIN medicines m ON pr.medicine_id = m.id
        JOIN locations l ON pr.location_id = l.id
        LEFT JOIN users u ON pr.user_id = u.id
        ORDER BY pr.created_at DESC LIMIT 10
    ''')
    
    return render_template('admin_dashboard.html', 
                         stats=stats, 
                         recent_alerts=recent_alerts,
                         recent_reports=recent_reports)

@app.route('/pharmacy/dashboard')
@login_required
@role_required(['pharmacy'])
def pharmacy_dashboard():
    """Pharmacy dashboard for inventory management"""
    user_id = session.get('user_id')
    
    # Get pharmacy info
    pharmacy = execute_query(
        'SELECT * FROM pharmacies WHERE user_id = ?', 
        (user_id,)
    )[0] if execute_query('SELECT * FROM pharmacies WHERE user_id = ?', (user_id,)) else None
    
    if not pharmacy:
        flash('Pharmacy profile not found. Please complete your profile.', 'warning')
        return redirect(url_for('profile'))
    
    # Get inventory with low stock alerts
    inventory = execute_query('''
        SELECT pi.*, m.name as medicine_name, m.generic_name, m.brand_name, m.dosage_form, m.strength
        FROM pharmacy_inventory pi
        JOIN medicines m ON pi.medicine_id = m.id
        WHERE pi.pharmacy_id = ?
        ORDER BY pi.current_stock ASC
    ''', (pharmacy['id'],))
    
    # Get low stock items
    low_stock = [item for item in inventory if item['current_stock'] <= item['minimum_stock_level']]
    
    return render_template('pharmacy_dashboard.html', 
                         pharmacy=pharmacy,
                         inventory=inventory,
                         low_stock=low_stock)

@app.route('/patient/dashboard')
@login_required
@role_required(['patient'])
def patient_dashboard():
    """Patient dashboard for reporting and viewing medicine availability"""
    user_id = session.get('user_id')
    
    # Get user's reports
    my_reports = execute_query('''
        SELECT pr.*, m.name as medicine_name, l.name as location_name, p.pharmacy_name
        FROM patient_reports pr
        JOIN medicines m ON pr.medicine_id = m.id
        JOIN locations l ON pr.location_id = l.id
        LEFT JOIN pharmacies p ON pr.pharmacy_id = p.id
        WHERE pr.user_id = ?
        ORDER BY pr.created_at DESC
    ''', (user_id,))
    
    # Get active alerts in user's area (assuming Mumbai for now)
    active_alerts = execute_query('''
        SELECT sa.*, m.name as medicine_name, l.name as location_name
        FROM shortage_alerts sa
        JOIN medicines m ON sa.medicine_id = m.id
        JOIN locations l ON sa.location_id = l.id
        WHERE sa.is_active = TRUE
        ORDER BY sa.severity DESC, sa.created_at DESC
        LIMIT 10
    ''')
    
    return render_template('patient_dashboard.html', 
                         my_reports=my_reports,
                         active_alerts=active_alerts)

@app.route('/authority/dashboard')
@login_required
@role_required(['government', 'ngo'])
def authority_dashboard():
    """Dashboard for government bodies and NGOs"""
    # Get critical alerts
    critical_alerts = execute_query('''
        SELECT sa.*, m.name as medicine_name, l.name as location_name
        FROM shortage_alerts sa
        JOIN medicines m ON sa.medicine_id = m.id
        JOIN locations l ON sa.location_id = l.id
        WHERE sa.is_active = TRUE AND sa.severity IN ('high', 'critical')
        ORDER BY sa.severity DESC, sa.created_at DESC
    ''')
    
    # Get shortage statistics by location
    shortage_stats = execute_query('''
        SELECT l.name as location_name, COUNT(*) as alert_count, 
               AVG(sa.price_increase_percentage) as avg_price_increase
        FROM shortage_alerts sa
        JOIN locations l ON sa.location_id = l.id
        WHERE sa.is_active = TRUE
        GROUP BY l.id, l.name
        ORDER BY alert_count DESC
    ''')
    
    return render_template('authority_dashboard.html', 
                         critical_alerts=critical_alerts,
                         shortage_stats=shortage_stats)

@app.route('/report-medicine', methods=['GET', 'POST'])
@login_required
@role_required(['patient'])
def report_medicine():
    """Page for patients to report medicine issues"""
    if request.method == 'POST':
        medicine_id = request.form.get('medicine_id')
        location_id = request.form.get('location_id')
        report_type = request.form.get('report_type')
        pharmacy_id = request.form.get('pharmacy_id') or None
        reported_price = request.form.get('reported_price')
        expected_price = request.form.get('expected_price')
        description = request.form.get('description')

        # Handle prescription upload
        prescription_file = request.files.get('prescription')
        prescription_filename = None
        if prescription_file and prescription_file.filename:
            prescription_filename = secure_filename(prescription_file.filename)
            prescription_path = os.path.join(app.config['UPLOAD_FOLDER'], prescription_filename)
            prescription_file.save(prescription_path)
        else:
            prescription_path = None

        # Insert into SQL database
        report_id = execute_insert('''
            INSERT INTO patient_reports (user_id, medicine_id, location_id, report_type, 
                                       pharmacy_id, reported_price, expected_price, description)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (session['user_id'], medicine_id, location_id, report_type, 
              pharmacy_id, reported_price, expected_price, description))

        if report_id:
            # Prepare data for Firestore
            firestore_data = {
                'report_id': report_id,
                'user_id': session['user_id'],
                'medicine_id': medicine_id,
                'location_id': location_id,
                'report_type': report_type,
                'pharmacy_id': pharmacy_id,
                'reported_price': float(reported_price) if reported_price else None,
                'expected_price': float(expected_price) if expected_price else None,
                'description': description,
                'prescription_filename': prescription_filename,
                'timestamp': firestore.SERVER_TIMESTAMP  # add Firestore server timestamp
            }

            try:
                # Save to Firestore in collection 'patient_reports'
                db.collection('patient_reports').document(str(report_id)).set(firestore_data)
            except Exception as e:
                print(f"Error saving to Firestore: {e}")
                # Optionally flash or log but don’t block success

            flash('Report submitted successfully!', 'success')
            # Check if this triggers an alert
            check_and_create_alerts(medicine_id, location_id)
            return redirect(url_for('patient_dashboard'))
        else:
            flash('Failed to submit report', 'error')

    # Get data for form
    medicines = execute_query('SELECT * FROM medicines ORDER BY name')
    locations = execute_query('SELECT * FROM locations ORDER BY name')
    pharmacies = execute_query('SELECT * FROM pharmacies ORDER BY pharmacy_name')

    return render_template('report_medicine.html', 
                           medicines=medicines, 
                           locations=locations,
                           pharmacies=pharmacies)

@app.route('/inventory/manage')
@login_required
@role_required(['pharmacy'])
def manage_inventory():
    """Inventory management page for pharmacies"""
    user_id = session.get('user_id')
    pharmacy = execute_query('SELECT * FROM pharmacies WHERE user_id = ?', (user_id,))[0]
    
    # Get all medicines for adding to inventory
    medicines = execute_query('SELECT * FROM medicines ORDER BY name')
    
    # Get current inventory
    inventory = execute_query('''
        SELECT pi.*, m.name as medicine_name, m.generic_name, m.brand_name
        FROM pharmacy_inventory pi
        JOIN medicines m ON pi.medicine_id = m.id
        WHERE pi.pharmacy_id = ?
        ORDER BY m.name
    ''', (pharmacy['id'],))
    
    return render_template('manage_inventory.html', 
                         medicines=medicines, 
                         inventory=inventory,
                         pharmacy=pharmacy)

@app.route('/inventory/update', methods=['POST'])
@login_required
@role_required(['pharmacy'])
def update_inventory():
    """API endpoint to update pharmacy inventory"""
    user_id = session.get('user_id')
    pharmacy = execute_query('SELECT * FROM pharmacies WHERE user_id = ?', (user_id,))[0]
    
    medicine_id = request.form.get('medicine_id')
    current_stock = request.form.get('current_stock')
    unit_price = request.form.get('unit_price')
    mrp = request.form.get('mrp')
    batch_number = request.form.get('batch_number')
    expiry_date = request.form.get('expiry_date')
    minimum_stock_level = request.form.get('minimum_stock_level')
    
    # Check if item exists in inventory
    existing = execute_query('''
        SELECT id FROM pharmacy_inventory 
        WHERE pharmacy_id = ? AND medicine_id = ? AND batch_number = ?
    ''', (pharmacy['id'], medicine_id, batch_number))
    
    if existing:
        # Update existing inventory
        execute_query('''
            UPDATE pharmacy_inventory 
            SET current_stock = ?, unit_price = ?, mrp = ?, expiry_date = ?, 
                minimum_stock_level = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (current_stock, unit_price, mrp, expiry_date, minimum_stock_level, existing[0]['id']))
    else:
        # Add new inventory item
        execute_insert('''
            INSERT INTO pharmacy_inventory (pharmacy_id, medicine_id, current_stock, unit_price, 
                                          mrp, batch_number, expiry_date, minimum_stock_level)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (pharmacy['id'], medicine_id, current_stock, unit_price, mrp, 
              batch_number, expiry_date, minimum_stock_level))
    
    flash('Inventory updated successfully!', 'success')
    return redirect(url_for('manage_inventory'))

@app.route('/medicine-search')
def medicine_search():
    """Public page for searching medicine availability"""
    medicines = execute_query('SELECT * FROM medicines ORDER BY name')
    locations = execute_query('SELECT * FROM locations ORDER BY name')
    
    search_results = []
    if request.args.get('medicine_id') and request.args.get('location_id'):
        medicine_id = request.args.get('medicine_id')
        location_id = request.args.get('location_id')
        
        # Search for medicine availability
        search_results = execute_query('''
            SELECT p.pharmacy_name, p.address, p.phone, pi.current_stock, 
                   pi.unit_price, pi.mrp, pi.batch_number, pi.expiry_date,
                   m.name as medicine_name, m.strength, m.dosage_form
            FROM pharmacy_inventory pi
            JOIN pharmacies p ON pi.pharmacy_id = p.id
            JOIN medicines m ON pi.medicine_id = m.id
            WHERE pi.medicine_id = ? AND p.location_id = ? AND pi.current_stock > 0
            ORDER BY pi.unit_price ASC
        ''', (medicine_id, location_id))
    
    return render_template('medicine_search.html', 
                         medicines=medicines, 
                         locations=locations,
                         search_results=search_results)

@app.route('/alerts')
@login_required
def view_alerts():
    """View all active alerts"""
    alerts = execute_query('''
        SELECT sa.*, m.name as medicine_name, l.name as location_name
        FROM shortage_alerts sa
        JOIN medicines m ON sa.medicine_id = m.id
        JOIN locations l ON sa.location_id = l.id
        WHERE sa.is_active = TRUE
        ORDER BY sa.severity DESC, sa.created_at DESC
    ''')
    
    return render_template('alerts.html', alerts=alerts)

@app.route('/analytics')
@login_required
@role_required(['admin', 'government', 'ngo'])
def analytics():
    """Analytics dashboard with charts and trends"""
    # Get shortage trends
    shortage_trends = execute_query('''
        SELECT DATE(created_at) as date, COUNT(*) as count
        FROM shortage_alerts
        WHERE created_at >= DATE('now', '-30 days')
        GROUP BY DATE(created_at)
        ORDER BY date
    ''')
    
    # Get top medicines with shortages
    top_shortage_medicines = execute_query('''
        SELECT m.name, COUNT(*) as shortage_count
        FROM shortage_alerts sa
        JOIN medicines m ON sa.medicine_id = m.id
        WHERE sa.created_at >= DATE('now', '-30 days')
        GROUP BY m.id, m.name
        ORDER BY shortage_count DESC
        LIMIT 10
    ''')
    
    # Get location-wise shortage distribution
    location_shortages = execute_query('''
        SELECT l.name, COUNT(*) as shortage_count
        FROM shortage_alerts sa
        JOIN locations l ON sa.location_id = l.id
        WHERE sa.created_at >= DATE('now', '-30 days')
        GROUP BY l.id, l.name
        ORDER BY shortage_count DESC
    ''')
    
    return render_template('analytics.html', 
                         shortage_trends=shortage_trends,
                         top_shortage_medicines=top_shortage_medicines,
                         location_shortages=location_shortages)

@app.route('/chatbot')
@login_required
def chatbot():
    """Medicine inventory chatbot interface"""
    return render_template('chatbot.html')

@app.route('/api/chatbot', methods=['POST'])
@login_required
def chatbot_api():
    """Simple chatbot API for medicine queries"""
    user_message = request.json.get('message', '').lower()
    
    # Simple keyword-based responses
    if 'insulin' in user_message:
        # Get insulin availability
        insulin_data = execute_query('''
            SELECT p.pharmacy_name, p.phone, pi.current_stock, pi.unit_price
            FROM pharmacy_inventory pi
            JOIN pharmacies p ON pi.pharmacy_id = p.id
            JOIN medicines m ON pi.medicine_id = m.id
            WHERE m.name LIKE '%insulin%' AND pi.current_stock > 0
            ORDER BY pi.unit_price ASC
            LIMIT 5
        ''')
        
        if insulin_data:
            response = "Here are pharmacies with insulin available:\n\n"
            for pharmacy in insulin_data:
                response += f"• {pharmacy['pharmacy_name']}: {pharmacy['current_stock']} units at ₹{pharmacy['unit_price']}\n"
        else:
            response = "Sorry, insulin is currently out of stock in nearby pharmacies."
    
    elif 'shortage' in user_message:
        # Get current shortages
        shortages = execute_query('''
            SELECT m.name, sa.severity, l.name as location
            FROM shortage_alerts sa
            JOIN medicines m ON sa.medicine_id = m.id
            JOIN locations l ON sa.location_id = l.id
            WHERE sa.is_active = TRUE
            ORDER BY sa.severity DESC
            LIMIT 5
        ''')
        
        if shortages:
            response = "Current medicine shortages:\n\n"
            for shortage in shortages:
                response += f"• {shortage['name']} - {shortage['severity']} shortage in {shortage['location']}\n"
        else:
            response = "No major shortages reported currently."
    
    else:
        response = "I can help you with medicine availability and shortage information. Try asking about specific medicines or current shortages!"
    
    return jsonify({'response': response})

@app.route('/profile')
@login_required
def profile():
    """User profile page"""
    user_id = session.get('user_id')
    user = execute_query('SELECT * FROM users WHERE id = ?', (user_id,))[0]
    
    return render_template('profile.html', user=user)

@app.route('/logout')
@login_required
def logout():
    """Logout user"""
    session.clear()
    flash('You have been logged out successfully.', 'success')
    return redirect(url_for('index'))

# Helper functions
def check_and_create_alerts(medicine_id, location_id):
    """Check if conditions warrant creating a shortage alert"""
    # Count recent reports for this medicine in this location
    recent_reports = execute_query('''
        SELECT COUNT(*) as count
        FROM patient_reports
        WHERE medicine_id = ? AND location_id = ? 
        AND created_at >= DATE('now', '-7 days')
    ''', (medicine_id, location_id))
    
    if recent_reports[0]['count'] >= 3:  # Threshold for creating alert
        # Check if alert already exists
        existing_alert = execute_query('''
            SELECT id FROM shortage_alerts
            WHERE medicine_id = ? AND location_id = ? AND is_active = TRUE
        ''', (medicine_id, location_id))
        
        if not existing_alert:
            # Create new alert
            execute_insert('''
                INSERT INTO shortage_alerts (medicine_id, location_id, alert_type, severity, description)
                VALUES (?, ?, 'shortage', 'medium', 'Multiple shortage reports received')
            ''', (medicine_id, location_id))

# Error handlers
# @app.errorhandler(404)
# def not_found(error):
#     return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

if __name__ == '__main__':
    # Initialize database if it doesn't exist
    if not os.path.exists('healthcare.db'):
        print("Database not found. Please run the schema script first.")
    
    app.run(debug=True, host='0.0.0.0', port=5000)