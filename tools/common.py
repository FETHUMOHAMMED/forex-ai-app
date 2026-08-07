from pathlib import Path
import sqlite3
import MetaTrader5 as mt5

# Project root
ROOT = Path(__file__).resolve().parent.parent

# Database path
DB_PATH = ROOT / "ai-service" / "trades.db"


def get_db():
    """Returns a connection to the trades database"""
    return sqlite3.connect(str(DB_PATH))


def check_mt5():
    """
    Check MT5 connection status
    
    Returns:
        dict with keys: connected, account, balance, equity, server
    """
    if not mt5.initialize():
        return {
            "connected": False,
            "account": None,
            "balance": 0,
            "equity": 0,
            "server": ""
        }

    info = mt5.account_info()

    if info is None:
        return {
            "connected": False,
            "account": None,
            "balance": 0,
            "equity": 0,
            "server": ""
        }

    return {
        "connected": True,
        "account": info.login,
        "balance": info.balance,
        "equity": info.equity,
        "server": info.server
    }


def check_daemon():
    """Check if the trading daemon is running"""
    return {"running": False, "pid": None}


def check_backend():
    """Check if the AI backend service is running"""
    return {"running": False, "url": None}