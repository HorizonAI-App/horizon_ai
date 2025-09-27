# 🔐 Horizon Security Architecture

## Overview

Horizon implements a comprehensive security architecture designed to protect user assets, private keys, and sensitive data while maintaining the flexibility needed for autonomous trading operations.

## Security Principles

### 1. Defense in Depth
- Multiple layers of security controls
- Fail-safe defaults
- Principle of least privilege
- Comprehensive monitoring and logging

### 2. Zero Trust Architecture
- Never trust, always verify
- Continuous authentication and authorization
- Encrypted data in transit and at rest
- Secure by default configurations

### 3. Privacy by Design
- Data minimization
- User consent and control
- Transparent data handling
- Right to deletion

## Core Security Components

### 1. Private Key Management

#### Fernet Encryption
```python
from cryptography.fernet import Fernet
import os

class SecureKeyManager:
    def __init__(self, fernet_key: str):
        self.fernet = Fernet(fernet_key.encode())
    
    def encrypt_private_key(self, private_key: str) -> bytes:
        """Encrypt private key for storage."""
        return self.fernet.encrypt(private_key.encode())
    
    def decrypt_private_key(self, encrypted_key: bytes) -> str:
        """Decrypt private key for use."""
        return self.fernet.decrypt(encrypted_key).decode()
    
    def generate_fernet_key(self) -> str:
        """Generate a new Fernet encryption key."""
        return Fernet.generate_key().decode()
```

#### OS Keyring Integration
```python
import keyring
from typing import Optional

class OSKeyringManager:
    def __init__(self, service_name: str = "horizon"):
        self.service_name = service_name
    
    def store_credential(self, username: str, credential: str) -> None:
        """Store credential in OS keyring."""
        keyring.set_password(self.service_name, username, credential)
    
    def get_credential(self, username: str) -> Optional[str]:
        """Retrieve credential from OS keyring."""
        return keyring.get_password(self.service_name, username)
    
    def delete_credential(self, username: str) -> None:
        """Delete credential from OS keyring."""
        keyring.delete_password(self.service_name, username)
```

#### Secure Storage Implementation
```python
class SecureStorage:
    def __init__(self, fernet_key: str):
        self.key_manager = SecureKeyManager(fernet_key)
        self.keyring = OSKeyringManager()
    
    async def store_wallet_key(self, user_id: str, private_key: str) -> None:
        """Store wallet private key securely."""
        # Encrypt the private key
        encrypted_key = self.key_manager.encrypt_private_key(private_key)
        
        # Store in OS keyring
        self.keyring.store_credential(f"wallet_{user_id}", encrypted_key.decode())
    
    async def get_wallet_key(self, user_id: str) -> Optional[str]:
        """Retrieve wallet private key securely."""
        encrypted_key_b64 = self.keyring.get_credential(f"wallet_{user_id}")
        if not encrypted_key_b64:
            return None
        
        try:
            encrypted_key = encrypted_key_b64.encode()
            return self.key_manager.decrypt_private_key(encrypted_key)
        except Exception as e:
            logger.error(f"Failed to decrypt wallet key for user {user_id}: {e}")
            return None
```

### 2. Input Validation and Sanitization

#### Pydantic Model Validation
```python
from pydantic import BaseModel, Field, validator
from typing import Optional
import re

class TransactionInput(BaseModel):
    to_address: str = Field(..., description="Recipient Solana address")
    amount: float = Field(..., gt=0, description="Amount in SOL")
    slippage: Optional[float] = Field(1.0, ge=0.1, le=50.0, description="Slippage percentage")
    
    @validator('to_address')
    def validate_solana_address(cls, v):
        """Validate Solana address format."""
        if not re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', v):
            raise ValueError('Invalid Solana address format')
        return v
    
    @validator('amount')
    def validate_amount(cls, v):
        """Validate transaction amount."""
        if v <= 0:
            raise ValueError('Amount must be positive')
        if v > 1000:  # Configurable limit
            raise ValueError('Amount exceeds maximum limit')
        return v

class TokenPurchaseInput(BaseModel):
    mint: str = Field(..., description="Token mint address")
    amount_sol: float = Field(..., gt=0, le=100, description="Amount in SOL")
    slippage_percent: float = Field(5.0, ge=1.0, le=50.0, description="Slippage percentage")
    
    @validator('mint')
    def validate_mint_address(cls, v):
        """Validate token mint address."""
        if not re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', v):
            raise ValueError('Invalid token mint address format')
        return v
```

