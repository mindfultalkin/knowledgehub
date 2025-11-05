from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import os
import json
import config
from datetime import datetime
from dotenv import load_dotenv, set_key

# Load environment variables
load_dotenv()

class GoogleDriveClient:
    """Google Drive API Client for file operations using .env configuration"""
    
    def __init__(self):
        self.creds = None
        self.service = None
        self.scopes = config.SCOPES
        self.client_config = self._build_client_config()
        
    def _build_client_config(self):
        """Build client config from environment variables instead of JSON file"""
        return {
            "web": {
                "client_id": config.GOOGLE_CLIENT_ID,
                "client_secret": config.GOOGLE_CLIENT_SECRET,
                "project_id": config.GOOGLE_PROJECT_ID,
                "auth_uri": config.GOOGLE_AUTH_URI,
                "token_uri": config.GOOGLE_TOKEN_URI,
                "auth_provider_x509_cert_url": config.GOOGLE_AUTH_PROVIDER_CERT_URL,
                "redirect_uris": [config.GOOGLE_REDIRECT_URI]  # Use single consistent redirect URI
            }
        }
        
    def get_authorization_url(self, redirect_uri):
        """Get OAuth authorization URL"""
        try:
            # Use the consistent redirect URI from config
            flow = Flow.from_client_config(
                self.client_config,
                scopes=self.scopes,
                redirect_uri=config.GOOGLE_REDIRECT_URI  # Always use config redirect URI
            )
            
            # Generate authorization URL with proper parameters
            authorization_url, state = flow.authorization_url(
                access_type='offline',
                include_granted_scopes='true',
                prompt='consent'
            )
            
            print(f"✅ Authorization URL generated successfully")
            print(f"🔗 Using redirect URI: {config.GOOGLE_REDIRECT_URI}")
            return authorization_url, state
            
        except Exception as e:
            print(f"❌ Error creating authorization URL: {str(e)}")
            raise
    
    def exchange_code_for_credentials(self, code, redirect_uri):
        """Exchange authorization code for credentials"""
        try:
            # Use the consistent redirect URI from config
            flow = Flow.from_client_config(
                self.client_config,
                scopes=self.scopes,
                redirect_uri=config.GOOGLE_REDIRECT_URI  # Always use config redirect URI
            )
            
            # Fetch the token using the authorization code
            flow.fetch_token(code=code)
            self.creds = flow.credentials
            
            # Save credentials to .env
            self.save_credentials_to_env()
            self.build_service()
            
            print("✅ Successfully exchanged code for credentials")
            print(f"🔗 Used redirect URI: {config.GOOGLE_REDIRECT_URI}")
            return self.creds
            
        except Exception as e:
            print(f"❌ Error exchanging code: {str(e)}")
            raise
    
    def save_credentials_to_env(self):
        """Save credentials to .env file"""
        try:
            if self.creds:
                env_file = '.env'
                
                # Update .env file with new tokens
                set_key(env_file, 'GOOGLE_ACCESS_TOKEN', self.creds.token or '')
                set_key(env_file, 'GOOGLE_REFRESH_TOKEN', self.creds.refresh_token or '')
                
                if self.creds.expiry:
                    expiry_str = self.creds.expiry.isoformat()
                    set_key(env_file, 'GOOGLE_TOKEN_EXPIRY', expiry_str)
                
                print("✅ Credentials saved to .env file")
                
                # Reload environment variables
                load_dotenv(override=True)
                
        except Exception as e:
            print(f"❌ Error saving credentials to .env: {str(e)}")
    
    def load_credentials(self):
        """Load saved credentials from .env"""
        try:
            # Check if we have token information in .env
            access_token = config.GOOGLE_ACCESS_TOKEN
            refresh_token = config.GOOGLE_REFRESH_TOKEN
            
            if not access_token and not refresh_token:
                print("ℹ️  No saved credentials found in .env")
                return False
            
            # Build credentials from .env
            token_data = {
                'token': access_token,
                'refresh_token': refresh_token,
                'token_uri': config.GOOGLE_TOKEN_URI,
                'client_id': config.GOOGLE_CLIENT_ID,
                'client_secret': config.GOOGLE_CLIENT_SECRET,
                'scopes': self.scopes
            }
            
            if config.GOOGLE_TOKEN_EXPIRY:
                token_data['expiry'] = config.GOOGLE_TOKEN_EXPIRY
            
            self.creds = Credentials.from_authorized_user_info(token_data, self.scopes)
            
            # Check if credentials are valid
            if self.creds and self.creds.valid:
                self.build_service()
                print("✅ Loaded existing credentials from .env")
                return True
            elif self.creds and self.creds.expired and self.creds.refresh_token:
                # Try to refresh
                try:
                    from google.auth.transport.requests import Request
                    self.creds.refresh(Request())
                    self.save_credentials_to_env()
                    self.build_service()
                    print("✅ Refreshed expired credentials")
                    return True
                except Exception as e:
                    print(f"⚠️  Credentials expired and couldn't refresh: {str(e)}")
                    return False
                    
        except Exception as e:
            print(f"❌ Error loading credentials from .env: {str(e)}")
        
        return False
    
    def build_service(self):
        """Build Google Drive service"""
        try:
            if self.creds:
                self.service = build('drive', 'v3', credentials=self.creds)
                print("✅ Google Drive service built successfully")
        except Exception as e:
            print(f"❌ Error building service: {str(e)}")
    
    def list_files(self, page_size=100, page_token=None, query=None):
        """List files from Google Drive"""
        try:
            if not self.service:
                raise Exception("Not authenticated. Please authorize first.")
            
            # Build query
            search_query = "trashed=false"
            if query:
                search_query += f" and name contains '{query}'"
            
            # Execute request
            results = self.service.files().list(
                pageSize=page_size,
                pageToken=page_token,
                q=search_query,
                fields="nextPageToken, files(id, name, mimeType, size, "
                       "modifiedTime, createdTime, owners, thumbnailLink, "
                       "webViewLink, iconLink)",
                orderBy="modifiedTime desc"
            ).execute()
            
            print(f"✅ Retrieved {len(results.get('files', []))} files")
            return results
            
        except HttpError as error:
            print(f"❌ An HTTP error occurred: {error}")
            raise
        except Exception as error:
            print(f"❌ An error occurred: {error}")
            raise
    
    def get_file(self, file_id):
        """Get specific file details"""
        try:
            if not self.service:
                raise Exception("Not authenticated")
            
            file = self.service.files().get(
                fileId=file_id,
                fields="id, name, mimeType, size, modifiedTime, "
                       "createdTime, owners, thumbnailLink, webViewLink, "
                       "iconLink, description"
            ).execute()
            
            return file
            
        except HttpError as error:
            print(f"❌ An error occurred: {error}")
            raise
    
    def get_about(self):
        """Get Google Drive information"""
        try:
            if not self.service:
                raise Exception("Not authenticated")
            
            about = self.service.about().get(
                fields="user, storageQuota"
            ).execute()
            
            return about
            
        except HttpError as error:
            print(f"❌ An error occurred: {error}")
            raise