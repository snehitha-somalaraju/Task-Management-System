#!/usr/bin/env python3
"""
Manual Google Calendar Authentication
Run this once to set up authentication
"""

from google_auth_oauthlib.flow import InstalledAppFlow
import pickle
import os

print("\n" + "="*70)
print("GOOGLE CALENDAR AUTHENTICATION SETUP".center(70))
print("="*70 + "\n")

SCOPES = ['https://www.googleapis.com/auth/calendar']

print("[STEP 1] Reading credentials file...")
if not os.path.exists('google_credentials.json'):
    print("✗ google_credentials.json not found!")
    print("  Make sure it's in the project folder")
    exit(1)

print("✓ Credentials file found\n")

print("[STEP 2] Starting OAuth flow...")
print("A browser window will open. Please:")
print("1. Sign in with your Google account")
print("2. Click 'Allow' to authorize the app")
print("3. You'll see a success message\n")

try:
    flow = InstalledAppFlow.from_client_secrets_file(
        'google_credentials.json',
        SCOPES
    )
    
    # This will open your browser automatically
    creds = flow.run_local_server(port=8080, open_browser=True)
    
    print("\n✓ Authentication successful!")
    
    # Save the token
    with open('token.pickle', 'wb') as token:
        pickle.dump(creds, token)
    
    print("✓ Token saved to token.pickle\n")
    
    print("="*70)
    print("You are now authenticated with Google Calendar!".center(70))
    print("="*70)
    print("\nNow you can:")
    print("1. Start Flask: python flask_api.py")
    print("2. Create tasks in the system")
    print("3. Tasks will automatically sync to Google Calendar\n")
    
except Exception as e:
    print(f"\n✗ Authentication failed: {e}")
    import traceback
    traceback.print_exc()
    exit(1)
