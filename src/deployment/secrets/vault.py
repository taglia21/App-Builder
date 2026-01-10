
import logging
import json
import os
from pathlib import Path
from typing import Dict, Optional
from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)

class SecretsVault:
    """
    Securely stores secrets locally using Fernet encryption.
    Useful for persisting secrets between sessions without committing them to git.
    """
    
    def __init__(self, vault_path: str = ".secrets_vault", key_path: str = ".vault_key"):
        self.vault_path = Path(vault_path)
        self.key_path = Path(key_path)
        self._key = self._load_or_create_key()
        self._cipher = Fernet(self._key)

    def _load_or_create_key(self) -> bytes:
        if self.key_path.exists():
            return self.key_path.read_bytes()
        else:
            key = Fernet.generate_key()
            # In a real app, ensure this file is gitignored
            self.key_path.write_bytes(key)
            return key

    def store_encrypted(self, secrets: Dict[str, str]) -> None:
        """Encrypt and save secrets to disk."""
        data = json.dumps(secrets).encode('utf-8')
        encrypted_data = self._cipher.encrypt(data)
        self.vault_path.write_bytes(encrypted_data)
        logger.info(f"Encrypted secrets stored in {self.vault_path}")

    def retrieve_decrypted(self) -> Dict[str, str]:
        """Load and decrypt secrets from disk."""
        if not self.vault_path.exists():
            return {}
        
        try:
            encrypted_data = self.vault_path.read_bytes()
            if not encrypted_data:
                return {}
            
            data = self._cipher.decrypt(encrypted_data)
            return json.loads(data.decode('utf-8'))
        except Exception as e:
            logger.error(f"Failed to decrypt vault: {e}")
            return {}
