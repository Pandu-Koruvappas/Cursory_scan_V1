import os
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv

load_dotenv()

class AzureStorageService:
    def __init__(self):
        self.connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        self.sas_url = os.getenv("AZURE_STORAGE_SAS_URL")
        self.container_name = os.getenv("AZURE_STORAGE_CONTAINER", "ba-documents")
        
        if self.sas_url:
            try:
                # Initialize from SAS URL
                self.blob_service_client = BlobServiceClient(account_url=self.sas_url)
                self.container_client = self.blob_service_client.get_container_client(self.container_name)
                print(f"INFO: Azure Storage initialized via SAS URL. Target Container: {self.container_name}")
            except Exception as e:
                print(f"ERROR: Azure SAS URL Initialization Failed: {e}")
                self.blob_service_client = None
        elif self.connection_string:
            try:
                self.blob_service_client = BlobServiceClient.from_connection_string(self.connection_string)
                self.container_client = self.blob_service_client.get_container_client(self.container_name)
                if not self.container_client.exists():
                    self.container_client.create_container()
                print(f"INFO: Azure Storage initialized via Connection String.")
            except Exception as e:
                print(f"ERROR: Azure Connection String Initialization Failed: {e}")
                self.blob_service_client = None
        else:
            print("WARN: No Azure Storage credentials found. Falling back to local storage.")
            self.blob_service_client = None

    def upload_file(self, file_path, blob_name):
        """Uploads a file to Azure Blob Storage or falls back to local."""
        if self.blob_service_client:
            try:
                blob_client = self.blob_service_client.get_blob_client(container=self.container_name, blob=blob_name)
                with open(file_path, "rb") as data:
                    blob_client.upload_blob(data, overwrite=True)
                return blob_client.url
            except Exception as e:
                print(f"ERROR: Azure Upload Failed: {e}")
                return file_path # Fallback to local path
        return file_path

    def download_file(self, blob_name, destination_path):
        """Downloads a blob to a local path."""
        if self.blob_service_client:
            try:
                blob_client = self.blob_service_client.get_blob_client(container=self.container_name, blob=blob_name)
                with open(destination_path, "wb") as file:
                    file.write(blob_client.download_blob().readall())
                return destination_path
            except Exception as e:
                print(f"ERROR: Azure Download Failed: {e}")
                return None
        return destination_path

    def save_json_artifact(self, doc_id: str, artifact_type: str, data):
        """Uploads JSON artifact data (functional_spec, gaps, backlog, test_cases) to Azure Blob Storage."""
        import json
        blob_name = f"artifacts/{doc_id}/{artifact_type}.json"
        json_bytes = json.dumps(data, indent=2).encode('utf-8') if not isinstance(data, (str, bytes)) else (data.encode('utf-8') if isinstance(data, str) else data)

        if self.blob_service_client:
            try:
                blob_client = self.blob_service_client.get_blob_client(container=self.container_name, blob=blob_name)
                blob_client.upload_blob(json_bytes, overwrite=True)
                print(f"INFO: Saved artifact '{artifact_type}' to Azure Blob: {blob_name}")
                return blob_client.url
            except Exception as e:
                print(f"ERROR: Failed to save artifact '{artifact_type}' to Azure Blob: {e}")
        
        # Local fallback persistence
        try:
            local_dir = os.path.join(os.path.dirname(__file__), "..", "local_artifacts", doc_id)
            os.makedirs(local_dir, exist_ok=True)
            local_path = os.path.join(local_dir, f"{artifact_type}.json")
            with open(local_path, "wb") as f:
                f.write(json_bytes)
            return local_path
        except Exception as local_err:
            print(f"WARN: Local artifact save fallback failed: {local_err}")
            return None

    def load_json_artifact(self, doc_id: str, artifact_type: str):
        """Downloads and loads JSON artifact data from Azure Blob Storage or local fallback."""
        import json
        blob_name = f"artifacts/{doc_id}/{artifact_type}.json"
        if self.blob_service_client:
            try:
                blob_client = self.blob_service_client.get_blob_client(container=self.container_name, blob=blob_name)
                blob_data = blob_client.download_blob().readall().decode('utf-8')
                from utils.json_extractor import extract_json_from_llm_response
                res = extract_json_from_llm_response(blob_data)
                if isinstance(res, (dict, list)) and "error" not in res:
                    return res
                try:
                    return json.loads(blob_data, strict=False)
                except Exception:
                    return res if isinstance(res, (dict, list)) else blob_data
            except Exception:
                pass

        # Try local fallback
        try:
            local_path = os.path.join(os.path.dirname(__file__), "..", "local_artifacts", doc_id, f"{artifact_type}.json")
            if os.path.exists(local_path):
                with open(local_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    from utils.json_extractor import extract_json_from_llm_response
                    res = extract_json_from_llm_response(content)
                    if isinstance(res, (dict, list)) and "error" not in res:
                        return res
                    try:
                        return json.loads(content, strict=False)
                    except Exception:
                        return res if isinstance(res, (dict, list)) else content
        except Exception:
            pass

        return None

    def save_blob_artifact(self, doc_id: str, artifact_type: str, byte_data: bytes, ext: str = "pdf"):
        """Uploads binary artifact data (e.g. PDF package) to Azure Blob Storage or local fallback."""
        blob_name = f"artifacts/{doc_id}/{artifact_type}.{ext}"
        if self.blob_service_client:
            try:
                blob_client = self.blob_service_client.get_blob_client(container=self.container_name, blob=blob_name)
                blob_client.upload_blob(byte_data, overwrite=True)
                print(f"INFO: Saved binary blob artifact '{artifact_type}.{ext}' to Azure Blob: {blob_name}")
                return blob_client.url
            except Exception as e:
                print(f"ERROR: Failed to save binary blob '{artifact_type}.{ext}' to Azure Blob: {e}")
        
        try:
            local_dir = os.path.join(os.path.dirname(__file__), "..", "local_artifacts", doc_id)
            os.makedirs(local_dir, exist_ok=True)
            local_path = os.path.join(local_dir, f"{artifact_type}.{ext}")
            with open(local_path, "wb") as f:
                f.write(byte_data)
            return local_path
        except Exception as local_err:
            print(f"WARN: Local binary artifact save fallback failed: {local_err}")
            return None

    def load_blob_artifact(self, doc_id: str, artifact_type: str, ext: str = "pdf") -> bytes:
        """Downloads binary artifact data (e.g. PDF package) from Azure Blob Storage or local fallback."""
        blob_name = f"artifacts/{doc_id}/{artifact_type}.{ext}"
        if self.blob_service_client:
            try:
                blob_client = self.blob_service_client.get_blob_client(container=self.container_name, blob=blob_name)
                return blob_client.download_blob().readall()
            except Exception:
                pass

        try:
            local_path = os.path.join(os.path.dirname(__file__), "..", "local_artifacts", doc_id, f"{artifact_type}.{ext}")
            if os.path.exists(local_path):
                with open(local_path, "rb") as f:
                    return f.read()
        except Exception:
            pass

        return None

storage_service = AzureStorageService()
