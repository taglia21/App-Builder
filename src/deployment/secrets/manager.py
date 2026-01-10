
import logging
from typing import Dict, Optional
import os
import re
import secrets
import base64

logger = logging.getLogger(__name__)

class SecretsManager:
    """
    Orchestrates secret key validation, generation, and provider synchronization.
    """

    def validate_secret(self, key: str, value: str) -> bool:
        """
        Basic format validation for common secret types.
        """
        if not value:
            return False
            
        if "API_KEY" in key.upper():
            return len(value) > 8
        
        if "DB_URL" in key.upper() or "DATABASE_URL" in key.upper():
            return value.startswith("postgres://") or value.startswith("postgresql://")
        
        return True

    def generate_jwt_secret(self, length: int = 64) -> str:
        """
        Generate a secure random JWT secret key.
        """
        return secrets.token_urlsafe(length)

    def generate_secure_password(self, length: int = 32) -> str:
        """
        Generate a secure random password.
        """
        alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*"
        return "".join(secrets.choice(alphabet) for i in range(length))
    
    def orchestrate_secrets(self, config_secrets: Dict[str, str]) -> Dict[str, str]:
        """
        Prepare secrets for deployment:
        1. Fill in missing generated secrets (like JWT_SECRET)
        2. Validate existing secrets
        """
        final_secrets = config_secrets.copy()
        
        # Auto-generate if missing
        if "JWT_SECRET" not in final_secrets:
            final_secrets["JWT_SECRET"] = self.generate_jwt_secret()
            logger.info("Generated new JWT_SECRET")
            
        if "SECRET_KEY" not in final_secrets:
            final_secrets["SECRET_KEY"] = self.generate_jwt_secret()
            logger.info("Generated new SECRET_KEY")

        # Validate
        for k, v in final_secrets.items():
            if not self.validate_secret(k, v):
                logger.warning(f"Secret '{k}' failed basic validation (length or format).")
        
        return final_secrets
