import json
import os
from flask import flash, url_for, redirect
from GrandBridge import db
from GrandBridge.models import User
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
import google.auth.exceptions
import requests
from google.oauth2 import id_token
from GrandBridge.config import Config
from datetime import datetime, timedelta
from googleapiclient.discovery import build

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

# Get credentials from environment variables instead of JSON file
GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID') or getattr(Config, 'GOOGLE_CLIENT_ID', None)
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET') or getattr(Config, 'GOOGLE_CLIENT_SECRET', None)
GOOGLE_PROJECT_ID = os.environ.get('GOOGLE_PROJECT_ID') or getattr(Config, 'GOOGLE_PROJECT_ID', 'grandbridge')

# Check if required environment variables are set
if not GOOGLE_CLIENT_ID:
    raise RuntimeError("Missing GOOGLE_CLIENT_ID environment variable")
if not GOOGLE_CLIENT_SECRET:
    raise RuntimeError("Missing GOOGLE_CLIENT_SECRET environment variable")
if not GOOGLE_PROJECT_ID:
    raise RuntimeError("Missing GOOGLE_PROJECT_ID environment variable")

# Create client configuration from environment variables instead of JSON file
CLIENT_CONFIG = {
    "web": {
        "client_id": GOOGLE_CLIENT_ID,
        "project_id": GOOGLE_PROJECT_ID,
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uris": ["https://grandbridge.azurewebsites.net/callback"],  # Updated for Azure
        "javascript_origins": ["https://grandbridge.azurewebsites.net"]  # Updated for Azure
    }
}

SCOPES = ["https://www.googleapis.com/auth/userinfo.profile", 
          "https://www.googleapis.com/auth/userinfo.email", 
          "openid", 
          "https://www.googleapis.com/auth/calendar"]

flow = Flow.from_client_config(
    client_config=CLIENT_CONFIG,
    scopes=SCOPES)

authorization_url, state = flow.authorization_url(
    access_type='offline',
    include_granted_scopes='true',
    prompt='consent'
)

# Updated redirect URI for Azure deployment
flow.redirect_uri = 'https://grandbridge.azurewebsites.net/callback'

def get_id_info(credentials):
    token_request = google.auth.transport.requests.Request(session=requests.session())
    try:
        id_info = id_token.verify_oauth2_token(
            id_token=credentials._id_token,
            request=token_request,
            audience=GOOGLE_CLIENT_ID
        )
        return id_info
    except Exception as error:
        raise Exception(f"Error occured: {error}")

def refresh_token(credentials):
    print(credentials.refresh_token)
    print(type(credentials.refresh_token))

    params = {
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
        "refresh_token": credentials.refresh_token,
        "grant_type": "refresh_token"
    }

    try:
        response = requests.post("https://oauth2.googleapis.com/token", data=params)
        response.raise_for_status()
        # Calculate the new expiry date based on the current time and the expires_in value in the response
        new_expiry = datetime.now() + timedelta(seconds=response.json()['expires_in'])

        # Create the new Credentials object with the updated access token and expiry date
        new_credentials = Credentials(
            token=response.json()['access_token'],
            refresh_token=credentials.refresh_token,
            token_uri=credentials.token_uri,
            client_id=GOOGLE_CLIENT_ID,
            client_secret=GOOGLE_CLIENT_SECRET,
            scopes=SCOPES,
            expiry=new_expiry
        )
        return new_credentials
    except requests.exceptions.HTTPError as error:
        # Handle HTTP errors
        raise Exception(f"HTTP error occurred: {error}")
    
    except Exception as error:
        raise Exception(f"Error occured: {error}")

def get_flow():
    return flow

class SQLAlchemyDBError(Exception):
    pass

def db_add_user(id, google_id, credentials):
    credentials_data = {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes,
        'expiry': credentials.expiry.isoformat() if credentials.expiry else None,
    }

    credentials_json = credentials.to_json()

    try:
        user = User.query.filter_by(id=id).first()
        if user:
            user.google_credentials_data = credentials_data
            user.google_credentials_json = credentials_json
            user.google_id = google_id
            db.session.commit()
        else:
            flash('User not exist.', 'danger')
            return redirect(url_for('users.register'))

        
    except Exception as e:
        db.session.rollback()
        raise SQLAlchemyDBError(f"Error adding/updating user: {e}")

def db_get_user_credentials(user_id):
    # print(user_id)
    try:
        user = User.query.filter_by(google_id=user_id).first()
        if user and user.google_credentials_json:
            credentials_info = json.loads(user.google_credentials_json)
            credentials = google.oauth2.credentials.Credentials.from_authorized_user_info(credentials_info)
            return credentials
        else:
            raise SQLAlchemyDBError("User not found or missing credentials.")
    except Exception as e:
        raise SQLAlchemyDBError(f"Error retrieving user credentials: {e}")
