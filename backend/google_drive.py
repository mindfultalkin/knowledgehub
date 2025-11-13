from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import os
import json
import config
from datetime import datetime
from dotenv import load_dotenv, set_key


load_dotenv()


class GoogleDriveClient:
    """Google Drive API Client - Always requires fresh login"""
    
    def __init__(self):
        self.creds = None
        self.service = None
        self.scopes = config.SCOPES
        self.client_config = self._build_client_config()
        
    def _build_client_config(self):
        """Build client config from environment variables"""
        return {
            "web": {
                "client_id": config.GOOGLE_CLIENT_ID,
                "client_secret": config.GOOGLE_CLIENT_SECRET,
                "project_id": config.GOOGLE_PROJECT_ID,
                "auth_uri": config.GOOGLE_AUTH_URI,
                "token_uri": config.GOOGLE_TOKEN_URI,
                "auth_provider_x509_cert_url": config.GOOGLE_AUTH_PROVIDER_CERT_URL,
                "redirect_uris": [config.GOOGLE_REDIRECT_URI]
            }
        }
        
    def get_authorization_url(self, redirect_uri):
        """Get OAuth authorization URL - FORCES account selection"""
        try:
            flow = Flow.from_client_config(
                self.client_config,
                scopes=self.scopes,
                redirect_uri=config.GOOGLE_REDIRECT_URI
            )
            
            # ✅ FORCE ACCOUNT SELECTION + CONSENT SCREEN
            authorization_url, state = flow.authorization_url(
                access_type='offline',
                include_granted_scopes='true',
                prompt='select_account consent'  # ✅ Always show account chooser
            )
            
            print(f"✅ Authorization URL generated")
            print(f"🔗 Redirect URI: {config.GOOGLE_REDIRECT_URI}")
            return authorization_url, state
            
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            raise
    
    def exchange_code_for_credentials(self, code, redirect_uri):
        """Exchange authorization code for credentials"""
        try:
            flow = Flow.from_client_config(
                self.client_config,
                scopes=self.scopes,
                redirect_uri=config.GOOGLE_REDIRECT_URI
            )
            
            flow.fetch_token(code=code)
            self.creds = flow.credentials
            
            # ✅ OPTIONAL: Save to .env (but don't auto-load on startup)
            # Comment out if you don't want to save at all
            self.save_credentials_to_env()
            
            self.build_service()
            
            print("✅ Credentials exchanged successfully")
            return self.creds
            
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            raise
    
    def save_credentials_to_env(self):
        """Save credentials to .env (optional)"""
        try:
            if self.creds:
                env_file = '.env'
                set_key(env_file, 'GOOGLE_ACCESS_TOKEN', self.creds.token or '')
                set_key(env_file, 'GOOGLE_REFRESH_TOKEN', self.creds.refresh_token or '')
                
                if self.creds.expiry:
                    set_key(env_file, 'GOOGLE_TOKEN_EXPIRY', self.creds.expiry.isoformat())
                
                print("✅ Credentials saved to .env")
                load_dotenv(override=True)
                
        except Exception as e:
            print(f"❌ Error saving: {str(e)}")
    
    def load_credentials(self):
        """
        ✅ MODIFIED: Don't auto-load credentials
        Return False to force re-authentication
        """
        print("ℹ️  Skipping auto-load - user must connect manually")
        return False  # ✅ Always return False to force login
    
    def clear_credentials(self):
        """Clear saved credentials from .env"""
        try:
            env_file = '.env'
            set_key(env_file, 'GOOGLE_ACCESS_TOKEN', '')
            set_key(env_file, 'GOOGLE_REFRESH_TOKEN', '')
            set_key(env_file, 'GOOGLE_TOKEN_EXPIRY', '')
            
            self.creds = None
            self.service = None
            
            print("✅ Credentials cleared")
            load_dotenv(override=True)
            
        except Exception as e:
            print(f"❌ Error clearing credentials: {str(e)}")
    
    def build_service(self):
        """Build Google Drive service"""
        try:
            if self.creds:
                self.service = build('drive', 'v3', credentials=self.creds)
                print("✅ Google Drive service built")
        except Exception as e:
            print(f"❌ Error: {str(e)}")
    
    def list_files(self, page_size=100, page_token=None, query=None):
        """List files from Google Drive"""
        try:
            if not self.service:
                raise Exception("Not authenticated")
            
            search_query = "trashed=false"
            if query:
                search_query += f" and name contains '{query}'"
            
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
            
        except Exception as error:
            print(f"❌ Error: {error}")
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
            
        except Exception as error:
            print(f"❌ Error: {error}")
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
            
        except Exception as error:
            print(f"❌ Error: {error}")
            raise
