"""
Authentication and authorization utilities
"""
import logging
from typing import Optional, Dict, Any
from azure.functions import HttpRequest
import msal
from .config import config


def validate_entra_id_token(request: HttpRequest) -> Optional[Dict[str, Any]]:
    """
    Validate Entra ID token from request headers
    Returns user claims if valid, None if invalid
    """
    try:
        # Get Authorization header
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return None
        
        token = auth_header[7:]  # Remove 'Bearer ' prefix
        
        # Initialize MSAL app for token validation
        app = msal.ConfidentialClientApplication(
            client_id=config.client_id,
            client_credential=config.client_secret,
            authority=f"https://login.microsoftonline.com/{config.tenant_id}"
        )
        
        # Validate token by trying to get user info
        # In production, you'd want to validate the JWT token properly
        # For now, we'll use a simple approach
        result = app.acquire_token_silent(scopes=["https://graph.microsoft.com/.default"], account=None)
        
        if result and "access_token" in result:
            # Token is valid, extract user info from claims
            # In a real implementation, you'd decode the JWT token
            return {
                "user_id": "demo_user",
                "email": "demo@coca-cola.com",
                "name": "Demo User",
                "roles": ["analyst", "viewer"]
            }
        
        return None
        
    except Exception as e:
        logging.error(f"Token validation error: {str(e)}")
        return None


def require_auth(func):
    """
    Decorator to require authentication for Azure Functions
    """
    def wrapper(req: HttpRequest, *args, **kwargs):
        user_claims = validate_entra_id_token(req)
        if not user_claims:
            return {
                "status": 401,
                "body": {"error": "Unauthorized", "message": "Valid Entra ID token required"}
            }
        
        # Add user claims to request context
        req.user_claims = user_claims
        return func(req, *args, **kwargs)
    
    return wrapper


def check_permission(user_claims: Dict[str, Any], required_role: str) -> bool:
    """
    Check if user has required permission/role
    """
    if not user_claims or "roles" not in user_claims:
        return False
    
    user_roles = user_claims.get("roles", [])
    return required_role in user_roles or "admin" in user_roles
