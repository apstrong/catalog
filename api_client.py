import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class OmniAPIClient:
    def __init__(self):
        self.api_key = os.getenv("OMNI_API_KEY")
        self.base_url = os.getenv("OMNI_BASE_URL")
        if not self.api_key:
            raise ValueError("OMNI_API_KEY not found in environment variables")
        
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def get_models(self, model_kind="SHARED", sort_field="name", sort_direction="asc", page_size=10, cursor=None):
        """Fetch available models from the Omni API"""
        endpoint = f"{self.base_url}/api/unstable/models"
        params = {
            "modelKind": model_kind,
            "sortField": sort_field,
            "sortDirection": sort_direction,
            "pageSize": page_size
        }
        
        if cursor:
            params["cursor"] = cursor
        
        try:
            response = requests.get(endpoint, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching models: {str(e)}")
            return None

    def get_model_yaml(self, model_id):
        """Fetch YAML configuration for a specific model"""
        endpoint = f"{self.base_url}/api/unstable/models/{model_id}/yaml"
        params = {
            "mode": "combined"
        }
        
        try:
            response = requests.get(endpoint, headers=self.headers, params=params)
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException as e:
            print(f"Error fetching model YAML: {str(e)}")
            return None 