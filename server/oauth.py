import json
import os
from pathlib import Path

from server.bin.encrypt_secrets import decrypt_file
from server.common import DECRYPT_KEY, MODE_ENUM, get_mode

# Set this to avoid scope change warnings. I don't understand where they come from.
# It started when I added support for mobile.
os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'

import google.oauth2.credentials
import google_auth_oauthlib.flow
from google_auth_oauthlib.flow import Flow

import requests
import flask
import logging


# Note this is set in the Google API Console. It is the URL where the user will be sent after the
# authorization process is complete. This value must exactly match one of the authorized redirect
# URIs for the OAuth 2.0 client, which are configured in the API Console.
def get_oauth_redirect_url():
    if get_mode() == MODE_ENUM.LOCAL:
        return 'http://localhost:3000/app/oauth_redirect'
    else:
        return 'https://cleanmail-abc7a98eaa1f.herokuapp.com/app/oauth_redirect'


def get_client_secret_file() -> Path:
    client_secrets = Path('client_secret.json')
    if not client_secrets.exists():
        decrypt_file('client_secret.json.encrypt', DECRYPT_KEY)
    
    return client_secrets

SCOPES = [
    'https://www.googleapis.com/auth/userinfo.email', 
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.compose',
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/contacts',
    'https://www.googleapis.com/auth/calendar.events',
    'https://www.googleapis.com/auth/tasks',
    'openid'
    ]
def get_credentials_from_flask_session() -> google.oauth2.credentials.Credentials:
    if flask.session.get('credentials') is None:
        return None
    return google.oauth2.credentials.Credentials(**flask.session['credentials'])
    
def get_flow(state=None):
    # Required, call the from_client_secrets_file method to retrieve the client ID from a
    # client_secret.json file. The client ID (from that file) and access scopes are required. (You can
    # also use the from_client_config method, which passes the client configuration as it originally
    # appeared in a client secrets file but doesn't access the file itself.)
    return google_auth_oauthlib.flow.Flow.from_client_secrets_file(
        get_client_secret_file(),
        scopes=SCOPES,
        state=state)


def start_oauth_flow(state: str='web'):
    flow = get_flow()

    # Required, indicate where the API server will redirect the user after the user completes
    # the authorization flow. The redirect URI is required. The value must exactly
    # match one of the authorized redirect URIs for the OAuth 2.0 client, which you
    # configured in the API Console. If this value doesn't match an authorized URI,
    # you will get a 'redirect_uri_mismatch' error.
    flow.redirect_uri = get_oauth_redirect_url()

    # Generate URL for request to Google's OAuth 2.0 server.
    # Use kwargs to set optional request parameters.
    authorization_url, state = flow.authorization_url(
        # Recommended, enable offline access so that you can represh an access token without
        # re-prompting the user for permission. Recommended for web server apps.
        access_type='offline',
        # Optional, enable incremental authorization. Recommended as a best practice.
        include_granted_scopes='true',
        # Recommended, state value can increase your assurance that an incoming connection is the result
        # of an authentication request.
        state=state,
        # Optional, if your application knows which user is trying to authenticate, it can use this
        # parameter to provide a hint to the Google Authentication Server.
        login_hint='',
        # Optional, set prompt to 'consent' will prompt the user for consent
        prompt='consent')
    logging.info('authorization_url: %s', authorization_url)
    logging.info('state: %s', state)
    flask.session['state'] = state 
    return flask.redirect(authorization_url)

def oauth_handle_redirect() -> bool:
    state = flask.session.get('state')
    logging.info('state: %s', state)
    if state is None:
        logging.info(f'skipping auth due to missing state: {flask.request.user_agent}')
        return False
    
    response_state = flask.request.args.get("state")
    if response_state != state:
        logging.info(f"skipping auth due to state mismsatch:  {state} != {response_state}")
    flow = get_flow(state)
    
    flow.redirect_uri = get_oauth_redirect_url()
    logging.info('redirect_uri: %s', flow.redirect_uri)
    authorization_response = flask.request.url
    flow.fetch_token(authorization_response=authorization_response)

    # Store the credentials in the session.
    # ACTION ITEM for developers:
    #     Store user's access and refresh tokens in your data store if
    #     incorporating this code into your real app.
    credentials = flow.credentials
    logging.info('credentials: %s', credentials)
    flask.session['credentials'] = {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes}
    
    flask.session['username'] = get_username(credentials)
    return True

def get_username(credentials):
    # Define the URL of the Userinfo API.
    userinfo_url = 'https://www.googleapis.com/oauth2/v3/userinfo'

    # Include the OAuth token in the request headers.
    headers = {
        'Authorization': f'Bearer {credentials.token}'
    }

    # Send a GET request to fetch user information.
    response = requests.get(userinfo_url, headers=headers)

    # Check if the request was successful.
    if response.status_code == 200:
        user_data = response.json()
        username = user_data.get('email')
        logging.info(f'Username: {username}')
        return username
    else:
        logging.info(f'Failed to fetch user information. {response.status_code}')
        logging.info(f'JSON: {response.json()}')


def refresh_credentials(credentials):
    credentials.refresh(google.auth.transport.requests.Request())
    flask.session['credentials'] = {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes}
    return credentials

def serialize_credentials(credentials):
    return json.dumps({
            "token": credentials.token,
            "refresh_token": credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes
        })

def deserialize_credentials(credential_str):
    data = json.loads(credential_str)
    return google.oauth2.credentials.Credentials(**data)
