import sqlite3
import random
import csv

conn = sqlite3.connect('database.db')
cursor = conn.cursor()

# Create pharmacies table
cursor.execute('''
CREATE TABLE IF NOT EXISTS pharmacies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pharmacy_name TEXT NOT NULL,
    address TEXT NOT NULL,
    latitude REAL,
    longitude REAL
)
''')

# Create pharmacy_medicines table
cursor.execute('''
CREATE TABLE IF NOT EXISTS pharmacy_medicines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pharmacy_id INTEGER NOT NULL,
    medicine_name TEXT NOT NULL,
    price REAL NOT NULL,
    FOREIGN KEY (pharmacy_id) REFERENCES pharmacies(id)
)
''')

# Clear existing data to avoid duplicates
cursor.execute('DELETE FROM pharmacy_medicines')
cursor.execute('DELETE FROM pharmacies')
conn.commit()

# Insert pharmacies data
pharmacies_data = [
    ('Apollo Pharmacy - Andheri', '123 Main St, Andheri West, Mumbai', 19.1205, 72.8303),
    ('MedPlus Pharmacy', '456 MG Road, Bengaluru', 12.9716, 77.5946),
    ('HealthFirst Pharmacy', '789 CP Market, New Delhi', 28.6333, 77.2167),
    ('CarePlus Pharmacy', '22 Park Street, Kolkata', 22.5726, 88.3639),
    ('CityMeds Pharmacy', '45 MG Road, Pune', 18.5204, 73.8567),
    ('GoodHealth Pharmacy', '11 Brigade Road, Bengaluru', 12.9719, 77.5943),
    ('Wellness Pharmacy', '56 MG Road, Chennai', 13.0827, 80.2707),
    ('CareWell Pharmacy', '123 Nehru St, Hyderabad', 17.3850, 78.4867),
    ('HealthMart Pharmacy', '88 Marine Drive, Mumbai', 18.9333, 72.8236),
    ('PrimeCare Pharmacy', '54 Connaught Place, New Delhi', 28.6315, 77.2172),
    ('MediCare Pharmacy', '12 MG Road, Jaipur', 26.9124, 75.7873),
    ('PharmaPlus', '44 Gandhi Nagar, Ahmedabad', 23.0225, 72.5714),
    ('HealthyLife Pharmacy', '67 Residency Rd, Bengaluru', 12.9718, 77.5940),
    ('UrbanMeds Pharmacy', '88 MG Road, Lucknow', 26.8467, 80.9462),
    ('WellCare Pharmacy', '23 Park Street, Kolkata', 22.5726, 88.3639),
    ('HealthZone Pharmacy', '99 Sector 17, Chandigarh', 30.7333, 76.7794),
    ('Medico Pharmacy', '77 Mall Road, Dehradun', 30.3165, 78.0322),
    ('PharmaCare', '55 Connaught Place, New Delhi', 28.6304, 77.2177),
    ('LifePlus Pharmacy', '45 MG Road, Surat', 21.1702, 72.8311),
    ('SafeMeds Pharmacy', '78 Civil Lines, Kanpur', 26.4499, 80.3319),
]

cursor.executemany('''
INSERT INTO pharmacies (pharmacy_name, address, latitude, longitude) 
VALUES (?, ?, ?, ?)
''', pharmacies_data)
conn.commit()

# Fetch all pharmacy ids for reference
cursor.execute("SELECT id, pharmacy_name FROM pharmacies")
pharmacies = cursor.fetchall()

# Medicine list with price ranges (min price, max price)
medicine_list = [
    ('Paracetamol', 15.0, 30.0),
    ('Insulin', 350.0, 500.0),
    ('Aspirin', 10.0, 40.0),
    ('Thyroxine', 300.0, 500.0),
    ('Amoxicillin', 45.0, 90.0),
    ('Metformin', 25.0, 65.0),
    ('Ibuprofen', 20.0, 50.0),
    ('Cetirizine', 10.0, 35.0),
    ('Omeprazole', 40.0, 80.0),
    ('Lisinopril', 50.0, 120.0),
    ('Simvastatin', 30.0, 90.0),
    ('Azithromycin', 100.0, 200.0),
    ('Ranitidine', 25.0, 60.0),
    ('Hydrochlorothiazide', 20.0, 60.0),
    ('Clopidogrel', 60.0, 130.0),
]

# Assign random medicines with random prices to each pharmacy
medicine_entries = []
for pharmacy in pharmacies:
    pharmacy_id = pharmacy[0]
    pharmacy_name = pharmacy[1]
    # Assign 4 to 7 random medicines per pharmacy
    meds_for_pharmacy = random.sample(medicine_list, random.randint(4,7))
    print(f"\nPharmacy: {pharmacy_name}")
    for med in meds_for_pharmacy:
        med_name = med[0].lower()
        med_price = round(random.uniform(med[1], med[2]), 2)
        print(f"  - {med_name} @ ₹{med_price}")
        medicine_entries.append((pharmacy_id, med_name, med_price))

cursor.executemany('''
INSERT INTO pharmacy_medicines (pharmacy_id, medicine_name, price) VALUES (?, ?, ?)
''', medicine_entries)

conn.commit()

# Optional: Save to CSV for inspection
with open("pharmacy_medicine_mapping.csv", "w", newline="") as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(["Pharmacy Name", "Medicine Name", "Price"])
    for entry in medicine_entries:
        pharmacy_id = entry[0]
        med_name = entry[1]
        price = entry[2]
        pharmacy_name = next(p[1] for p in pharmacies if p[0] == pharmacy_id)
        writer.writerow([pharmacy_name, med_name, price])

conn.close()

print("\nDatabase and tables created, dummy data inserted successfully.")
print("Pharmacy-medicine mapping saved to 'pharmacy_medicine_mapping.csv'.")
