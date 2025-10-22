import os
import json
from typing import Optional


class Config:
    """Configuration manager for Azure services"""
    
    def __init__(self):
        self.environment = os.getenv('ENVIRONMENT', 'development')
        self.key_vault_client = None
        self._load_local_settings()
    
    def _load_local_settings(self):
        """Load local.settings.json for local development"""
        settings_file = 'local.settings.json'
        paths_to_try = [
            settings_file,
            os.path.join(os.path.dirname(__file__), '..', settings_file),
            os.path.join(os.getcwd(), settings_file)
        ]
        
        for path in paths_to_try:
            if os.path.exists(path):
                try:
                    with open(path, 'r') as f:
                        settings = json.load(f)
                        values = settings.get('Values', {})
                        for key, value in values.items():
                            if key not in os.environ:
                                os.environ[key] = str(value)
                        return
                except Exception:
                    pass
    
    def _get_required_config(self, key: str, default: Optional[str] = None) -> str:
        value = os.getenv(key) or default
        if value is None:
            raise ValueError(f"Required configuration '{key}' is not set")
        return str(value)
    
    @property
    def azure_search_endpoint(self) -> str:
        return self._get_required_config('AZURE_SEARCH_ENDPOINT')
    
    @property
    def azure_search_key(self) -> str:
        return self._get_required_config('AZURE_SEARCH_KEY')
    
    @property
    def azure_search_index_name(self) -> str:
        return self._get_required_config('AZURE_SEARCH_INDEX_NAME', 'utterances')
    
    @property
    def storage_connection_string(self) -> str:
        return self._get_required_config('AZURE_STORAGE_CONNECTION_STRING')
    
    @property
    def data_lake_connection_string(self) -> str:
        return self._get_required_config('DATA_LAKE_CONNECTION_STRING')
    
    @property
    def azure_openai_endpoint(self) -> str:
        return self._get_required_config('AZURE_OPENAI_ENDPOINT')
    
    @property
    def azure_openai_api_key(self) -> str:
        return self._get_required_config('AZURE_OPENAI_API_KEY')
    
    @property
    def azure_openai_deployment_name(self) -> str:
        return self._get_required_config('AZURE_OPENAI_DEPLOYMENT_NAME', 'gpt-4')
    
    @property
    def azure_openai_embedding_deployment(self) -> str:
        return self._get_required_config('AZURE_OPENAI_EMBEDDING_DEPLOYMENT', 'text-embedding-ada-002')
    
    @property
    def azure_ai_language_endpoint(self) -> str:
        value = os.getenv('AZURE_AI_LANGUAGE_ENDPOINT')
        return str(value) if value else ""
    
    @property
    def azure_ai_language_key(self) -> str:
        value = os.getenv('AZURE_AI_LANGUAGE_KEY')
        return str(value) if value else ""
    
    @property
    def tenant_id(self) -> str:
        return self._get_required_config('TENANT_ID')
    
    @property
    def client_id(self) -> str:
        return self._get_required_config('CLIENT_ID')
    
    @property
    def client_secret(self) -> str:
        return self._get_required_config('CLIENT_SECRET')
    
    @property
    def graph_api_endpoint(self) -> str:
        return self._get_required_config('GRAPH_API_ENDPOINT', 'https://graph.microsoft.com/v1.0')


config = Config()