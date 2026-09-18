import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()

class AzureDocIntelService:
    def __init__(self):
        self.key = os.getenv("DOC_INTEL_CREDENTIAL")
        self.endpoint = os.getenv("AZURE_DOC_INTEL_ENDPOINT")
        self.api_version = "2023-07-31"

    def extract_text(self, file_path: str):
        """
        Uploads a file to Azure Document Intelligence and returns the extracted content.
        Uses the 'prebuilt-read' model for high-fidelity OCR and layout preservation.
        """
        if not self.key or not self.endpoint:
            print("ERROR: Azure Document Intelligence credentials missing in .env")
            return None

        url = f"{self.endpoint}/formrecognizer/documentModels/prebuilt-read:analyze?api-version={self.api_version}"
        headers = {
            "Ocp-Apim-Subscription-Key": self.key,
            "Content-Type": "application/octet-stream"
        }

        try:
            with open(file_path, "rb") as f:
                payload = f.read()

            # 1. Start Analysis
            response = requests.post(url, headers=headers, data=payload)
            if response.status_code != 202:
                print(f"ADI Error Start: {response.text}")
                return None

            result_url = response.headers["Operation-Location"]

            # 2. Poll for Results
            print("INFO: Polling Azure Document Intelligence for results...")
            while True:
                fetch_res = requests.get(result_url, headers={"Ocp-Apim-Subscription-Key": self.key})
                status_data = fetch_res.json()
                status = status_data.get("status")

                if status == "succeeded":
                    # 3. Aggregate Content
                    content = ""
                    for page in status_data.get("analyzeResult", {}).get("pages", []):
                        for line in page.get("lines", []):
                            content += line.get("content", "") + "\n"
                    print(f"INFO: ADI Successfully extracted {len(content)} characters.")
                    return content
                
                if status == "failed":
                    print(f"ADI Error Failed: {status_data}")
                    return None

                time.sleep(1) # Wait and poll again

        except Exception as e:
            print(f"ADI Exception: {str(e)}")
            return None
