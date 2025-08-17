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
GOOGLE_CLIENT_ID = Config.GOOGLE_CLIENT_ID
GOOGLE_CLIENT_SECRET = Config.GOOGLE_CLIENT_SECRET
GOOGLE_CLIENT_JSON_PATH = Config.GOOGLE_CLIENT_JSON_PATH

if not GOOGLE_CLIENT_JSON_PATH:
    raise RuntimeError("Missing GOOGLE_CLIENT_JSON_PATH environment variable")

from pathlib import Path

# Resolve path relative to the project root
project_root = Path(__file__).resolve().parents[2]  # Adjust this if needed
json_path = project_root / GOOGLE_CLIENT_JSON_PATH

if not json_path.exists():
    raise FileNotFoundError(f"Google client secrets file not found: {json_path}")

with open(json_path, 'r') as f:
    CLIENT_CONFIG = json.load(f)

SCOPES=["https://www.googleapis.com/auth/userinfo.profile", 
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

flow.redirect_uri = 'http://localhost:8080/callback'


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