#### SQL Injection Prevention
```python
import sqlite3
from typing import Any, Dict, List

class SecureDatabase:
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    async def execute_query(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """Execute parameterized query to prevent SQL injection."""
        async with aiosqlite.connect(self.db_path) as conn:
            cursor = await conn.execute(query, params)
            rows = await cursor.fetchall()
            columns = [description[0] for description in cursor.description]
            return [dict(zip(columns, row)) for row in rows]
    
    async def execute_update(self, query: str, params: tuple = ()) -> int:
        """Execute parameterized update query."""
        async with aiosqlite.connect(self.db_path) as conn:
            cursor = await conn.execute(query, params)
            await conn.commit()
            return cursor.rowcount
```

### 3. Rate Limiting and DDoS Protection

#### Token Bucket Rate Limiter
```python
import asyncio
import time
from typing import Dict, Optional

class TokenBucketRateLimiter:
    def __init__(self, capacity: int, refill_rate: float):
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = capacity
        self.last_refill = time.time()
        self._lock = asyncio.Lock()
    
    async def acquire(self, tokens: int = 1) -> bool:
        """Acquire tokens from the bucket."""
        async with self._lock:
            now = time.time()
            # Refill tokens based on time elapsed
            time_passed = now - self.last_refill
            self.tokens = min(self.capacity, self.tokens + time_passed * self.refill_rate)
            self.last_refill = now
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False

class RateLimiter:
    def __init__(self):
        self.limiters: Dict[str, TokenBucketRateLimiter] = {}
    
    def get_limiter(self, key: str, capacity: int = 100, refill_rate: float = 10.0) -> TokenBucketRateLimiter:
        """Get or create rate limiter for a key."""
        if key not in self.limiters:
            self.limiters[key] = TokenBucketRateLimiter(capacity, refill_rate)
        return self.limiters[key]
    
    async def check_rate_limit(self, key: str, tokens: int = 1) -> bool:
        """Check if request is within rate limits."""
        limiter = self.get_limiter(key)
        return await limiter.acquire(tokens)
```

#### API Rate Limiting
```python
from functools import wraps
from typing import Callable, Any

def rate_limit(calls_per_minute: int = 60, key_func: Optional[Callable] = None):
    """Decorator for rate limiting API calls."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            # Generate rate limit key
            if key_func:
                rate_key = key_func(*args, **kwargs)
            else:
                rate_key = f"{func.__name__}_global"
            
            # Check rate limit
            if not await rate_limiter.check_rate_limit(rate_key, calls_per_minute):
                raise RateLimitExceeded(f"Rate limit exceeded for {rate_key}")
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

# Usage example
@rate_limit(calls_per_minute=30, key_func=lambda self, user_id: f"user_{user_id}")
async def get_balance(self, user_id: str) -> Dict[str, Any]:
    """Get user balance with rate limiting."""
    # Implementation
    pass
```

### 4. Transaction Safety and Validation

#### Transaction Limits
```python
class TransactionValidator:
    def __init__(self, max_sol_per_transaction: float = 1000.0):
        self.max_sol_per_transaction = max_sol_per_transaction
    
    def validate_transaction(self, amount: float, transaction_type: str) -> bool:
        """Validate transaction parameters."""
        if amount <= 0:
            raise ValueError("Transaction amount must be positive")
        
        if amount > self.max_sol_per_transaction:
            raise ValueError(f"Transaction amount exceeds maximum limit: {self.max_sol_per_transaction} SOL")
        
        # Additional validation based on transaction type
        if transaction_type == "transfer":
            return self._validate_transfer(amount)
        elif transaction_type == "swap":
            return self._validate_swap(amount)
        elif transaction_type == "buy":
            return self._validate_buy(amount)
        
        return True
    
    def _validate_transfer(self, amount: float) -> bool:
        """Validate transfer transaction."""
        # Additional transfer-specific validation
        return True
    
    def _validate_swap(self, amount: float) -> bool:
        """Validate swap transaction."""
        # Additional swap-specific validation
        return True
    
    def _validate_buy(self, amount: float) -> bool:
        """Validate buy transaction."""
        # Additional buy-specific validation
        return True
```

#### Address Validation
```python
import base58
from typing import Optional

class AddressValidator:
    @staticmethod
    def validate_solana_address(address: str) -> bool:
        """Validate Solana address format and checksum."""
        try:
            # Decode base58
            decoded = base58.b58decode(address)
            
            # Check length (32 bytes for Solana addresses)
            if len(decoded) != 32:
                return False
            
            # Additional validation can be added here
            return True
        except Exception:
            return False
    
    @staticmethod
    def validate_token_mint(mint: str) -> bool:
        """Validate token mint address."""
        return AddressValidator.validate_solana_address(mint)
    
    @staticmethod
    def sanitize_address(address: str) -> Optional[str]:
        """Sanitize and validate address."""
        # Remove whitespace
        address = address.strip()
        
        # Validate format
        if not AddressValidator.validate_solana_address(address):
            return None
        
        return address
```

