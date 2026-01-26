"""
NexusAI OAuth Module

OAuth2 integration for third-party authentication providers.
Currently supports Google OAuth2.
"""

import os
import secrets
from typing import Optional, Tuple, Dict, Any
from urllib.parse import urlencode
import logging

import httpx

from src.auth.schemas import GoogleUserInfo, OAuthState


logger = logging.getLogger(__name__)


class OAuthError(Exception):
    """Exception for OAuth-related errors."""
    
    def __init__(self, message: str, provider: str = "unknown"):
        super().__init__(message)
        self.provider = provider


class OAuthConfig:
    """OAuth configuration container."""
    
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        scopes: list,
        authorize_url: str,
        token_url: str,
        userinfo_url: str,
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.scopes = scopes
        self.authorize_url = authorize_url
        self.token_url = token_url
        self.userinfo_url = userinfo_url


def get_google_oauth_config() -> OAuthConfig:
    """
    Get Google OAuth configuration from environment.
    
    Returns:
        OAuthConfig: Google OAuth settings
        
    Raises:
        OAuthError: If required environment variables are missing
    """
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    redirect_uri = os.getenv(
        "GOOGLE_REDIRECT_URI",
        "http://localhost:8000/api/auth/oauth/google/callback"
    )
    
    if not client_id or not client_secret:
        raise OAuthError(
            "Google OAuth not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET",
            provider="google"
        )
    
    return OAuthConfig(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        scopes=["openid", "email", "profile"],
        authorize_url="https://accounts.google.com/o/oauth2/v2/auth",
        token_url="https://oauth2.googleapis.com/token",
        userinfo_url="https://www.googleapis.com/oauth2/v2/userinfo",
    )


def generate_oauth_state() -> str:
    """Generate a secure state parameter for OAuth CSRF protection."""
    return secrets.token_urlsafe(32)


class GoogleOAuth:
    """
    Google OAuth2 handler.
    
    Implements the OAuth2 authorization code flow for Google.
    """
    
    def __init__(self, config: Optional[OAuthConfig] = None):
        """
        Initialize Google OAuth handler.
        
        Args:
            config: OAuth configuration (will fetch from env if not provided)
        """
        self._config = config
    
    @property
    def config(self) -> OAuthConfig:
        """Get OAuth config, lazily initialized."""
        if self._config is None:
            self._config = get_google_oauth_config()
        return self._config
    
    def get_authorization_url(
        self,
        state: Optional[str] = None,
        redirect_uri: Optional[str] = None,
    ) -> Tuple[str, str]:
        """
        Generate the Google OAuth authorization URL.
        
        Args:
            state: Custom state parameter (generated if not provided)
            redirect_uri: Custom redirect URI (uses config default if not provided)
            
        Returns:
            Tuple[str, str]: (authorization_url, state)
        """
        if state is None:
            state = generate_oauth_state()
        
        params = {
            "client_id": self.config.client_id,
            "redirect_uri": redirect_uri or self.config.redirect_uri,
            "response_type": "code",
            "scope": " ".join(self.config.scopes),
            "state": state,
            "access_type": "offline",  # Request refresh token
            "prompt": "consent",  # Force consent to get refresh token
        }
        
        auth_url = f"{self.config.authorize_url}?{urlencode(params)}"
        return auth_url, state
    
    async def exchange_code(
        self,
        code: str,
        redirect_uri: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Exchange authorization code for tokens.
        
        Args:
            code: Authorization code from callback
            redirect_uri: Redirect URI (must match the one used in authorization)
            
        Returns:
            Dict containing access_token, refresh_token, etc.
            
        Raises:
            OAuthError: If token exchange fails
        """
        data = {
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri or self.config.redirect_uri,
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    self.config.token_url,
                    data=data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"Google token exchange failed: {e.response.text}")
                raise OAuthError(
                    f"Failed to exchange authorization code: {e.response.status_code}",
                    provider="google"
                )
            except httpx.RequestError as e:
                logger.error(f"Google token request failed: {e}")
                raise OAuthError(
                    "Failed to connect to Google OAuth server",
                    provider="google"
                )
    
    async def get_user_info(self, access_token: str) -> GoogleUserInfo:
        """
        Get user information from Google.
        
        Args:
            access_token: OAuth access token
            
        Returns:
            GoogleUserInfo: User profile data
            
        Raises:
            OAuthError: If user info request fails
        """
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    self.config.userinfo_url,
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                response.raise_for_status()
                data = response.json()
                return GoogleUserInfo(**data)
            except httpx.HTTPStatusError as e:
                logger.error(f"Google user info request failed: {e.response.text}")
                raise OAuthError(
                    f"Failed to get user info: {e.response.status_code}",
                    provider="google"
                )
            except httpx.RequestError as e:
                logger.error(f"Google user info request failed: {e}")
                raise OAuthError(
                    "Failed to connect to Google API",
                    provider="google"
                )
    
    async def authenticate(
        self,
        code: str,
        redirect_uri: Optional[str] = None,
    ) -> Tuple[GoogleUserInfo, Dict[str, Any]]:
        """
        Complete OAuth flow: exchange code and get user info.
        
        Args:
            code: Authorization code from callback
            redirect_uri: Redirect URI
            
        Returns:
            Tuple[GoogleUserInfo, Dict]: (user_info, token_data)
        """
        # Exchange code for tokens
        token_data = await self.exchange_code(code, redirect_uri)
        access_token = token_data.get("access_token")
        
        if not access_token:
            raise OAuthError("No access token in response", provider="google")
        
        # Get user info
        user_info = await self.get_user_info(access_token)
        
        return user_info, token_data


# Synchronous versions for non-async contexts

class GoogleOAuthSync:
    """Synchronous Google OAuth2 handler."""
    
    def __init__(self, config: Optional[OAuthConfig] = None):
        self._config = config
    
    @property
    def config(self) -> OAuthConfig:
        if self._config is None:
            self._config = get_google_oauth_config()
        return self._config
    
    def get_authorization_url(
        self,
        state: Optional[str] = None,
        redirect_uri: Optional[str] = None,
    ) -> Tuple[str, str]:
        """Generate Google OAuth authorization URL."""
        if state is None:
            state = generate_oauth_state()
        
        params = {
            "client_id": self.config.client_id,
            "redirect_uri": redirect_uri or self.config.redirect_uri,
            "response_type": "code",
            "scope": " ".join(self.config.scopes),
            "state": state,
            "access_type": "offline",
            "prompt": "consent",
        }
        
        auth_url = f"{self.config.authorize_url}?{urlencode(params)}"
        return auth_url, state
    
    def exchange_code(
        self,
        code: str,
        redirect_uri: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Exchange authorization code for tokens."""
        data = {
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri or self.config.redirect_uri,
        }
        
        with httpx.Client() as client:
            try:
                response = client.post(
                    self.config.token_url,
                    data=data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                raise OAuthError(
                    f"Failed to exchange code: {e.response.status_code}",
                    provider="google"
                )
    
    def get_user_info(self, access_token: str) -> GoogleUserInfo:
        """Get user information from Google."""
        with httpx.Client() as client:
            try:
                response = client.get(
                    self.config.userinfo_url,
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                response.raise_for_status()
                return GoogleUserInfo(**response.json())
            except httpx.HTTPStatusError as e:
                raise OAuthError(
                    f"Failed to get user info: {e.response.status_code}",
                    provider="google"
                )


# Default Google OAuth instance
google_oauth = GoogleOAuth()
google_oauth_sync = GoogleOAuthSync()
