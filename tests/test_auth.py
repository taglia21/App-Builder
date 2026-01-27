"""
NexusAI Authentication Tests

Comprehensive tests for authentication system:
- Password hashing and validation
- JWT token generation and verification
- User registration and login
- Email verification
- Password reset
- OAuth integration
"""

import pytest
import time
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database.models import Base, User, SubscriptionTier
from src.auth.password import (
    hash_password,
    verify_password,
    validate_password_strength,
    get_password_strength_score,
    PasswordStrengthError,
    check_password_strength,
)
from src.auth.jwt import (
    create_access_token,
    create_refresh_token,
    create_email_verification_token,
    create_password_reset_token,
    verify_token,
    decode_token,
    get_token_expiry,
    is_token_expired,
    get_user_id_from_token,
    TokenType,
    TokenExpiredError,
    InvalidTokenError,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)
from src.auth.tokens import (
    generate_secure_token,
    generate_verification_token,
    generate_reset_token,
    verify_reset_token,
    generate_api_token,
    verify_api_token,
    mask_token,
)
from src.auth.service import (
    AuthService,
    AuthError,
    UserExistsError,
    InvalidCredentialsError,
    UserNotFoundError,
)
from src.auth.middleware import (
    extract_token_from_header,
    get_current_user_id,
    AuthenticationError,
    JWTMiddleware,
)
from src.auth.schemas import (
    RegisterRequest,
    LoginRequest,
    ResetPasswordRequest,
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture(scope="function")
def engine():
    """Create a fresh SQLite in-memory engine for each test."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="function")
def session(engine):
    """Create a new session for each test."""
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def sample_user(session):
    """Create a sample user for testing."""
    from src.auth.password import hash_password
    
    user = User(
        id=str(uuid4()),
        email="test@example.com",
        password_hash=hash_password("TestPass123"),
        subscription_tier=SubscriptionTier.FREE,
        credits_remaining=100,
        email_verified=False,
    )
    session.add(user)
    session.commit()
    return user


@pytest.fixture
def verified_user(session):
    """Create a verified user for testing."""
    from src.auth.password import hash_password
    
    user = User(
        id=str(uuid4()),
        email="verified@example.com",
        password_hash=hash_password("TestPass123"),
        subscription_tier=SubscriptionTier.PRO,
        credits_remaining=10000,
        email_verified=True,
    )
    session.add(user)
    session.commit()
    return user


# =============================================================================
# PASSWORD TESTS
# =============================================================================

class TestPasswordHashing:
    """Tests for password hashing and verification."""
    
    def test_hash_password(self):
        """Test password hashing creates valid hash."""
        password = "SecurePass123!"
        hashed = hash_password(password)
        
        assert hashed != password
        assert len(hashed) > 0
        assert hashed.startswith("$2")  # bcrypt prefix
    
    def test_hash_is_unique(self):
        """Test each hash is unique (different salt)."""
        password = "SecurePass123!"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        
        assert hash1 != hash2
    
    def test_verify_correct_password(self):
        """Test verifying correct password."""
        password = "SecurePass123!"
        hashed = hash_password(password)
        
        assert verify_password(password, hashed) is True
    
    def test_verify_wrong_password(self):
        """Test verifying wrong password."""
        password = "SecurePass123!"
        wrong_password = "WrongPass123!"
        hashed = hash_password(password)
        
        assert verify_password(wrong_password, hashed) is False
    
    def test_verify_handles_invalid_hash(self):
        """Test verify handles invalid hash gracefully."""
        assert verify_password("password", "invalid_hash") is False
        assert verify_password("password", "") is False


class TestPasswordStrength:
    """Tests for password strength validation."""
    
    def test_valid_password(self):
        """Test valid password passes validation."""
        is_valid, errors = validate_password_strength("SecurePass123")
        
        assert is_valid is True
        assert len(errors) == 0
    
    def test_too_short(self):
        """Test password too short fails."""
        is_valid, errors = validate_password_strength("Short1")
        
        assert is_valid is False
        assert any("8 characters" in e for e in errors)
    
    def test_missing_uppercase(self):
        """Test password without uppercase fails."""
        is_valid, errors = validate_password_strength("lowercase123")
        
        assert is_valid is False
        assert any("uppercase" in e for e in errors)
    
    def test_missing_lowercase(self):
        """Test password without lowercase fails."""
        is_valid, errors = validate_password_strength("UPPERCASE123")
        
        assert is_valid is False
        assert any("lowercase" in e for e in errors)
    
    def test_missing_digit(self):
        """Test password without digit fails."""
        is_valid, errors = validate_password_strength("NoDigitsHere")
        
        assert is_valid is False
        assert any("digit" in e for e in errors)
    
    def test_multiple_failures(self):
        """Test password with multiple issues."""
        is_valid, errors = validate_password_strength("weak")
        
        assert is_valid is False
        assert len(errors) >= 3
    
    def test_check_password_strength_raises(self):
        """Test check_password_strength raises on weak password."""
        with pytest.raises(PasswordStrengthError) as exc_info:
            check_password_strength("weak")
        
        assert len(exc_info.value.errors) > 0
    
    def test_password_strength_score(self):
        """Test password strength scoring."""
        weak_score = get_password_strength_score("weak")
        strong_score = get_password_strength_score("SecureP@ssw0rd123!")
        
        assert weak_score["score"] < strong_score["score"]
        assert weak_score["strength"] == "weak"
        assert strong_score["strength"] in ["good", "strong"]


# =============================================================================
# JWT TOKEN TESTS
# =============================================================================

class TestJWTTokens:
    """Tests for JWT token generation and verification."""
    
    def test_create_access_token(self):
        """Test access token creation."""
        user_id = str(uuid4())
        token = create_access_token(user_id, "test@example.com")
        
        assert token is not None
        assert len(token) > 0
    
    def test_verify_access_token(self):
        """Test access token verification."""
        user_id = str(uuid4())
        email = "test@example.com"
        token = create_access_token(user_id, email)
        
        payload = verify_token(token, TokenType.ACCESS)
        
        assert payload["sub"] == user_id
        assert payload["email"] == email
        assert payload["type"] == "access"
    
    def test_create_refresh_token(self):
        """Test refresh token creation."""
        user_id = str(uuid4())
        token = create_refresh_token(user_id)
        
        assert token is not None
        
        payload = verify_token(token, TokenType.REFRESH)
        assert payload["sub"] == user_id
        assert payload["type"] == "refresh"
    
    def test_token_type_mismatch(self):
        """Test verifying wrong token type fails."""
        user_id = str(uuid4())
        access_token = create_access_token(user_id, "test@example.com")
        
        with pytest.raises(InvalidTokenError) as exc_info:
            verify_token(access_token, TokenType.REFRESH)
        
        assert "Expected refresh" in str(exc_info.value)
    
    def test_expired_token(self):
        """Test expired token raises error."""
        user_id = str(uuid4())
        token = create_access_token(
            user_id,
            "test@example.com",
            expires_delta=timedelta(seconds=-1),  # Already expired
        )
        
        with pytest.raises(TokenExpiredError):
            verify_token(token, TokenType.ACCESS)
    
    def test_invalid_token(self):
        """Test invalid token raises error."""
        with pytest.raises(InvalidTokenError):
            verify_token("invalid.token.here", TokenType.ACCESS)
    
    def test_decode_token(self):
        """Test token decoding without verification."""
        user_id = str(uuid4())
        token = create_access_token(user_id, "test@example.com")
        
        payload = decode_token(token)
        
        assert payload["sub"] == user_id
    
    def test_get_token_expiry(self):
        """Test getting token expiry time."""
        user_id = str(uuid4())
        token = create_access_token(user_id, "test@example.com")
        
        expiry = get_token_expiry(token)
        
        assert expiry is not None
        assert expiry > datetime.now(timezone.utc)
    
    def test_is_token_expired(self):
        """Test checking token expiration."""
        user_id = str(uuid4())
        
        valid_token = create_access_token(user_id, "test@example.com")
        expired_token = create_access_token(
            user_id,
            "test@example.com",
            expires_delta=timedelta(seconds=-1),
        )
        
        assert is_token_expired(valid_token) is False
        assert is_token_expired(expired_token) is True
    
    def test_get_user_id_from_token(self):
        """Test extracting user ID from token."""
        user_id = str(uuid4())
        token = create_access_token(user_id, "test@example.com")
        
        extracted_id = get_user_id_from_token(token)
        
        assert extracted_id == user_id
    
    def test_additional_claims(self):
        """Test adding custom claims to token."""
        user_id = str(uuid4())
        token = create_access_token(
            user_id,
            "test@example.com",
            additional_claims={"role": "admin", "tier": "pro"},
        )
        
        payload = verify_token(token, TokenType.ACCESS)
        
        assert payload["role"] == "admin"
        assert payload["tier"] == "pro"
    
    def test_email_verification_token(self):
        """Test email verification token."""
        user_id = str(uuid4())
        email = "test@example.com"
        token = create_email_verification_token(user_id, email)
        
        payload = verify_token(token, TokenType.EMAIL_VERIFICATION)
        
        assert payload["sub"] == user_id
        assert payload["email"] == email
    
    def test_password_reset_token(self):
        """Test password reset token."""
        user_id = str(uuid4())
        email = "test@example.com"
        token = create_password_reset_token(user_id, email)
        
        payload = verify_token(token, TokenType.PASSWORD_RESET)
        
        assert payload["sub"] == user_id


# =============================================================================
# TOKEN UTILITIES TESTS
# =============================================================================

class TestTokenUtilities:
    """Tests for token utility functions."""
    
    def test_generate_secure_token(self):
        """Test secure token generation."""
        token = generate_secure_token(32)
        
        assert len(token) == 64  # 32 bytes = 64 hex chars
    
    def test_tokens_are_unique(self):
        """Test tokens are unique."""
        tokens = [generate_secure_token() for _ in range(100)]
        
        assert len(set(tokens)) == 100
    
    def test_generate_verification_token(self):
        """Test verification token generation."""
        token = generate_verification_token()
        
        assert len(token) > 0
    
    def test_generate_reset_token(self):
        """Test reset token generation with expiry."""
        token, expires_at = generate_reset_token()
        
        assert len(token) > 0
        assert expires_at > datetime.now(timezone.utc)
    
    def test_verify_reset_token_valid(self):
        """Test verifying valid reset token."""
        token, expires_at = generate_reset_token()
        
        is_valid, error = verify_reset_token(token, token, expires_at)
        
        assert is_valid is True
        assert error is None
    
    def test_verify_reset_token_expired(self):
        """Test verifying expired reset token."""
        token = generate_secure_token()
        expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        
        is_valid, error = verify_reset_token(token, token, expires_at)
        
        assert is_valid is False
        assert "expired" in error.lower()
    
    def test_verify_reset_token_mismatch(self):
        """Test verifying wrong reset token."""
        token1 = generate_secure_token()
        token2 = generate_secure_token()
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        
        is_valid, error = verify_reset_token(token1, token2, expires_at)
        
        assert is_valid is False
        assert "invalid" in error.lower()
    
    def test_generate_api_token(self):
        """Test API token generation."""
        full_token, token_hash = generate_api_token()
        
        assert full_token.startswith("lf_")
        assert len(token_hash) == 64  # SHA-256 hex
    
    def test_verify_api_token(self):
        """Test API token verification."""
        full_token, token_hash = generate_api_token()
        
        assert verify_api_token(full_token, token_hash) is True
        assert verify_api_token("wrong_token", token_hash) is False
    
    def test_mask_token(self):
        """Test token masking."""
        token = "lf_abc12345_secretsecret"
        masked = mask_token(token, 4)
        
        assert token[:4] in masked
        assert token[-4:] in masked
        assert "secret" not in masked


# =============================================================================
# AUTH SERVICE TESTS
# =============================================================================

class TestAuthService:
    """Tests for AuthService."""
    
    def test_register_new_user(self, session):
        """Test registering a new user."""
        auth = AuthService(session)
        
        user, verification_token = auth.register(
            email="new@example.com",
            password="SecurePass123",
            name="New User",
        )
        session.commit()
        
        assert user.id is not None
        assert user.email == "new@example.com"
        assert user.name == "New User"
        assert user.email_verified is False
        assert verification_token is not None
    
    def test_register_duplicate_email(self, session, sample_user):
        """Test registering with existing email fails."""
        auth = AuthService(session)
        
        with pytest.raises(UserExistsError):
            auth.register(
                email=sample_user.email,
                password="SecurePass123",
            )
    
    def test_register_weak_password(self, session):
        """Test registering with weak password fails."""
        auth = AuthService(session)
        
        with pytest.raises(PasswordStrengthError):
            auth.register(
                email="new@example.com",
                password="weak",
            )
    
    def test_login_success(self, session, sample_user):
        """Test successful login."""
        auth = AuthService(session)
        
        user, tokens = auth.login(
            email=sample_user.email,
            password="TestPass123",
        )
        
        assert user.id == sample_user.id
        assert tokens.access_token is not None
        assert tokens.refresh_token is not None
    
    def test_login_wrong_password(self, session, sample_user):
        """Test login with wrong password."""
        auth = AuthService(session)
        
        with pytest.raises(InvalidCredentialsError):
            auth.login(
                email=sample_user.email,
                password="WrongPass123",
            )
    
    def test_login_nonexistent_user(self, session):
        """Test login with non-existent email."""
        auth = AuthService(session)
        
        with pytest.raises(InvalidCredentialsError):
            auth.login(
                email="nonexistent@example.com",
                password="TestPass123",
            )
    
    def test_refresh_tokens(self, session, sample_user):
        """Test token refresh."""
        auth = AuthService(session)
        
        # First login to get tokens
        _, initial_tokens = auth.login(sample_user.email, "TestPass123")
        
        # Refresh tokens
        new_tokens = auth.refresh_tokens(initial_tokens.refresh_token)
        
        assert new_tokens.access_token is not None
        assert new_tokens.refresh_token is not None
        # Verify new access token is valid
        payload = verify_token(new_tokens.access_token, TokenType.ACCESS)
        assert payload["sub"] == sample_user.id

    def test_verify_email(self, session):
        """Test email verification."""
        auth = AuthService(session)
        
        # Register user
        user, verification_token = auth.register(
            email="verify@example.com",
            password="SecurePass123",
        )
        session.commit()
        
        assert user.email_verified is False
        
        # Verify email
        verified_user = auth.verify_email(verification_token)
        session.commit()
        
        assert verified_user.email_verified is True
    
    def test_request_password_reset(self, session, sample_user):
        """Test password reset request."""
        auth = AuthService(session)
        
        reset_token = auth.request_password_reset(sample_user.email)
        session.commit()
        
        assert reset_token is not None
        
        # Check user has reset token stored
        session.refresh(sample_user)
        assert sample_user.reset_token == reset_token
    
    def test_request_password_reset_nonexistent(self, session):
        """Test password reset for non-existent email."""
        auth = AuthService(session)
        
        # Should not raise, just return None
        reset_token = auth.request_password_reset("nonexistent@example.com")
        
        assert reset_token is None
    
    def test_reset_password(self, session, sample_user):
        """Test password reset."""
        auth = AuthService(session)
        
        # Request reset
        reset_token = auth.request_password_reset(sample_user.email)
        session.commit()
        
        # Reset password
        auth.reset_password(reset_token, "NewSecurePass123")
        session.commit()
        
        # Login with new password should work
        user, tokens = auth.login(sample_user.email, "NewSecurePass123")
        assert user.id == sample_user.id
    
    def test_change_password(self, session, sample_user):
        """Test password change."""
        auth = AuthService(session)
        
        auth.change_password(
            user_id=sample_user.id,
            current_password="TestPass123",
            new_password="NewSecurePass123",
        )
        session.commit()
        
        # Login with new password
        user, tokens = auth.login(sample_user.email, "NewSecurePass123")
        assert user.id == sample_user.id
    
    def test_change_password_wrong_current(self, session, sample_user):
        """Test password change with wrong current password."""
        auth = AuthService(session)
        
        with pytest.raises(InvalidCredentialsError):
            auth.change_password(
                user_id=sample_user.id,
                current_password="WrongPass123",
                new_password="NewSecurePass123",
            )
    
    def test_get_user_by_token(self, session, sample_user):
        """Test getting user from access token."""
        auth = AuthService(session)
        
        # Login to get token
        _, tokens = auth.login(sample_user.email, "TestPass123")
        
        # Get user from token
        user = auth.get_user_by_token(tokens.access_token)
        
        assert user.id == sample_user.id


# =============================================================================
# MIDDLEWARE TESTS
# =============================================================================

class TestMiddleware:
    """Tests for authentication middleware."""
    
    def test_extract_token_from_header(self):
        """Test extracting token from Authorization header."""
        token = "some.jwt.token"
        header = f"Bearer {token}"
        
        extracted = extract_token_from_header(header)
        
        assert extracted == token
    
    def test_extract_token_no_header(self):
        """Test extracting from missing header."""
        extracted = extract_token_from_header(None)
        
        assert extracted is None
    
    def test_extract_token_wrong_scheme(self):
        """Test extracting with wrong auth scheme."""
        extracted = extract_token_from_header("Basic abc123")
        
        assert extracted is None
    
    def test_get_current_user_id(self, sample_user):
        """Test getting user ID from header."""
        token = create_access_token(sample_user.id, sample_user.email)
        header = f"Bearer {token}"
        
        user_id = get_current_user_id(header)
        
        assert user_id == sample_user.id
    
    def test_get_current_user_id_missing_token(self):
        """Test error when token is missing."""
        with pytest.raises(AuthenticationError) as exc_info:
            get_current_user_id(None)
        
        assert "Missing" in str(exc_info.value)
    
    def test_get_current_user_id_expired_token(self, sample_user):
        """Test error for expired token."""
        token = create_access_token(
            sample_user.id,
            sample_user.email,
            expires_delta=timedelta(seconds=-1),
        )
        header = f"Bearer {token}"
        
        with pytest.raises(AuthenticationError) as exc_info:
            get_current_user_id(header)
        
        assert "expired" in str(exc_info.value).lower()
    
    def test_jwt_middleware_excluded_paths(self):
        """Test middleware path exclusion."""
        middleware = JWTMiddleware()
        
        assert middleware.is_excluded("/api/auth/login") is True
        assert middleware.is_excluded("/api/auth/register") is True
        assert middleware.is_excluded("/api/projects") is False
    
    def test_jwt_middleware_authenticate(self, sample_user):
        """Test middleware authentication."""
        middleware = JWTMiddleware()
        token = create_access_token(
            sample_user.id,
            sample_user.email,
            additional_claims={"tier": "free", "verified": False},
        )
        header = f"Bearer {token}"
        
        user_info = middleware.authenticate(header)
        
        assert user_info["user_id"] == sample_user.id
        assert user_info["email"] == sample_user.email


# =============================================================================
# SCHEMA VALIDATION TESTS
# =============================================================================

class TestSchemas:
    """Tests for request/response schemas."""
    
    def test_register_request_valid(self):
        """Test valid registration request."""
        request = RegisterRequest(
            email="test@example.com",
            password="SecurePass123",
            name="Test User",
        )
        
        assert request.email == "test@example.com"
    
    def test_register_request_weak_password(self):
        """Test registration with weak password fails validation."""
        with pytest.raises(ValueError):
            RegisterRequest(
                email="test@example.com",
                password="weak",
            )
    
    def test_login_request_valid(self):
        """Test valid login request."""
        request = LoginRequest(
            email="test@example.com",
            password="anypassword",
        )
        
        assert request.remember_me is False
    
    def test_reset_password_request_valid(self):
        """Test valid password reset request."""
        request = ResetPasswordRequest(
            token="sometoken",
            new_password="SecurePass123",
        )
        
        assert request.token == "sometoken"
    
    def test_reset_password_request_weak(self):
        """Test password reset with weak password fails."""
        with pytest.raises(ValueError):
            ResetPasswordRequest(
                token="sometoken",
                new_password="weak",
            )


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestAuthIntegration:
    """Integration tests for complete auth flows."""
    
    def test_full_registration_to_login_flow(self, session):
        """Test complete registration to login flow."""
        auth = AuthService(session)
        
        # 1. Register
        user, verification_token = auth.register(
            email="newuser@example.com",
            password="SecurePass123",
            name="New User",
        )
        session.commit()
        
        assert user.email_verified is False
        
        # 2. Verify email
        auth.verify_email(verification_token)
        session.commit()
        
        session.refresh(user)
        assert user.email_verified is True
        
        # 3. Login
        logged_in_user, tokens = auth.login(
            email="newuser@example.com",
            password="SecurePass123",
        )
        session.commit()
        
        assert logged_in_user.id == user.id
        assert tokens.access_token is not None
        
        # 4. Access protected resource (verify token)
        payload = verify_token(tokens.access_token, TokenType.ACCESS)
        assert payload["sub"] == user.id
        
        # 5. Refresh token
        new_tokens = auth.refresh_tokens(tokens.refresh_token)
        # Verify new token is valid and belongs to same user
        new_payload = verify_token(new_tokens.access_token, TokenType.ACCESS)
        assert new_payload["sub"] == user.id
        assert new_tokens.refresh_token is not None
    
    def test_password_reset_flow(self, session, sample_user):
        """Test complete password reset flow."""
        auth = AuthService(session)
        original_email = sample_user.email
        
        # 1. Request reset
        reset_token = auth.request_password_reset(original_email)
        session.commit()
        
        assert reset_token is not None
        
        # 2. Reset password
        auth.reset_password(reset_token, "NewSecurePass456")
        session.commit()
        
        # 3. Old password should not work
        with pytest.raises(InvalidCredentialsError):
            auth.login(original_email, "TestPass123")
        
        # 4. New password should work
        user, tokens = auth.login(original_email, "NewSecurePass456")
        assert user.email == original_email


# =============================================================================
# RUN TESTS
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
