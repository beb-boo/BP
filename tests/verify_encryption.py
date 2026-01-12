
import urllib.request
import urllib.error
import json
import sqlite3
import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '../app/.env'))

BASE_URL = "http://localhost:8888/api/v1"
DB_PATH = "blood_pressure.db"

def post_json(url, data):
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode('utf-8'),
        headers={
            'Content-Type': 'application/json',
            'X-API-Key': 'bp-web-app-key' 
        }
    )
    try:
        with urllib.request.urlopen(req) as response:
            return response.getcode(), json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode('utf-8'))
    except Exception as e:
        return 0, str(e)

def manual_insert_and_login_test():
    print("\n[2] Manual Insert & API Login Test...")
    from app.utils.encryption import encrypt_value, hash_value, decrypt_value
    from app.utils.security import hash_password
    from app.models import now_th
    from datetime import datetime
    
    # Prepare Data
    email = "bob@secure.com"
    phone = "0888888888"
    pwd = "password123"
    name = "Bob Secure"
    
    # Encrypt & Hash
    email_enc = encrypt_value(email)
    email_hash = hash_value(email)
    phone_enc = encrypt_value(phone)
    phone_hash = hash_value(phone)
    name_enc = encrypt_value(name)
    name_hash = hash_value(name)
    pwd_hash = hash_password(pwd)
    
    print(f"  > Generated Data for '{name}':")
    print(f"    Email Hash: {email_hash[:10]}...")
    print(f"    Name Encrip: {name_enc[:10]}...")
    
    # Insert Config
    try:
        conn = sqlite3.connect("blood_pressure.db")
        cursor = conn.cursor()
        
        # Check if table exists (it should if app restarted)
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users';")
        if not cursor.fetchone():
            print("  ! ERROR: 'users' table not found. Did Uvicorn restart/recreate DB?")
            return

        cursor.execute("""
            INSERT INTO users (
                email_encrypted, email_hash,
                phone_number_encrypted, phone_number_hash,
                full_name_encrypted, full_name_hash,
                password_hash, role, is_active, is_email_verified, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            email_enc, email_hash,
            phone_enc, phone_hash,
            name_enc, name_hash,
            pwd_hash, "patient", 1, 1, datetime.now(), datetime.now()
        ))
        conn.commit()
        conn.close()
        print("  > Inserted User into SQLite DB successfully.")
    except Exception as e:
        print(f"  ! Note: Insert failed ({e}). Assuming user exists and proceeding...")
        # return # Do not return, proceed to verification

    # Verify Data in DB is encrypted (Visual Check)
    conn = sqlite3.connect("blood_pressure.db")
    cursor = conn.cursor()
    cursor.execute("SELECT email_encrypted, full_name_encrypted FROM users WHERE email_hash=?", (email_hash,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        print(f"  > DB Row Check: Email='{row[0][:10]}...', Name='{row[1][:10]}...'")
        if "bob" in row[0] or "Bob" in row[1]:
             print("  ! FAIL: Data is plain text in DB!")
        else:
             print("  > PASS: Data appears encrypted in DB.")
    else:
        print("  ! FAIL: Could not read back user.")
        return

    # Attempt Login via API
    print("\n[3] Attempting API Login...")
    login_data = {
        "email": email,
        "password": pwd
    }
    
    code, resp_data = post_json(f"{BASE_URL}/auth/login", login_data)
    
    if code == 200:
        print("  > PASS: Login Successful!")
        data = resp_data['data']['user']
        print(f"    API Returned Name: {data.get('full_name')}")
        if data.get('full_name') == name:
            print("    PASS: API correctly decrypted the name.")
        else:
            print(f"    FAIL: API returned wrong name: {data.get('full_name')}")
    else:
         print(f"  ! FAIL: Login Failed ({code}): {resp_data}")

if __name__ == "__main__":
    manual_insert_and_login_test()
