"""
Frontend Authentication Tools
Handles private key requests and authentication from chat interface.
"""

import asyncio
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

from sam.core.tools import Tool, ToolSpec
from sam.core.private_key_manager import PrivateKeyManager
from sam.utils.secure_storage import SecureStorage
from sam.utils.error_handling import handle_errors
from sam.utils.error_messages import handle_error_gracefully


class RequestPrivateKeyInput(BaseModel):
    """Input model for requesting private key from user."""
    session_id: str = Field(..., description="Unique session identifier")
    private_key: str = Field(..., description="Base58 encoded Solana private key")


class CheckAuthStatusInput(BaseModel):
    """Input model for checking authentication status."""
    session_id: str = Field(..., description="Unique session identifier")


class ClearAuthInput(BaseModel):
    """Input model for clearing authentication."""
    session_id: str = Field(..., description="Unique session identifier")


# Global private key manager instance
_private_key_manager: Optional[PrivateKeyManager] = None


def get_private_key_manager() -> PrivateKeyManager:
    """Get or create the global private key manager instance."""
    global _private_key_manager
    if _private_key_manager is None:
        from sam.utils.secure_storage import get_secure_storage
        secure_storage = get_secure_storage()
        _private_key_manager = PrivateKeyManager(secure_storage)
    return _private_key_manager


@handle_errors("frontend_auth")
async def request_private_key_handler(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Request and store a private key from the frontend chat interface.
    
    This tool should be called when the AI needs to perform transactions
    but doesn't have access to a private key yet.
    """
    try:
        input_data = RequestPrivateKeyInput(**args)
        private_key_manager = get_private_key_manager()
        
        result = await private_key_manager.request_private_key(
            input_data.session_id,
            input_data.private_key
        )
        
        if result["success"]:
            return {
                "success": True,
                "message": "Private key stored securely. You can now perform transactions.",
                "session_id": input_data.session_id,
                "authenticated": True
            }
        else:
            return result
            
    except Exception as e:
        return {
            "success": False,
            "error": "Failed to request private key",
            "error_detail": {"code": "request_error", "message": str(e)}
        }


@handle_errors("frontend_auth")
async def check_auth_status_handler(args: Dict[str, Any], agent=None) -> Dict[str, Any]:
    """
    Check if a session has an authenticated private key.
    
    This tool can be used to verify authentication status before
    attempting transactions.
    """
    try:
        # Get session_id from agent context if not provided in args
        session_id = args.get("session_id")
        if not session_id and agent and hasattr(agent, '_context'):
            session_id = getattr(agent._context, 'session_id', 'default')
        elif not session_id:
            session_id = 'default'
        
        private_key_manager = get_private_key_manager()
        
        has_key = await private_key_manager.has_private_key(session_id)
        
        return {
            "success": True,
            "authenticated": has_key,
            "session_id": session_id,
            "message": "Authenticated" if has_key else "Not authenticated - private key required"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": "Failed to check authentication status",
            "error_detail": {"code": "check_error", "message": str(e)}
        }


@handle_errors("frontend_auth")
async def clear_auth_handler(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Clear authentication for a session.
    
    This tool removes the stored private key for security purposes.
    """
    try:
        input_data = ClearAuthInput(**args)
        private_key_manager = get_private_key_manager()
        
        result = await private_key_manager.clear_session_key(input_data.session_id)
        
        if result["success"]:
            return {
                "success": True,
                "message": "Authentication cleared. Private key removed from secure storage.",
                "session_id": input_data.session_id,
                "authenticated": False
            }
        else:
            return result
            
    except Exception as e:
        return {
            "success": False,
            "error": "Failed to clear authentication",
            "error_detail": {"code": "clear_error", "message": str(e)}
        }


def register(registry, agent=None):
    """Register frontend authentication tools."""
    
    # Create wrapper functions that have access to the agent
    async def check_auth_status_wrapper(args: Dict[str, Any]) -> Dict[str, Any]:
        return await check_auth_status_handler(args, agent)
    
    async def request_private_key_wrapper(args: Dict[str, Any]) -> Dict[str, Any]:
        return await request_private_key_handler(args, agent)
    
    async def clear_auth_wrapper(args: Dict[str, Any]) -> Dict[str, Any]:
        return await clear_auth_handler(args, agent)
    
    # Check Auth Status Tool
    registry.register(Tool(
        spec=ToolSpec(
            name="check_auth_status",
            description="Check if the current session has an authenticated private key",
            input_schema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "Optional session identifier (will use current session if not provided)"
                    }
                }
            },
            namespace="frontend_auth",
            version="1.0.0"
        ),
        handler=check_auth_status_wrapper
    ))
    
    # Request Private Key Tool
    registry.register(Tool(
        spec=ToolSpec(
            name="request_private_key",
            description="Request and store a private key from the frontend chat interface. Use this when you need to perform transactions but don't have access to a private key yet.",
            input_schema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "Unique session identifier"
                    },
                    "private_key": {
                        "type": "string",
                        "description": "Base58 encoded Solana private key"
                    }
                },
                "required": ["session_id", "private_key"]
            },
            namespace="frontend_auth",
            version="1.0.0"
        ),
        handler=request_private_key_wrapper,
        input_model=RequestPrivateKeyInput
    ))
    
    # Clear Auth Tool
    registry.register(Tool(
        spec=ToolSpec(
            name="clear_auth",
            description="Clear authentication for a session by removing the stored private key. Use this for security purposes.",
            input_schema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "Unique session identifier"
                    }
                },
                "required": ["session_id"]
            },
            namespace="frontend_auth",
            version="1.0.0"
        ),
        handler=clear_auth_wrapper,
        input_model=ClearAuthInput
    ))
