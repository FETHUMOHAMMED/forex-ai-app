#!/usr/bin/env python3
"""
ONE COMMAND TO RUN EVERYTHING
Run this and all services start automatically
"""

import subprocess
import sys
import os
import time
import threading
import signal

# Get the project root (where this script is)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
processes = []

def print_banner():
    print("=" * 60)
    print("🤖 FOREX AI TRADING SYSTEM")
    print("=" * 60)
    print("\nStarting all services...\n")

def run_command(cmd, cwd, name):
    """Run a command and return the process"""
    print(f"🚀 Starting {name}...")
    try:
        if sys.platform == "win32":
            process = subprocess.Popen(
                cmd,
                cwd=cwd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )
        else:
            process = subprocess.Popen(
                cmd,
                cwd=cwd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )
        
        # Print output in real-time
        def print_output():
            for line in iter(process.stdout.readline, ''):
                if line:
                    print(f"[{name}] {line.strip()}")
        
        thread = threading.Thread(target=print_output)
        thread.daemon = True
        thread.start()
        
        return process
    except Exception as e:
        print(f"❌ Failed to start {name}: {e}")
        return None

def signal_handler(sig, frame):
    print("\n\n🛑 Shutting down all services...")
    for process in processes:
        if process:
            process.terminate()
    time.sleep(2)
    sys.exit(0)

def main():
    signal.signal(signal.SIGINT, signal_handler)
    print_banner()
    
    # 1. First, install dependencies if needed
    print("📦 Checking dependencies...")
    
    # Check if AI service venv exists
    ai_venv = os.path.join(PROJECT_ROOT, "ai-service", "venv")
    if not os.path.exists(ai_venv):
        print("📦 Creating Python virtual environment...")
        subprocess.run([sys.executable, "-m", "venv", ai_venv], cwd=os.path.join(PROJECT_ROOT, "ai-service"))
    
    # Install Python packages
    pip_path = os.path.join(ai_venv, "Scripts", "pip") if sys.platform == "win32" else os.path.join(ai_venv, "bin", "pip")
    subprocess.run([pip_path, "install", "-r", "requirements.txt"], cwd=os.path.join(PROJECT_ROOT, "ai-service"))
    
    # Install Node dependencies if needed
    backend_node_modules = os.path.join(PROJECT_ROOT, "backend", "node_modules")
    if not os.path.exists(backend_node_modules):
        print("📦 Installing backend dependencies...")
        subprocess.run(["npm", "install"], cwd=os.path.join(PROJECT_ROOT, "backend"))
    
    frontend_node_modules = os.path.join(PROJECT_ROOT, "frontend", "node_modules")
    if not os.path.exists(frontend_node_modules):
        print("📦 Installing frontend dependencies...")
        subprocess.run(["npm", "install"], cwd=os.path.join(PROJECT_ROOT, "frontend"))
    
    print("\n✅ Dependencies ready!\n")
    
    # 2. Start AI Service
    python_path = os.path.join(ai_venv, "Scripts", "python") if sys.platform == "win32" else os.path.join(ai_venv, "bin", "python")
    ai_process = run_command(
        f'"{python_path}" ai_service.py',
        os.path.join(PROJECT_ROOT, "ai-service"),
        "AI Service"
    )
    if ai_process:
        processes.append(ai_process)
    
    time.sleep(3)  # Wait for AI service to initialize
    
    # 3. Start Backend
    backend_process = run_command(
        "npm run dev" if sys.platform != "win32" else "npm run dev",
        os.path.join(PROJECT_ROOT, "backend"),
        "Backend"
    )
    if backend_process:
        processes.append(backend_process)
    
    time.sleep(2)
    
    # 4. Start Frontend
    frontend_process = run_command(
        "npm start",
        os.path.join(PROJECT_ROOT, "frontend"),
        "Frontend"
    )
    if frontend_process:
        processes.append(frontend_process)
    
    print("\n" + "=" * 60)
    print("✅ ALL SERVICES RUNNING!")
    print("=" * 60)
    print("\n📊 Dashboard: http://localhost:3000")
    print("🔌 API: http://localhost:3001")
    print("📡 WebSocket: ws://localhost:8080")
    print("\n⚠️  Press CTRL+C to stop all services")
    print("=" * 60)
    
    # Keep running
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        signal_handler(None, None)

if __name__ == "__main__":
    main()