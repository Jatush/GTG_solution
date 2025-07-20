import firebase_admin
from firebase_admin import credentials, firestore  # Or db for Realtime DB

# Load your Firebase service account key
cred = credentials.Certificate("firebase-key.json")

# Initialize the Firebase app
firebase_admin.initialize_app(cred)

# Firestore instance (you can change to db if using Realtime Database)
db = firestore.client()
