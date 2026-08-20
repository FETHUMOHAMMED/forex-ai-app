from pathlib import Path
import sqlite3
import MetaTrader5 as mt5
import psutil
import socket
import os
from datetime import datetime, timezone

# Project root
ROOT = Path(__file__).resolve().parent.parent

# Database path
DB_PATH = ROOT / "ai-service" / "trades.db"

# Service definitions
SERVICES = {
    "trading_daemon": {
        "name": "Trading Daemon",
        "process_name": "python",
        "expected_scripts": ["ai_service_daemon.py", "daemon_v2.py", "auto_trader"],
        "expected_port": None,  # Daemon doesn't listen on a port
        "heartbeat_file": "ai-service/trading_daemon_heartbeat.json"
    },
    "backend_api": {
        "name": "Backend API",
        "process_name": "python",
        "expected_scripts": ["uvicorn", "main:app", "server"],
        "expected_port": 8001,
        "heartbeat_file": "ai-service/api_heartbeat.json"
    },
    "frontend": {
        "name": "Frontend Dashboard",
        "process_name": "node",
        "expected_scripts": ["react-scripts", "webpack"],
        "expected_port": 3000,
        "heartbeat_file": None
    },
    "backend_server": {
        "name": "Backend Server (Node)",
        "process_name": "node",
        "expected_scripts": ["server.js"],
        "expected_port": 8080,
        "heartbeat_file": None
    }
}


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


def find_process_by_script(script_patterns):
    """Find Python processes running specific scripts"""
    matches = []
    for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time']):
        try:
            cmdline = proc.info['cmdline']
            if cmdline:
                cmdline_str = ' '.join(cmdline).lower()
                if any(pattern.lower() in cmdline_str for pattern in script_patterns):
                    matches.append({
                        'pid': proc.info['pid'],
                        'cmdline': cmdline,
                        'start_time': datetime.fromtimestamp(proc.info['create_time'], tz=timezone.utc)
                    })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return matches


def check_port(port):
    """Check if a port is listening"""
    if port is None:
        return False
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('127.0.0.1', port))
    sock.close()
    return result == 0


def check_heartbeat(heartbeat_file):
    """Check last heartbeat timestamp"""
    if heartbeat_file is None:
        return None
    
    full_path = ROOT / heartbeat_file
    if not full_path.exists():
        return None
    
    try:
        with open(full_path, 'r') as f:
            import json
            data = json.load(f)
            return data.get('last_heartbeat')
    except:
        return None


def check_service(service_key):
    """Comprehensive service health check"""
    service = SERVICES.get(service_key)
    if not service:
        return {"status": "UNKNOWN", "error": "Service not defined"}
    
    result = {
        "name": service["name"],
        "status": "OFFLINE",
        "expected_port": service.get("expected_port"),
        "process": None,
        "last_heartbeat": None
    }
    
    # Check by port first (most reliable for services that listen)
    if service.get("expected_port"):
        if check_port(service["expected_port"]):
            result["status"] = "ONLINE"
    
    # Find process
    if service.get("expected_scripts"):
        processes = find_process_by_script(service["expected_scripts"])
        if processes:
            result["status"] = "ONLINE"
            result["process"] = processes[0]  # Return first match
    
    # Check heartbeat file
    if service.get("heartbeat_file"):
        heartbeat = check_heartbeat(service["heartbeat_file"])
        if heartbeat:
            result["last_heartbeat"] = heartbeat
            if result["status"] == "OFFLINE":
                result["status"] = "STALE"  # Process dead but heartbeat exists
    
    return result


def check_daemon():
    """Check if the trading daemon is running (legacy compat)"""
    status = check_service("trading_daemon")
    return {
        "running": status["status"] == "ONLINE",
        "pid": status["process"]["pid"] if status["process"] else None,
        "details": status
    }


def check_backend():
    """Check if the AI backend service is running (legacy compat)"""
    status = check_service("backend_api")
    return {
        "running": status["status"] == "ONLINE",
        "url": f"http://localhost:{status['expected_port']}" if status["status"] == "ONLINE" else None,
        "details": status
    }
