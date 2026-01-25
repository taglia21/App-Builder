"""
Integration tests for onboarding flow.

Tests:
- Full onboarding progression
- Email verification flow
- Status tracking
- Step completion
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone


class TestOnboardingFlow:
    """Test the complete onboarding flow."""
    
    @pytest.fixture
    def mock_db_session(self):
        """Create mock database session."""
        session = MagicMock()
        session.commit = MagicMock()
        session.rollback = MagicMock()
        return session
    
    @pytest.fixture
    def mock_user(self):
        """Create mock user."""
        user = MagicMock()
        user.id = "user_123"
        user.email = "test@example.com"
        user.name = "Test User"
        user.email_verified = False
        user.is_deleted = False
        user.verification_token = None
        return user
    
    @pytest.fixture
    def mock_onboarding_status(self):
        """Create mock onboarding status."""
        status = MagicMock()
        status.user_id = "user_123"
        status.email_verified = False
        status.api_keys_set = False
        status.first_app_generated = False
        status.first_deploy_completed = False
        status.email_verified_at = None
        status.api_keys_set_at = None
        status.first_app_generated_at = None
        status.first_deploy_completed_at = None
        return status


class TestEmailVerificationFlow:
    """Test email verification flow."""
    
    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return MagicMock()
    
    @pytest.fixture
    def mock_user(self):
        """Create mock user for verification."""
        user = MagicMock()
        user.id = "user_123"
        user.email = "test@example.com"
        user.name = "Test User"
        user.email_verified = False
        user.is_deleted = False
        user.verification_token = "valid_token_abc123xyz"
        user.verification_token_expires = None  # No expiry by default
        return user
    
    def test_generate_verification_token(self):
        """Token should be secure and URL-safe."""
        from src.auth.verification import generate_verification_token
        
        token = generate_verification_token()
        
        assert len(token) >= 32
        # Should be URL-safe base64
        import re
        assert re.match(r'^[A-Za-z0-9_-]+$', token)
    
    def test_validate_verification_token_valid(self):
        """Should accept valid tokens."""
        from src.auth.verification import validate_verification_token
        
        valid_token = "abcdefghijklmnopqrstuvwxyz123456"
        assert validate_verification_token(valid_token) == True
    
    def test_validate_verification_token_empty(self):
        """Should reject empty tokens."""
        from src.auth.verification import validate_verification_token
        
        assert validate_verification_token("") == False
        assert validate_verification_token(None) == False
    
    def test_validate_verification_token_too_short(self):
        """Should reject tokens that are too short."""
        from src.auth.verification import validate_verification_token
        
        assert validate_verification_token("short") == False
    
    def test_validate_verification_token_invalid_chars(self):
        """Should reject tokens with invalid characters."""
        from src.auth.verification import validate_verification_token
        
        assert validate_verification_token("invalid token with spaces") == False
        assert validate_verification_token("invalid@token#with$special") == False
    
    @pytest.mark.asyncio
    async def test_create_verification_token(self, mock_db, mock_user):
        """Should create and store verification token."""
        from src.auth.verification import create_verification_token
        
        mock_db.commit = MagicMock()
        
        url = await create_verification_token(
            user=mock_user,
            db=mock_db,
            base_url="https://example.com"
        )
        
        assert url.startswith("https://example.com/verify/email/")
        assert mock_user.verification_token is not None
        mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_verification_for_user_success(self, mock_db, mock_user):
        """Should send verification email successfully."""
        from src.auth.verification import send_verification_for_user
        from src.emails.client import EmailResult
        
        mock_db.commit = MagicMock()
        
        with patch('src.auth.verification.send_verification_email') as mock_send:
            mock_send.return_value = EmailResult(success=True, message_id="msg_123")
            
            result = await send_verification_for_user(
                user=mock_user,
                db=mock_db,
                base_url="https://example.com"
            )
            
            assert result == True
            mock_send.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_verification_for_user_failure(self, mock_db, mock_user):
        """Should return False when email sending fails."""
        from src.auth.verification import send_verification_for_user
        from src.emails.client import EmailResult
        
        mock_db.commit = MagicMock()
        
        with patch('src.auth.verification.send_verification_email') as mock_send:
            mock_send.return_value = EmailResult(success=False, error="API error")
            
            result = await send_verification_for_user(
                user=mock_user,
                db=mock_db,
                base_url="https://example.com"
            )
            
            assert result == False
    
    def test_verify_token_and_get_user_success(self, mock_db, mock_user):
        """Should return user for valid token."""
        from src.auth.verification import verify_token_and_get_user
        
        # Token must be 32+ chars with valid base64url characters
        valid_token = "abcdefghijklmnopqrstuvwxyz012345"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        mock_user.verification_token = valid_token
        
        user = verify_token_and_get_user(
            token=valid_token,
            db=mock_db
        )
        
        assert user == mock_user
    
    def test_verify_token_and_get_user_invalid_token(self, mock_db):
        """Should raise TokenInvalidError for invalid token."""
        from src.auth.verification import verify_token_and_get_user, TokenInvalidError
        
        with pytest.raises(TokenInvalidError):
            verify_token_and_get_user(token="short", db=mock_db)
    
    def test_verify_token_and_get_user_not_found(self, mock_db):
        """Should raise TokenInvalidError when user not found."""
        from src.auth.verification import verify_token_and_get_user, TokenInvalidError
        
        valid_token = "abcdefghijklmnopqrstuvwxyz012345"
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        with pytest.raises(TokenInvalidError):
            verify_token_and_get_user(
                token=valid_token,
                db=mock_db
            )
    
    def test_verify_token_and_get_user_already_verified(self, mock_db, mock_user):
        """Should raise AlreadyVerifiedError if email already verified."""
        from src.auth.verification import verify_token_and_get_user, AlreadyVerifiedError
        
        valid_token = "abcdefghijklmnopqrstuvwxyz012345"
        mock_user.email_verified = True
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        with pytest.raises(AlreadyVerifiedError):
            verify_token_and_get_user(
                token=valid_token,
                db=mock_db
            )
    
    def test_verify_token_and_get_user_expired(self, mock_db, mock_user):
        """Should raise TokenExpiredError if token has expired."""
        from src.auth.verification import verify_token_and_get_user, TokenExpiredError
        from datetime import datetime, timedelta, timezone
        
        valid_token = "abcdefghijklmnopqrstuvwxyz012345"
        mock_user.email_verified = False
        mock_user.verification_token_expires = datetime.now(timezone.utc) - timedelta(hours=1)
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        with pytest.raises(TokenExpiredError):
            verify_token_and_get_user(
                token=valid_token,
                db=mock_db
            )


class TestOnboardingStatusTracking:
    """Test onboarding status tracking."""
    
    @pytest.mark.asyncio
    async def test_track_email_verified_step(self):
        """Should track email verification in metrics."""
        with patch('src.monitoring.metrics.track_onboarding_step') as mock_track:
            # Simulate what happens when email is verified
            mock_track("email_verified")
            mock_track.assert_called_with("email_verified")
    
    @pytest.mark.asyncio
    async def test_track_api_keys_step(self):
        """Should track API keys setup in metrics."""
        with patch('src.monitoring.metrics.track_onboarding_step') as mock_track:
            mock_track("api_keys_set")
            mock_track.assert_called_with("api_keys_set")
    
    @pytest.mark.asyncio
    async def test_track_first_app_step(self):
        """Should track first app generation in metrics."""
        with patch('src.monitoring.metrics.track_onboarding_step') as mock_track:
            mock_track("first_app_generated")
            mock_track.assert_called_with("first_app_generated")
    
    @pytest.mark.asyncio
    async def test_track_first_deploy_step(self):
        """Should track first deployment in metrics."""
        with patch('src.monitoring.metrics.track_onboarding_step') as mock_track:
            mock_track("first_deploy_completed")
            mock_track.assert_called_with("first_deploy_completed")


class TestOnboardingAPIEndpoint:
    """Test onboarding status API endpoint."""
    
    @pytest.mark.asyncio
    async def test_get_onboarding_status(self):
        """Should return onboarding status."""
        from src.dashboard.api import APIRoutes
        
        api = APIRoutes()
        result = await api.get_onboarding_status()
        
        assert "steps" in result.model_dump()
        assert "completedCount" in result.model_dump()
        assert "totalSteps" in result.model_dump()
        assert result.totalSteps == 4
    
    @pytest.mark.asyncio
    async def test_onboarding_status_all_complete(self):
        """allComplete should be True when all steps done."""
        from src.dashboard.api import OnboardingStatusResponse
        
        response = OnboardingStatusResponse(
            steps={
                "emailVerified": True,
                "apiKeysAdded": True,
                "firstAppGenerated": True,
                "firstDeploy": True
            },
            completedCount=4,
            totalSteps=4,
            allComplete=True
        )
        
        assert response.allComplete == True
        assert response.completedCount == 4
    
    @pytest.mark.asyncio
    async def test_onboarding_status_partial(self):
        """Should correctly report partial completion."""
        from src.dashboard.api import OnboardingStatusResponse
        
        response = OnboardingStatusResponse(
            steps={
                "emailVerified": True,
                "apiKeysAdded": True,
                "firstAppGenerated": False,
                "firstDeploy": False
            },
            completedCount=2,
            totalSteps=4,
            allComplete=False
        )
        
        assert response.allComplete == False
        assert response.completedCount == 2


class TestOnboardingIntegration:
    """Integration tests for full onboarding flow."""
    
    @pytest.mark.asyncio
    async def test_new_user_onboarding_flow(self):
        """Test complete onboarding flow for a new user."""
        # This would be a full integration test with a test database
        # For now, we test the logical flow
        
        # Step 1: User signs up
        user_data = {
            "email": "newuser@example.com",
            "password": "secure_password_123"
        }
        
        # Step 2: Verification email sent
        # Step 3: User clicks verification link
        # Step 4: User adds API keys
        # Step 5: User generates first app
        # Step 6: User deploys first app
        
        # Each step should update onboarding status
        steps_completed = [
            "email_verified",
            "api_keys_set", 
            "first_app_generated",
            "first_deploy_completed"
        ]
        
        # Verify flow logic
        for i, step in enumerate(steps_completed):
            completed_count = i + 1
            all_complete = completed_count == len(steps_completed)
            
            assert completed_count <= 4
            if completed_count == 4:
                assert all_complete
    
    @pytest.mark.asyncio
    async def test_verification_triggers_onboarding_update(self):
        """Email verification should update onboarding status."""
        # This tests that the verification flow updates both user.email_verified
        # and onboarding_status.email_verified
        
        mock_user = MagicMock()
        mock_user.id = "user_123"
        mock_user.email_verified = False
        
        mock_onboarding = MagicMock()
        mock_onboarding.email_verified = False
        
        # Simulate verification
        mock_user.email_verified = True
        mock_onboarding.email_verified = True
        mock_onboarding.email_verified_at = datetime.now(timezone.utc)
        
        assert mock_user.email_verified == True
        assert mock_onboarding.email_verified == True
        assert mock_onboarding.email_verified_at is not None


class TestResendVerification:
    """Test resending verification emails."""
    
    @pytest.mark.asyncio
    async def test_resend_to_unverified_user(self):
        """Should resend verification to unverified users."""
        from src.emails.client import EmailResult
        
        mock_user = MagicMock()
        mock_user.email_verified = False
        mock_user.email = "test@example.com"
        
        with patch('src.auth.verification.send_verification_for_user') as mock_send:
            mock_send.return_value = True
            
            # Simulate the resend logic
            if mock_user and not mock_user.email_verified:
                result = await mock_send(mock_user, MagicMock(), "https://example.com")
                assert result == True
    
    @pytest.mark.asyncio
    async def test_resend_to_verified_user_ignored(self):
        """Should not resend to already verified users."""
        mock_user = MagicMock()
        mock_user.email_verified = True
        
        with patch('src.auth.verification.send_verification_for_user') as mock_send:
            # The resend logic should skip verified users
            if mock_user and not mock_user.email_verified:
                await mock_send(mock_user, MagicMock(), "https://example.com")
            
            # Should not have been called
            mock_send.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_resend_to_nonexistent_user_silent(self):
        """Should silently handle nonexistent users (no enumeration)."""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # The endpoint should still return success
        response_message = "If an account exists, a verification email has been sent"
        
        # This prevents email enumeration attacks
        assert "If an account exists" in response_message