### 5. Error Handling and Information Disclosure

#### Secure Error Messages
```python
class SecureErrorHandler:
    @staticmethod
    def sanitize_error(error: Exception, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Sanitize error messages to prevent information disclosure."""
        error_type = type(error).__name__
        
        # Log full error details for debugging
        logger.error(f"Error for user {user_id}: {error}", exc_info=True)
        
        # Return sanitized error to user
        if "private key" in str(error).lower():
            return {
                "success": False,
                "error": "Authentication failed",
                "error_code": "AUTH_ERROR"
            }
        elif "network" in str(error).lower():
            return {
                "success": False,
                "error": "Network error occurred",
                "error_code": "NETWORK_ERROR"
            }
        elif "validation" in str(error).lower():
            return {
                "success": False,
                "error": "Invalid input parameters",
                "error_code": "VALIDATION_ERROR"
            }
        else:
            return {
                "success": False,
                "error": "An unexpected error occurred",
                "error_code": "UNKNOWN_ERROR"
            }
```

#### Audit Logging
```python
import json
from datetime import datetime
from typing import Dict, Any, Optional

class AuditLogger:
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    async def log_action(
        self,
        user_id: str,
        action: str,
        details: Dict[str, Any],
        success: bool,
        error: Optional[str] = None
    ) -> None:
        """Log user action for audit purposes."""
        audit_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "action": action,
            "success": success,
            "details": details,
            "error": error,
            "ip_address": details.get("ip_address"),
            "user_agent": details.get("user_agent")
        }
        
        # Store in secure audit log
        await self._store_audit_entry(audit_entry)
    
    async def _store_audit_entry(self, entry: Dict[str, Any]) -> None:
        """Store audit entry in database."""
        query = """
        INSERT INTO audit_log (timestamp, user_id, action, success, details, error, ip_address, user_agent)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            entry["timestamp"],
            entry["user_id"],
            entry["action"],
            entry["success"],
            json.dumps(entry["details"]),
            entry["error"],
            entry.get("ip_address"),
            entry.get("user_agent")
        )
        
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute(query, params)
            await conn.commit()
```

### 6. Session Management and Authentication

#### Secure Session Management
```python
import secrets
import hashlib
from typing import Dict, Optional
from datetime import datetime, timedelta

class SessionManager:
    def __init__(self, session_timeout: int = 3600):  # 1 hour
        self.session_timeout = session_timeout
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
    
    def create_session(self, user_id: str, metadata: Dict[str, Any] = None) -> str:
        """Create a new secure session."""
        session_id = secrets.token_urlsafe(32)
        
        self.active_sessions[session_id] = {
            "user_id": user_id,
            "created_at": datetime.utcnow(),
            "last_activity": datetime.utcnow(),
            "metadata": metadata or {},
            "csrf_token": secrets.token_urlsafe(32)
        }
        
        return session_id
    
    def validate_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Validate session and return session data."""
        if session_id not in self.active_sessions:
            return None
        
        session = self.active_sessions[session_id]
        
        # Check if session has expired
        if datetime.utcnow() - session["last_activity"] > timedelta(seconds=self.session_timeout):
            del self.active_sessions[session_id]
            return None
        
        # Update last activity
        session["last_activity"] = datetime.utcnow()
        return session
    
    def invalidate_session(self, session_id: str) -> None:
        """Invalidate a session."""
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
    
    def cleanup_expired_sessions(self) -> None:
        """Clean up expired sessions."""
        now = datetime.utcnow()
        expired_sessions = [
            session_id for session_id, session in self.active_sessions.items()
            if now - session["last_activity"] > timedelta(seconds=self.session_timeout)
        ]
        
        for session_id in expired_sessions:
            del self.active_sessions[session_id]
```

### 7. Network Security

#### HTTPS Enforcement
```python
from aiohttp import web
from aiohttp_middlewares import cors_middleware

def setup_security_middleware(app: web.Application) -> None:
    """Setup security middleware for web application."""
    
    # CORS middleware
    app.middlewares.append(cors_middleware(
        origins=["https://yourdomain.com"],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["*"]
    ))
    
    # Security headers middleware
    @web.middleware
    async def security_headers(request: web.Request, handler):
        response = await handler(request)
        
        # Security headers
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        response.headers['Content-Security-Policy'] = "default-src 'self'"
        
        return response
    
    app.middlewares.append(security_headers)
```

