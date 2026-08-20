"""API Authentication - Simple API key for order-mutating endpoints"""
import os
from fastapi import HTTPException, Header
from typing import Optional

API_KEY = os.getenv("FOREX_API_KEY", "dev-key-2026")

def verify_api_key(x_api_key: Optional[str] = Header(None)):
    """Verify API key for protected endpoints"""
    if x_api_key is None or x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return True
