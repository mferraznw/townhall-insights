"""
Configuration management for Azure services
"""
import os
from typing import Optional
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient


class Config:
    """Configuration manager for Azure services"""
    
    def __init__(self):
        self.environment = os.getenv('ENVIRONMENT', 'development')
        
        # Only initialize DefaultAzureCredential if Key Vault URL is provided
        key_vault_url = os.getenv('AZURE_KEY_VAULT_URL')
        if key_vault_url:
            try:
                self.credential = DefaultAzureCredential()
                self.key_vault_client = SecretClient(
                    vault_url=key_vault_url, 
                    credential=self.credential
                )
            except Exception:
                self.key_vault_client = None
        else:
            self.key_vault_client = None
    
    def get_secret(self, secret_name: str) -> Optional[str]:
        """Get secret from Key Vault or environment variables"""
        if self.key_vault_client:
            try:
                secret = self.key_vault_client.get_secret(secret_name)
                return secret.value
            except Exception:
                # Fallback to environment variable
                return os.getenv(secret_name)
        return os.getenv(secret_name)
    
    def _get_required_config(self, key: str, default: Optional[str] = None) -> str:
        """Get required configuration value and ensure it's a string"""
        value = self.get_secret(key) or os.getenv(key) or default
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
        value = self.get_secret('AZURE_AI_LANGUAGE_ENDPOINT') or os.getenv('AZURE_AI_LANGUAGE_ENDPOINT')
        return str(value) if value else ""
    
    @property
    def azure_ai_language_key(self) -> str:
        value = self.get_secret('AZURE_AI_LANGUAGE_KEY') or os.getenv('AZURE_AI_LANGUAGE_KEY')
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


# Global config instance
config = Config()
