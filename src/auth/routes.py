"""
LaunchForge Authentication API Routes

REST API endpoints for authentication operations.
Designed for use with FastAPI or similar frameworks.
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone

from src.database.db import get_db, get_session
from src.database.models import User
from src.auth.service import (
    AuthService,
    AuthError,
    UserExistsError,
    InvalidCredentialsError,
    UserNotFoundError,
    EmailNotVerifiedError,
)
from src.auth.password import PasswordStrengthError
from src.auth.jwt import (
    TokenError,
    TokenExpiredError,
    InvalidTokenError,
)
from src.auth.oauth import GoogleOAuth, OAuthError, generate_oauth_state
from src.auth.schemas import (
    RegisterRequest,
    LoginRequest,
    RefreshRequest,
    VerifyEmailRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    ChangePasswordRequest,
    TokenResponse,
    UserResponse,
    AuthError as AuthErrorSchema,
)
from src.auth.middleware import (
    get_current_user_id,
    extract_token_from_header,
    AuthenticationError,
)


logger = logging.getLogger(__name__)


# OAuth state storage (in production, use Redis or database)
_oauth_states: Dict[str, Dict[str, Any]] = {}


class AuthRoutes:
    """
    Authentication route handlers.
    
    These methods can be adapted for use with any web framework
    (FastAPI, Flask, etc.) by wrapping them in appropriate route decorators.
    """
    
    @staticmethod
    def register(request: RegisterRequest) -> Dict[str, Any]:
        """
        Register a new user.
        
        POST /api/auth/register
        
        Args:
            request: Registration data
            
        Returns:
            dict: User data and verification info
        """
        db = get_db()
        with db.session() as session:
            auth_service = AuthService(session)
            
            try:
                user, verification_token = auth_service.register(
                    email=request.email,
                    password=request.password,
                    name=request.name,
                )
                
                session.commit()
                
                return {
                    "status": "success",
                    "message": "Registration successful. Please check your email to verify your account.",
                    "user": {
                        "id": user.id,
                        "email": user.email,
                        "email_verified": user.email_verified,
                    },
                    # In production, send this via email instead
                    "verification_token": verification_token,
                }
                
            except UserExistsError:
                return {
                    "status": "error",
                    "error": "user_exists",
                    "message": "An account with this email already exists",
                }
            except PasswordStrengthError as e:
                return {
                    "status": "error",
                    "error": "weak_password",
                    "message": str(e),
                    "details": e.errors,
                }
    
    @staticmethod
    def login(request: LoginRequest) -> Dict[str, Any]:
        """
        Authenticate user and return tokens.
        
        POST /api/auth/login
        
        Args:
            request: Login credentials
            
        Returns:
            dict: User data and tokens
        """
        db = get_db()
        with db.session() as session:
            auth_service = AuthService(session)
            
            try:
                user, tokens = auth_service.login(
                    email=request.email,
                    password=request.password,
                    require_verified=False,  # Allow unverified for now
                )
                
                session.commit()
                
                return {
                    "status": "success",
                    "message": "Login successful",
                    "user": auth_service.to_user_response(user).model_dump(),
                    "tokens": tokens.model_dump(),
                }
                
            except InvalidCredentialsError:
                return {
                    "status": "error",
                    "error": "invalid_credentials",
                    "message": "Invalid email or password",
                }
            except EmailNotVerifiedError:
                return {
                    "status": "error",
                    "error": "email_not_verified",
                    "message": "Please verify your email before logging in",
                }
    
    @staticmethod
    def refresh_token(request: RefreshRequest) -> Dict[str, Any]:
        """
        Refresh access token.
        
        POST /api/auth/refresh
        
        Args:
            request: Refresh token
            
        Returns:
            dict: New token pair
        """
        db = get_db()
        with db.session() as session:
            auth_service = AuthService(session)
            
            try:
                tokens = auth_service.refresh_tokens(request.refresh_token)
                
                return {
                    "status": "success",
                    "tokens": tokens.model_dump(),
                }
                
            except TokenExpiredError:
                return {
                    "status": "error",
                    "error": "token_expired",
                    "message": "Refresh token has expired. Please login again.",
                }
            except InvalidTokenError as e:
                return {
                    "status": "error",
                    "error": "invalid_token",
                    "message": str(e),
                }
    
    @staticmethod
    def logout(auth_header: Optional[str]) -> Dict[str, Any]:
        """
        Logout user (invalidate tokens).
        
        POST /api/auth/logout
        
        Note: With JWT, true logout requires token blacklisting.
        For now, we just confirm logout and let the client discard tokens.
        
        Args:
            auth_header: Authorization header
            
        Returns:
            dict: Logout confirmation
        """
        try:
            user_id = get_current_user_id(auth_header)
            logger.info(f"User logged out: {user_id}")
            
            return {
                "status": "success",
                "message": "Logged out successfully",
            }
        except AuthenticationError:
            # Even if token is invalid, consider logout successful
            return {
                "status": "success",
                "message": "Logged out successfully",
            }
    
    @staticmethod
    def verify_email(request: VerifyEmailRequest) -> Dict[str, Any]:
        """
        Verify user's email address.
        
        POST /api/auth/verify-email
        
        Args:
            request: Verification token
            
        Returns:
            dict: Verification status
        """
        db = get_db()
        with db.session() as session:
            auth_service = AuthService(session)
            
            try:
                user = auth_service.verify_email(request.token)
                session.commit()
                
                return {
                    "status": "success",
                    "message": "Email verified successfully",
                    "user": {
                        "id": user.id,
                        "email": user.email,
                        "email_verified": True,
                    },
                }
                
            except InvalidTokenError as e:
                return {
                    "status": "error",
                    "error": "invalid_token",
                    "message": str(e),
                }
    
    @staticmethod
    def forgot_password(request: ForgotPasswordRequest) -> Dict[str, Any]:
        """
        Request password reset.
        
        POST /api/auth/forgot-password
        
        Args:
            request: User's email
            
        Returns:
            dict: Always returns success (security: don't reveal if email exists)
        """
        db = get_db()
        with db.session() as session:
            auth_service = AuthService(session)
            
            reset_token = auth_service.request_password_reset(request.email)
            session.commit()
            
            # Always return success to prevent email enumeration
            response = {
                "status": "success",
                "message": "If an account exists with this email, a password reset link has been sent.",
            }
            
            # In development, include the token
            if reset_token:
                response["reset_token"] = reset_token  # Remove in production!
            
            return response
    
    @staticmethod
    def reset_password(request: ResetPasswordRequest) -> Dict[str, Any]:
        """
        Reset password with token.
        
        POST /api/auth/reset-password
        
        Args:
            request: Reset token and new password
            
        Returns:
            dict: Reset status
        """
        db = get_db()
        with db.session() as session:
            auth_service = AuthService(session)
            
            try:
                user = auth_service.reset_password(
                    token=request.token,
                    new_password=request.new_password,
                )
                session.commit()
                
                return {
                    "status": "success",
                    "message": "Password reset successful. You can now login with your new password.",
                }
                
            except InvalidTokenError as e:
                return {
                    "status": "error",
                    "error": "invalid_token",
                    "message": str(e),
                }
            except PasswordStrengthError as e:
                return {
                    "status": "error",
                    "error": "weak_password",
                    "message": str(e),
                    "details": e.errors,
                }
    
    @staticmethod
    def change_password(
        request: ChangePasswordRequest,
        auth_header: Optional[str],
    ) -> Dict[str, Any]:
        """
        Change password (authenticated user).
        
        POST /api/auth/change-password
        
        Args:
            request: Current and new password
            auth_header: Authorization header
            
        Returns:
            dict: Change status
        """
        try:
            user_id = get_current_user_id(auth_header)
        except AuthenticationError as e:
            return {
                "status": "error",
                "error": "unauthorized",
                "message": str(e),
            }
        
        db = get_db()
        with db.session() as session:
            auth_service = AuthService(session)
            
            try:
                auth_service.change_password(
                    user_id=user_id,
                    current_password=request.current_password,
                    new_password=request.new_password,
                )
                session.commit()
                
                return {
                    "status": "success",
                    "message": "Password changed successfully",
                }
                
            except InvalidCredentialsError:
                return {
                    "status": "error",
                    "error": "invalid_password",
                    "message": "Current password is incorrect",
                }
            except PasswordStrengthError as e:
                return {
                    "status": "error",
                    "error": "weak_password",
                    "message": str(e),
                    "details": e.errors,
                }
    
    @staticmethod
    def get_current_user(auth_header: Optional[str]) -> Dict[str, Any]:
        """
        Get current authenticated user.
        
        GET /api/auth/me
        
        Args:
            auth_header: Authorization header
            
        Returns:
            dict: Current user data
        """
        try:
            user_id = get_current_user_id(auth_header)
        except AuthenticationError as e:
            return {
                "status": "error",
                "error": "unauthorized",
                "message": str(e),
            }
        
        db = get_db()
        with db.session() as session:
            from src.database.repositories import UserRepository
            user_repo = UserRepository(session)
            
            user = user_repo.get(user_id)
            if not user:
                return {
                    "status": "error",
                    "error": "user_not_found",
                    "message": "User not found",
                }
            
            auth_service = AuthService(session)
            
            return {
                "status": "success",
                "user": auth_service.to_user_response(user).model_dump(),
            }
    
    @staticmethod
    def oauth_google_redirect() -> Dict[str, Any]:
        """
        Initiate Google OAuth flow.
        
        GET /api/auth/oauth/google
        
        Returns:
            dict: Authorization URL to redirect to
        """
        try:
            oauth = GoogleOAuth()
            state = generate_oauth_state()
            
            # Store state for verification
            _oauth_states[state] = {
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            
            auth_url, _ = oauth.get_authorization_url(state=state)
            
            return {
                "status": "success",
                "authorization_url": auth_url,
                "state": state,
            }
            
        except OAuthError as e:
            return {
                "status": "error",
                "error": "oauth_error",
                "message": str(e),
            }
    
    @staticmethod
    async def oauth_google_callback(
        code: str,
        state: str,
    ) -> Dict[str, Any]:
        """
        Handle Google OAuth callback.
        
        GET /api/auth/oauth/google/callback
        
        Args:
            code: Authorization code from Google
            state: State parameter for CSRF verification
            
        Returns:
            dict: User data and tokens
        """
        # Verify state
        if state not in _oauth_states:
            return {
                "status": "error",
                "error": "invalid_state",
                "message": "Invalid OAuth state parameter",
            }
        
        # Remove used state
        del _oauth_states[state]
        
        try:
            oauth = GoogleOAuth()
            user_info, token_data = await oauth.authenticate(code)
            
            # Create or link user
            db = get_db()
            with db.session() as session:
                auth_service = AuthService(session)
                
                user, is_new = auth_service.create_or_link_oauth_user(
                    email=user_info.email,
                    oauth_provider="google",
                    oauth_id=user_info.id,
                    name=user_info.name,
                    email_verified=user_info.verified_email,
                )
                
                # Generate tokens
                tokens = auth_service._generate_tokens(user)
                
                session.commit()
                
                return {
                    "status": "success",
                    "message": "Google login successful",
                    "is_new_user": is_new,
                    "user": auth_service.to_user_response(user).model_dump(),
                    "tokens": tokens.model_dump(),
                }
                
        except OAuthError as e:
            return {
                "status": "error",
                "error": "oauth_error",
                "message": str(e),
            }


# Convenience functions for direct use

def register_user(email: str, password: str, name: Optional[str] = None) -> Dict[str, Any]:
    """Register a new user."""
    request = RegisterRequest(email=email, password=password, name=name)
    return AuthRoutes.register(request)


def login_user(email: str, password: str) -> Dict[str, Any]:
    """Login a user."""
    request = LoginRequest(email=email, password=password)
    return AuthRoutes.login(request)


def refresh_access_token(refresh_token: str) -> Dict[str, Any]:
    """Refresh an access token."""
    request = RefreshRequest(refresh_token=refresh_token)
    return AuthRoutes.refresh_token(request)


def verify_user_email(token: str) -> Dict[str, Any]:
    """Verify user's email."""
    request = VerifyEmailRequest(token=token)
    return AuthRoutes.verify_email(request)


def request_password_reset(email: str) -> Dict[str, Any]:
    """Request a password reset."""
    request = ForgotPasswordRequest(email=email)
    return AuthRoutes.forgot_password(request)


def reset_user_password(token: str, new_password: str) -> Dict[str, Any]:
    """Reset user's password."""
    request = ResetPasswordRequest(token=token, new_password=new_password)
    return AuthRoutes.reset_password(request)