#### Request Validation
```python
from aiohttp import web
import json

class RequestValidator:
    @staticmethod
    async def validate_json_request(request: web.Request) -> Dict[str, Any]:
        """Validate and parse JSON request."""
        try:
            # Check content type
            if request.content_type != 'application/json':
                raise web.HTTPBadRequest(text="Content-Type must be application/json")
            
            # Parse JSON
            data = await request.json()
            
            # Validate required fields
            if not isinstance(data, dict):
                raise web.HTTPBadRequest(text="Request body must be a JSON object")
            
            return data
        
        except json.JSONDecodeError:
            raise web.HTTPBadRequest(text="Invalid JSON format")
        except Exception as e:
            raise web.HTTPBadRequest(text=f"Request validation failed: {str(e)}")
```

## Security Monitoring and Alerting

### 1. Anomaly Detection
```python
class SecurityMonitor:
    def __init__(self):
        self.user_activity: Dict[str, List[datetime]] = {}
        self.suspicious_patterns: List[str] = []
    
    def track_user_activity(self, user_id: str, action: str) -> None:
        """Track user activity for anomaly detection."""
        now = datetime.utcnow()
        
        if user_id not in self.user_activity:
            self.user_activity[user_id] = []
        
        self.user_activity[user_id].append(now)
        
        # Keep only recent activity (last 24 hours)
        cutoff = now - timedelta(hours=24)
        self.user_activity[user_id] = [
            activity for activity in self.user_activity[user_id]
            if activity > cutoff
        ]
        
        # Check for suspicious patterns
        self._check_suspicious_activity(user_id, action)
    
    def _check_suspicious_activity(self, user_id: str, action: str) -> None:
        """Check for suspicious user activity patterns."""
        activities = self.user_activity.get(user_id, [])
        
        # Check for rapid successive actions
        if len(activities) > 100:  # More than 100 actions in 24 hours
            self._alert_suspicious_activity(user_id, "High frequency activity")
        
        # Check for unusual transaction amounts
        if action.startswith("transfer") and "amount" in action:
            # Additional validation logic
            pass
    
    def _alert_suspicious_activity(self, user_id: str, reason: str) -> None:
        """Alert on suspicious activity."""
        alert = {
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "reason": reason,
            "severity": "HIGH"
        }
        
        # Send alert to security team
        logger.warning(f"Security alert: {alert}")
        
        # Store in security log
        self.suspicious_patterns.append(alert)
```

### 2. Security Metrics
```python
class SecurityMetrics:
    def __init__(self):
        self.metrics = {
            "failed_authentications": 0,
            "rate_limit_violations": 0,
            "invalid_requests": 0,
            "suspicious_activities": 0,
            "security_errors": 0
        }
    
    def increment_metric(self, metric_name: str) -> None:
        """Increment security metric."""
        if metric_name in self.metrics:
            self.metrics[metric_name] += 1
    
    def get_metrics(self) -> Dict[str, int]:
        """Get current security metrics."""
        return self.metrics.copy()
    
    def reset_metrics(self) -> None:
        """Reset security metrics."""
        for key in self.metrics:
            self.metrics[key] = 0
```

## Compliance and Privacy

### 1. Data Protection
```python
class DataProtection:
    def __init__(self):
        self.data_retention_days = 90
        self.encryption_key = Settings.SAM_FERNET_KEY
    
    async def anonymize_user_data(self, user_id: str) -> None:
        """Anonymize user data for privacy compliance."""
        # Remove or hash personally identifiable information
        # Keep only necessary data for system operation
        pass
    
    async def delete_user_data(self, user_id: str) -> None:
        """Delete user data for GDPR compliance."""
        # Delete all user-related data
        # Remove from databases, logs, and caches
        pass
    
    async def export_user_data(self, user_id: str) -> Dict[str, Any]:
        """Export user data for GDPR compliance."""
        # Collect all user-related data
        # Return in structured format
        pass
```

### 2. Audit Trail
```python
class ComplianceAudit:
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    async def log_data_access(self, user_id: str, data_type: str, purpose: str) -> None:
        """Log data access for compliance."""
        audit_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "data_type": data_type,
            "purpose": purpose,
            "action": "data_access"
        }
        
        await self._store_audit_entry(audit_entry)
    
    async def log_data_modification(self, user_id: str, data_type: str, changes: Dict[str, Any]) -> None:
        """Log data modification for compliance."""
        audit_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "data_type": data_type,
            "changes": changes,
            "action": "data_modification"
        }
        
        await self._store_audit_entry(audit_entry)
```

This comprehensive security architecture ensures that Horizon maintains the highest standards of security while providing the flexibility needed for autonomous trading operations. The multi-layered approach protects against various attack vectors while maintaining usability and performance.
