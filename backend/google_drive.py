from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import os
import json

class GoogleDriveClient:
    """Google Drive API Client for file operations"""
    
    def __init__(self, credentials_path='credentials/client_secret.json'):
        self.credentials_path = credentials_path
        self.creds = None
        self.service = None
        self.scopes = [
            'https://www.googleapis.com/auth/drive.readonly',
            'https://www.googleapis.com/auth/drive.metadata.readonly'
        ]
        
    def get_authorization_url(self, redirect_uri):
        """Get OAuth authorization URL"""
        try:
            flow = Flow.from_client_secrets_file(
                self.credentials_path,
                scopes=self.scopes,
                redirect_uri=redirect_uri
            )
            
            # Generate authorization URL with proper parameters
            authorization_url, state = flow.authorization_url(
                access_type='offline',
                include_granted_scopes='true',
                prompt='consent'
            )
            
            return authorization_url, flow
            
        except Exception as e:
            print(f"Error creating authorization URL: {str(e)}")
            raise
    
    def exchange_code_for_credentials(self, code, redirect_uri):
        """Exchange authorization code for credentials"""
        try:
            flow = Flow.from_client_secrets_file(
                self.credentials_path,
                scopes=self.scopes,
                redirect_uri=redirect_uri
            )
            
            # Fetch the token using the authorization code
            flow.fetch_token(code=code)
            self.creds = flow.credentials
            
            # Save credentials for later use
            self.save_credentials()
            self.build_service()
            
            return self.creds
            
        except Exception as e:
            print(f"Error exchanging code: {str(e)}")
            raise
    
    def save_credentials(self):
        """Save credentials to file"""
        try:
            if self.creds:
                os.makedirs('credentials', exist_ok=True)
                with open('credentials/token.json', 'w') as token:
                    token.write(self.creds.to_json())
                print("Credentials saved successfully")
        except Exception as e:
            print(f"Error saving credentials: {str(e)}")
    
    def load_credentials(self):
        """Load saved credentials"""
        try:
            if os.path.exists('credentials/token.json'):
                with open('credentials/token.json', 'r') as token:
                    creds_data = json.load(token)
                    self.creds = Credentials.from_authorized_user_info(creds_data, self.scopes)
                    
                    # Check if credentials are valid
                    if self.creds and self.creds.valid:
                        self.build_service()
                        print("Loaded existing credentials")
                        return True
                    elif self.creds and self.creds.expired and self.creds.refresh_token:
                        # Try to refresh
                        try:
                            from google.auth.transport.requests import Request
                            self.creds.refresh(Request())
                            self.save_credentials()
                            self.build_service()
                            print("Refreshed credentials")
                            return True
                        except:
                            print("Credentials expired and couldn't refresh")
                            return False
        except Exception as e:
            print(f"Error loading credentials: {str(e)}")
        return False
    
    def build_service(self):
        """Build Google Drive service"""
        try:
            if self.creds:
                self.service = build('drive', 'v3', credentials=self.creds)
                print("Google Drive service built successfully")
        except Exception as e:
            print(f"Error building service: {str(e)}")
    
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
            
            print(f"Retrieved {len(results.get('files', []))} files")
            return results
            
        except HttpError as error:
            print(f"An HTTP error occurred: {error}")
            raise
        except Exception as error:
            print(f"An error occurred: {error}")
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
            print(f"An error occurred: {error}")
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
            print(f"An error occurred: {error}")
            raise
