# debug_files.py
import sys
sys.path.append('.')

from google_drive import GoogleDriveClient
import config

def debug_files():
    try:
        drive_client = GoogleDriveClient()
        
        if drive_client.load_credentials():
            print("✅ Google Drive connected")
            
            # Get all files
            files_response = drive_client.list_files(page_size=100)
            files = files_response.get('files', [])
            
            print(f"📁 Total files found: {len(files)}")
            print("\n" + "="*80)
            
            for i, file in enumerate(files):
                print(f"\n{i+1}. {file['name']}")
                print(f"   📄 Type: {file.get('mimeType', 'unknown')}")
                print(f"   📦 Size: {file.get('size', '0')} bytes")
                print(f"   🆔 ID: {file['id']}")
                
                # Check if processable
                mime_type = file.get('mimeType', '')
                file_size = int(file.get('size', 0))
                
                is_pdf = mime_type == 'application/pdf'
                is_docx = mime_type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                is_txt = mime_type == 'text/plain'
                is_supported = is_pdf or is_docx or is_txt
                is_not_too_large = file_size <= 25 * 1024 * 1024
                
                print(f"   ✅ Processable: {is_supported and is_not_too_large}")
                if not is_supported:
                    print(f"   ❌ Reason: Unsupported type - {mime_type}")
                elif not is_not_too_large:
                    print(f"   ❌ Reason: File too large - {file_size} bytes")
                else:
                    print(f"   🎯 Will be processed!")
            
            print("\n" + "="*80)
            print(f"🎯 Processable files: {sum(1 for f in files if (f.get('mimeType') in ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'text/plain']) and int(f.get('size', 0)) <= 25 * 1024 * 1024)}")
            
        else:
            print("❌ Not authenticated with Google Drive")
            
    except Exception as e:
        print(f"❌ Debug failed: {e}")
        import traceback
        print(f"📋 Traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    debug_files()