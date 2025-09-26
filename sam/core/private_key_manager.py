"""
Private Key Manager for Frontend-Requested Keys
Handles secure storage and retrieval of private keys requested from chat interface.
"""

import asyncio
import base64
import logging
from typing import Optional, Dict, Any
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from sam.utils.secure_storage import SecureStorage
from sam.utils.crypto import generate_encryption_key
from sam.utils.validators import validate_solana_private_key
from sam.utils.error_handling import handle_errors
from sam.utils.error_messages import handle_error_gracefully

logger = logging.getLogger(__name__)


class PrivateKeyManager:
    """Manages private keys requested from frontend chat interface."""
    
    def __init__(self, secure_storage: SecureStorage):
        self.secure_storage = secure_storage
        self._session_keys: Dict[str, str] = {}  # session_id -> encrypted_key
        
    @handle_errors("private_key_manager")
    async def request_private_key(self, session_id: str, private_key: str) -> Dict[str, Any]:
        """
        Request and store a private key from frontend chat.
        
        Args:
            session_id: Unique session identifier
            private_key: Base58 encoded private key from user
            
        Returns:
            Success status and any error messages
        """
        try:
            # Validate the private key format
            if not validate_solana_private_key(private_key):
                return {
                    "success": False,
                    "error": "Invalid Solana private key format",
                    "error_detail": {"code": "validation_failed", "message": "Invalid Solana private key format"}
                }
            
            # Generate a session-specific encryption key
            session_key = self._generate_session_key(session_id)
            
            # Encrypt the private key
            encrypted_key = self._encrypt_private_key(private_key, session_key)
            
            # Store in session cache
            self._session_keys[session_id] = encrypted_key
            
            # Also store in secure storage for persistence
            # Use the session_id as the user_id for secure storage
            success = self.secure_storage.store_private_key(session_id, private_key)
            if not success:
                return {
                    "success": False,
                    "error": "Failed to store private key in secure storage",
                    "error_detail": {"code": "storage_error", "message": "Secure storage failed"}
                }
            
            return {
                "success": True,
                "message": "Private key stored securely",
                "session_id": session_id
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": "Failed to store private key",
                "error_detail": {"code": "storage_error", "message": str(e)}
            }
    
    @handle_errors("private_key_manager")
    async def get_private_key(self, session_id: str) -> Optional[str]:
        """
        Retrieve and decrypt private key for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Decrypted private key or None if not found
        """
        try:
            # Check session cache first
            if session_id in self._session_keys:
                encrypted_key = self._session_keys[session_id]
                # Decrypt the private key
                session_key = self._generate_session_key(session_id)
                private_key = self._decrypt_private_key(encrypted_key, session_key)
                return private_key
            else:
                # Try to load from secure storage
                private_key = self.secure_storage.get_private_key(session_id)
                if private_key:
                    # Store in session cache for future use
                    session_key = self._generate_session_key(session_id)
                    encrypted_key = self._encrypt_private_key(private_key, session_key)
                    self._session_keys[session_id] = encrypted_key
                return private_key
            
        except Exception as e:
            logger.error(f"Error retrieving private key for session {session_id}: {e}")
            return None
    
    @handle_errors("private_key_manager")
    async def clear_session_key(self, session_id: str) -> Dict[str, Any]:
        """
        Clear private key for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Success status
        """
        try:
            # Remove from session cache
            if session_id in self._session_keys:
                del self._session_keys[session_id]
            
            # Remove from secure storage
            self.secure_storage.delete_private_key(session_id)
            
            return {
                "success": True,
                "message": f"Private key cleared for session {session_id}"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": "Failed to clear private key",
                "error_detail": {"code": "clear_error", "message": str(e)}
            }
    
    def _generate_session_key(self, session_id: str) -> bytes:
        """Generate a session-specific encryption key."""
        # Use session ID as salt for deterministic key generation
        salt = session_id.encode('utf-8')
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(b"sam_framework_session_key"))
        return key
    
    def _encrypt_private_key(self, private_key: str, session_key: bytes) -> str:
        """Encrypt private key with session-specific key."""
        fernet = Fernet(session_key)
        encrypted = fernet.encrypt(private_key.encode('utf-8'))
        return base64.urlsafe_b64encode(encrypted).decode('utf-8')
    
    def _decrypt_private_key(self, encrypted_key: str, session_key: bytes) -> str:
        """Decrypt private key with session-specific key."""
        fernet = Fernet(session_key)
        encrypted_bytes = base64.urlsafe_b64decode(encrypted_key.encode('utf-8'))
        decrypted = fernet.decrypt(encrypted_bytes)
        return decrypted.decode('utf-8')
    
    async def has_private_key(self, session_id: str) -> bool:
        """Check if session has a stored private key."""
        return await self.get_private_key(session_id) is not None
