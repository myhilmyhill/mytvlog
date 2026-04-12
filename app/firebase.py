import firebase_admin
from firebase_admin import credentials
import os

SERVICE_ACCOUNT_KEY_PATH = "/etc/gcp/serviceAccountKey.json"

def initialize_firebase():
    if not firebase_admin._apps:
        if os.path.exists(SERVICE_ACCOUNT_KEY_PATH):
            cred = credentials.Certificate(SERVICE_ACCOUNT_KEY_PATH)
            firebase_admin.initialize_app(cred)
        else:
            firebase_admin.initialize_app()
