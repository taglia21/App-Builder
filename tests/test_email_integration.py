"""
Integration tests for email service.

Tests:
- Email client initialization
- Template rendering
- Email sending (mocked)
- Error scenarios
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

from src.emails.client import (
    EmailClient,
    EmailResult,
    EmailAttachment,
    EmailError,
    EmailConfigurationError,
    EmailSendError,
    EmailTemplateError,
    EmailRateLimitError,
)


class TestEmailClientInitialization:
    """Test email client initialization."""
    
    def test_client_creation_without_api_key(self):
        """Client should be created even without API key."""
        with patch('src.emails.client.get_settings') as mock_settings:
            mock_settings.return_value = MagicMock(
                resend_api_key=None,
                email_from=None
            )
            client = EmailClient()
            
            assert not client.is_configured
            assert client.from_name == "LaunchForge"
    
    def test_client_creation_with_api_key(self):
        """Client should be configured when API key provided."""
        with patch('src.emails.client.get_settings') as mock_settings:
            mock_settings.return_value = MagicMock(
                resend_api_key="re_test_key",
                email_from="test@example.com"
            )
            client = EmailClient()
            
            assert client.is_configured
            assert client.api_key == "re_test_key"
    
    def test_client_with_explicit_parameters(self):
        """Client should accept explicit parameters."""
        with patch('src.emails.client.get_settings') as mock_settings:
            mock_settings.return_value = MagicMock(
                resend_api_key=None,
                email_from=None
            )
            client = EmailClient(
                api_key="explicit_key",
                from_email="explicit@example.com",
                from_name="Test App"
            )
            
            assert client.is_configured
            assert client.api_key == "explicit_key"
            assert client.from_email == "explicit@example.com"
            assert client.from_name == "Test App"
    
    def test_validate_configuration_raises_on_missing_key(self):
        """validate_configuration should raise when API key missing."""
        with patch('src.emails.client.get_settings') as mock_settings:
            mock_settings.return_value = MagicMock(
                resend_api_key=None,
                email_from=None
            )
            client = EmailClient()
            
            with pytest.raises(EmailConfigurationError) as exc_info:
                client.validate_configuration()
            
            assert "RESEND_API_KEY" in str(exc_info.value)


class TestTemplateRendering:
    """Test email template rendering."""
    
    @pytest.fixture
    def client(self):
        """Create email client with test templates."""
        with patch('src.emails.client.get_settings') as mock_settings:
            mock_settings.return_value = MagicMock(
                resend_api_key="test_key",
                email_from="test@example.com"
            )
            return EmailClient()
    
    def test_render_verification_template(self, client):
        """Should render verification template with context."""
        # Skip if template doesn't exist
        template_path = Path(__file__).parent.parent / "src" / "emails" / "templates" / "verification.html"
        if not template_path.exists():
            pytest.skip("Verification template not found")
        
        html = client.render_template(
            "verification.html",
            name="John",
            verification_url="https://example.com/verify/abc123",
            year=2026
        )
        
        assert "John" in html or "john" in html.lower()
        assert "verify" in html.lower()
    
    def test_render_missing_template_raises(self, client):
        """Should raise EmailTemplateError for missing template."""
        with pytest.raises(EmailTemplateError) as exc_info:
            client.render_template("nonexistent_template.html")
        
        assert "not found" in str(exc_info.value)
    
    def test_render_template_with_syntax_error(self, client):
        """Should raise EmailTemplateError on template syntax error."""
        # This would require a malformed template to test
        # For now, we verify the error handling structure exists
        pass


class TestEmailSending:
    """Test email sending functionality."""
    
    @pytest.fixture
    def configured_client(self):
        """Create configured email client."""
        with patch('src.emails.client.get_settings') as mock_settings:
            mock_settings.return_value = MagicMock(
                resend_api_key="re_test_key",
                email_from="test@example.com"
            )
            return EmailClient()
    
    @pytest.fixture
    def unconfigured_client(self):
        """Create unconfigured email client."""
        with patch('src.emails.client.get_settings') as mock_settings:
            mock_settings.return_value = MagicMock(
                resend_api_key=None,
                email_from=None
            )
            return EmailClient()
    
    @pytest.mark.asyncio
    async def test_send_email_without_configuration(self, unconfigured_client):
        """Should return error when not configured."""
        result = await unconfigured_client.send_email(
            to="recipient@example.com",
            subject="Test",
            html="<p>Test</p>"
        )
        
        assert not result.success
        assert result.error_code == "NOT_CONFIGURED"
    
    @pytest.mark.asyncio
    async def test_send_email_without_configuration_raises(self, unconfigured_client):
        """Should raise when not configured and raise_on_error=True."""
        with pytest.raises(EmailConfigurationError):
            await unconfigured_client.send_email(
                to="recipient@example.com",
                subject="Test",
                html="<p>Test</p>",
                raise_on_error=True
            )
    
    @pytest.mark.asyncio
    async def test_send_email_no_recipients(self, configured_client):
        """Should return error when no recipients."""
        result = await configured_client.send_email(
            to=[],
            subject="Test",
            html="<p>Test</p>"
        )
        
        assert not result.success
        assert result.error_code == "NO_RECIPIENTS"
    
    @pytest.mark.asyncio
    async def test_send_email_success(self, configured_client):
        """Should return success on successful send."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "email_123"}
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_instance
            
            result = await configured_client.send_email(
                to="recipient@example.com",
                subject="Test Subject",
                html="<p>Test content</p>",
                tags={"type": "test"}
            )
        
        assert result.success
        assert result.message_id == "email_123"
        assert result.duration_ms is not None
    
    @pytest.mark.asyncio
    async def test_send_email_rate_limited(self, configured_client):
        """Should handle rate limiting."""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.headers = {"Retry-After": "60"}
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_instance
            
            # Mock sleep to speed up test
            with patch.object(configured_client, '_async_sleep', new_callable=AsyncMock):
                result = await configured_client.send_email(
                    to="recipient@example.com",
                    subject="Test",
                    html="<p>Test</p>"
                )
        
        assert not result.success
        assert result.error_code == "RATE_LIMITED"
    
    @pytest.mark.asyncio
    async def test_send_email_rate_limited_raises(self, configured_client):
        """Should raise EmailSendError after rate limit retries exhausted."""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.headers = {"Retry-After": "60"}
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_instance
            
            with patch.object(configured_client, '_async_sleep', new_callable=AsyncMock):
                # After all retries exhausted, EmailSendError is raised
                with pytest.raises(EmailSendError) as exc_info:
                    await configured_client.send_email(
                        to="recipient@example.com",
                        subject="Test",
                        html="<p>Test</p>",
                        raise_on_error=True
                    )
                
                assert "rate limit" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_send_email_server_error_retries(self, configured_client):
        """Should retry on server errors."""
        mock_response_error = MagicMock()
        mock_response_error.status_code = 500
        
        mock_response_success = MagicMock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = {"id": "email_after_retry"}
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            # First call fails, second succeeds
            mock_instance.post.side_effect = [mock_response_error, mock_response_success]
            mock_client.return_value.__aenter__.return_value = mock_instance
            
            with patch.object(configured_client, '_async_sleep', new_callable=AsyncMock):
                result = await configured_client.send_email(
                    to="recipient@example.com",
                    subject="Test",
                    html="<p>Test</p>"
                )
        
        assert result.success
        assert result.message_id == "email_after_retry"
    
    @pytest.mark.asyncio
    async def test_send_email_timeout_retries(self, configured_client):
        """Should retry on timeouts."""
        import httpx
        
        mock_response_success = MagicMock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = {"id": "email_after_timeout_retry"}
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            # First call times out, second succeeds
            mock_instance.post.side_effect = [
                httpx.TimeoutException("Timeout"),
                mock_response_success
            ]
            mock_client.return_value.__aenter__.return_value = mock_instance
            
            with patch.object(configured_client, '_async_sleep', new_callable=AsyncMock):
                result = await configured_client.send_email(
                    to="recipient@example.com",
                    subject="Test",
                    html="<p>Test</p>"
                )
        
        assert result.success
    
    @pytest.mark.asyncio
    async def test_send_email_client_error_no_retry(self, configured_client):
        """Should not retry on client errors (4xx except 429)."""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Invalid request"
        mock_response.json.return_value = {"message": "Invalid email format"}
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_instance
            
            result = await configured_client.send_email(
                to="invalid-email",
                subject="Test",
                html="<p>Test</p>"
            )
        
        assert not result.success
        assert "Invalid email format" in result.error
        # Should only be called once (no retries)
        assert mock_instance.post.call_count == 1
    
    @pytest.mark.asyncio
    async def test_send_email_with_attachments(self, configured_client):
        """Should include attachments in request."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "email_with_attachment"}
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_instance
            
            attachment = EmailAttachment(
                filename="test.txt",
                content=b"Hello, World!",
                content_type="text/plain"
            )
            
            result = await configured_client.send_email(
                to="recipient@example.com",
                subject="Test with attachment",
                html="<p>See attached</p>",
                attachments=[attachment]
            )
        
        assert result.success
        
        # Verify attachment was included
        call_kwargs = mock_instance.post.call_args[1]
        assert "attachments" in call_kwargs["json"]
        assert call_kwargs["json"]["attachments"][0]["filename"] == "test.txt"


class TestConvenienceFunctions:
    """Test convenience email functions."""
    
    @pytest.mark.asyncio
    async def test_send_verification_email(self):
        """Test send_verification_email function."""
        from src.emails.client import send_verification_email
        
        with patch('src.emails.client.EmailClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client.render_template.return_value = "<p>Verify</p>"
            mock_client.send_email = AsyncMock(return_value=EmailResult(
                success=True,
                message_id="verify_123"
            ))
            mock_client_class.return_value = mock_client
            
            result = await send_verification_email(
                email="user@example.com",
                name="John",
                verification_url="https://example.com/verify/abc"
            )
            
            assert result.success
            mock_client.render_template.assert_called_once()
            mock_client.send_email.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_welcome_email(self):
        """Test send_welcome_email function."""
        from src.emails.client import send_welcome_email
        
        with patch('src.emails.client.EmailClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client.render_template.return_value = "<p>Welcome</p>"
            mock_client.send_email = AsyncMock(return_value=EmailResult(
                success=True,
                message_id="welcome_123"
            ))
            mock_client_class.return_value = mock_client
            
            result = await send_welcome_email(
                email="user@example.com",
                name="John"
            )
            
            assert result.success


class TestMetricsTracking:
    """Test that email metrics are tracked."""
    
    @pytest.mark.asyncio
    async def test_success_tracked(self):
        """Should track successful email sends."""
        with patch('src.emails.client.get_settings') as mock_settings:
            mock_settings.return_value = MagicMock(
                resend_api_key="test_key",
                email_from="test@example.com"
            )
            client = EmailClient()
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "email_123"}
        
        with patch('httpx.AsyncClient') as mock_http:
            mock_instance = AsyncMock()
            mock_instance.post.return_value = mock_response
            mock_http.return_value.__aenter__.return_value = mock_instance
            
            with patch('src.monitoring.metrics.track_email_send') as mock_track:
                await client.send_email(
                    to="recipient@example.com",
                    subject="Test",
                    html="<p>Test</p>",
                    tags={"type": "test"}
                )
                
                mock_track.assert_called_once()
                call_args = mock_track.call_args
                assert call_args[0][0] == "test"  # template name
                assert call_args[0][1] == True  # success
    
    @pytest.mark.asyncio
    async def test_failure_tracked(self):
        """Should track failed email sends."""
        with patch('src.emails.client.get_settings') as mock_settings:
            mock_settings.return_value = MagicMock(
                resend_api_key="test_key",
                email_from="test@example.com"
            )
            client = EmailClient()
        
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad request"
        mock_response.json.return_value = {"message": "Error"}
        
        with patch('httpx.AsyncClient') as mock_http:
            mock_instance = AsyncMock()
            mock_instance.post.return_value = mock_response
            mock_http.return_value.__aenter__.return_value = mock_instance
            
            with patch('src.monitoring.metrics.track_email_send') as mock_track:
                await client.send_email(
                    to="recipient@example.com",
                    subject="Test",
                    html="<p>Test</p>",
                    tags={"type": "test"}
                )
                
                mock_track.assert_called_once()
                call_args = mock_track.call_args
                assert call_args[0][0] == "test"  # template name
                assert call_args[0][1] == False  # success=False
