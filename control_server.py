#!/usr/bin/env python3
"""
Control Server for Apache + mod_php
Manages the Apache web server running the PHP demo app
"""
import os
import subprocess
import json
from datetime import datetime
from flask import Flask, jsonify, request
import signal
import sys
import threading
import time

app = Flask(__name__)

# Configuration
APACHE_LOG_ERROR = "/var/log/apache2/error.log"
APACHE_LOG_ACCESS = "/var/log/apache2/access.log"
APACHE_LOG_OTHER = "/var/log/apache2/other_vhosts_access.log"
APACHE_PIDFILE = "/var/run/apache2/apache2.pid"
# Global state
apache_process = None
server_state = {
    "status": "stopped",
    "last_action": None,
    "last_action_time": None,
    "pid": None
}


def log_action(action, status="success", message=""):
    """Log server actions"""
    timestamp = datetime.now().isoformat()
    server_state["last_action"] = action
    server_state["last_action_time"] = timestamp
    print(f"[{timestamp}] {action}: {status} - {message}", flush=True)


def get_apache_pids():
    """Return a list of active Apache PIDs (from pidfile or pgrep)."""
    pids = []

    # Try pidfile first
    if os.path.exists(APACHE_PIDFILE):
        try:
            with open(APACHE_PIDFILE, "r") as f:
                pid = int(f.read().strip())
                if pid > 0:
                    pids.append(pid)
        except Exception as e:
            print(f"[WARN] Could not read PID file: {e}", flush=True)

    # Fallback to pgrep
    try:
        result = subprocess.run(
            ["pgrep", "-x", "apache2"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            for line in result.stdout.strip().splitlines():
                try:
                    pids.append(int(line))
                except ValueError:
                    pass
    except Exception as e:
        print(f"[WARN] Could not run pgrep: {e}", flush=True)

    return sorted(set(pids))


def check_apache_status():
    """Return True if Apache is running, False otherwise."""
    pids = get_apache_pids()
    if not pids:
        return False, None

    # Verify processes actually exist and are not zombies
    for pid in pids:
        try:
            with open(f"/proc/{pid}/status") as f:
                for line in f:
                    if line.startswith("State:"):
                        # Avoid counting zombies (Z)
                        if "Z" in line:
                            continue
                        return True, pid
        except FileNotFoundError:
            continue  # Process may have exited

    return False, None

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "apache-control-server",
        "timestamp": datetime.now().isoformat()
    })


@app.route('/status', methods=['GET'])
def status():
    """Get server status"""
    is_running, pid = check_apache_status()
    server_state["status"] = "running" if is_running else "stopped"
    server_state["pid"] = pid
    
    return jsonify({
        "apache_status": server_state["status"],
        "apache_pid": pid,
        "last_action": server_state["last_action"],
        "last_action_time": server_state["last_action_time"],
        "timestamp": datetime.now().isoformat()
    })


@app.route('/start_server', methods=['POST'])
def start_server():
    """Start Apache server"""
    try:
        is_running, pid = check_apache_status()
        if is_running:
            log_action("start_server", "info", "Apache already running")
            return jsonify({
                "is_running": is_running,
                "status": "already_running",
                "message": "Apache is already running",
                "pid": pid
            }), 200
        
        # Start Apache
        result = subprocess.run(
            ["apachectl", "-k", "start"],
            capture_output=True,
            text=True,
            timeout=10
        )
        time.sleep(1)
         
        if result.returncode == 0:
            is_running, pid = check_apache_status()
            pid = pid
            server_state["status"] = "running" if is_running else "stopped"
            server_state["pid"] = pid
            log_action("start_server", "success", f"Apache started with PID {pid}")
            
            return jsonify({
                "status": "success",
                "message": "Apache started successfully",
                "pid": pid,
                "is_running": is_running,
                "stdout": result.stdout,
                "stderr": result.stderr
            }), 200
        else:
            log_action("start_server", "error", result.stderr)
            return jsonify({
                "status": "error",
                "message": "Failed to start Apache",
                "stdout": result.stdout,
                "stderr": result.stderr
            }), 500
            
    except Exception as e:
        log_action("start_server", "error", str(e))
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.route('/stop_server', methods=['POST'])
def stop_server():
    """Stop Apache server"""
    try:
        is_running, pid = check_apache_status()
        if not is_running:
            log_action("stop_server", "info", "Apache not running")
            return jsonify({
                "is_running": is_running,
                "status": "not_running",
                "message": "Apache is not running"
            }), 200
        
        # Stop Apache
        result = subprocess.run(
            ["apachectl", "-k", "stop"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            time.sleep(1)  # Give Apache time to stop
            is_running, pid = check_apache_status()
            server_state["status"] = "running" if is_running else "stopped"
            server_state["pid"] = None
            log_action("stop_server", "success", "Apache stopped")
            
            return jsonify({
                "is_running": is_running,
                "status": "success",
                "message": "Apache stopped successfully",
                "stdout": result.stdout,
                "stderr": result.stderr
            }), 200
        else:
            log_action("stop_server", "error", result.stderr)
            return jsonify({
                "is_running": is_running,
                "status": "error",
                "message": "Failed to stop Apache",
                "stdout": result.stdout,
                "stderr": result.stderr
            }), 500
            
    except Exception as e:
        log_action("stop_server", "error", str(e))
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.route('/restart', methods=['POST'])
def restart():
    """Restart Apache server (hard restart)"""
    try:
        result = subprocess.run(
            ["apachectl", "-k", "restart"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            time.sleep(1)  # Give Apache time to restart
            is_running, pid = check_apache_status()
            server_state["status"] = "running"
            server_state["pid"] = pid
            log_action("restart", "success", f"Apache restarted with PID {pid}")
            
            return jsonify({
                "is_running": is_running,
                "status": "success",
                "message": "Apache restarted successfully",
                "pid": pid,
                "stdout": result.stdout,
                "stderr": result.stderr
            }), 200
        else:
            log_action("restart", "error", result.stderr)
            return jsonify({
                "is_running": is_running,
                "status": "error",
                "message": "Failed to restart Apache",
                "stdout": result.stdout,
                "stderr": result.stderr
            }), 500
            
    except Exception as e:
        log_action("restart", "error", str(e))
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.route('/graceful-restart', methods=['POST'])
def graceful_restart():
    """Gracefully restart Apache server"""
    try:
        result = subprocess.run(
            ["apachectl", "-k", "graceful"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            time.sleep(1)  # Give Apache time to gracefully restart
            is_running, pid = check_apache_status()
            server_state["status"] = "running" if is_running else "stopped"
            server_state["pid"] = pid
            log_action("graceful-restart", "success", f"Apache gracefully restarted with PID {pid}")
            
            return jsonify({
                "is_running": is_running,
                "status": "success",
                "message": "Apache gracefully restarted successfully",
                "pid": pid,
                "stdout": result.stdout,
                "stderr": result.stderr
            }), 200
        else:
            log_action("graceful-restart", "error", result.stderr)
            return jsonify({
                "status": "error",
                "message": "Failed to gracefully restart Apache",
                "stdout": result.stdout,
                "stderr": result.stderr
            }), 500
            
    except Exception as e:
        log_action("graceful-restart", "error", str(e))
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/graceful-stop', methods=['POST'])
def graceful_stop():
    """Gracefully stop Apache server"""
    try:
        result = subprocess.run(
            ["apachectl", "-k", "graceful-stop"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            time.sleep(1)  # Give Apache time to gracefully stop
            is_running, pid = check_apache_status()
            server_state["status"] = "running" if is_running else "stopped"
            server_state["pid"] = pid
            log_action("graceful-stop", "success", f"Apache gracefully stopped with PID {pid}")
            
            return jsonify({
                "is_running": is_running,
                "status": "success",
                "message": "Apache gracefully stopped successfully",
                "pid": pid,
                "stdout": result.stdout,
                "stderr": result.stderr
            }), 200
        else:
            log_action("graceful-stop", "error", result.stderr)
            return jsonify({
                "is_running": is_running,
                "status": "error",
                "message": "Failed to gracefully stop Apache",
                "stdout": result.stdout,
                "stderr": result.stderr
            }), 500
            
    except Exception as e:
        log_action("graceful-stop", "error", str(e))
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/get-server-logs', methods=['GET'])
def get_server_logs():
    """Get Apache server logs"""
    try:
        log_type = request.args.get('type', 'error')  # error, access, or all
        lines = request.args.get('lines', '100')
        
        try:
            lines = int(lines)
        except ValueError:
            lines = 100
        
        logs = {}
        
        if log_type in ['error', 'all']:
            if os.path.exists(APACHE_LOG_ERROR):
                result = subprocess.run(
                    ["tail", f"-n{lines}", APACHE_LOG_ERROR],
                    capture_output=True,
                    text=True
                )
                logs['error'] = result.stdout
            else:
                logs['error'] = "Error log not found"
        
        if log_type in ['access', 'all']:
            if os.path.exists(APACHE_LOG_ACCESS):
                result = subprocess.run(
                    ["tail", f"-n{lines}", APACHE_LOG_ACCESS],
                    capture_output=True,
                    text=True
                )
                logs['access'] = result.stdout
            else:
                logs['access'] = "Access log not found"
        
        return jsonify({
            "status": "success",
            "logs": logs,
            "lines": lines,
            "timestamp": datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        log_action("get-server-logs", "error", str(e))
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/uninstall-aikido', methods=['POST'])
def uninstall_aikido():
    try:
        subprocess.run(["dpkg", "--purge", "aikido-php-firewall"], capture_output=True, text=True, timeout=10)
        result = subprocess.run(["php", "-m"], capture_output=True, text=True, timeout=10)
        if result.returncode == 0 and "aikido" not in result.stdout.strip():
            return jsonify({
                "status": "success",
                "message": "Aikido uninstalled successfully",
            }), 200
        else:
            return jsonify({
                "status": "error",
                "message": "Failed to uninstall Aikido",
                "stdout": result.stdout,
                "stderr": result.stderr
            }), 500
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/install-aikido', methods=['POST'])
def install_aikido():
    #  .fly/scripts/aikido.sh
    try:
        subprocess.run(["./.fly/scripts/aikido.sh"], capture_output=True, text=True, timeout=10)
        result = subprocess.run(["php", "-m"], capture_output=True, text=True, timeout=10)
        if result.returncode == 0 and "aikido" in result.stdout.strip():
            return jsonify({
                "status": "success",
                "message": "Aikido installed successfully",
            }), 200
        else:
            return jsonify({
                "status": "error",
                "message": "Failed to install Aikido",
                "stdout": result.stdout,
                "stderr": result.stderr
            }), 500
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500



@app.route('/config-test', methods=['GET'])
def config_test():
    """Test Apache configuration"""
    try:
        result = subprocess.run(
            ["apachectl", "configtest"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        # apachectl configtest writes to stderr even on success
        is_success = result.returncode == 0 or "Syntax OK" in result.stderr
        
        return jsonify({
            "status": "success" if is_success else "error",
            "message": "Configuration test completed",
            "output": result.stderr + result.stdout,
            "returncode": result.returncode,
            "config_valid": is_success
        }), 200 if is_success else 400
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


def signal_handler(signum, frame):
    """Handle shutdown signals"""
    print(f"\nReceived signal {signum}, shutting down gracefully...", flush=True)
    
    # Stop Apache if running
    if check_apache_status():
        print("Stopping Apache...", flush=True)
        subprocess.run(["apachectl", "-k", "stop"], timeout=10)
    
    sys.exit(0)


if __name__ == '__main__':
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print("=" * 60, flush=True)
    print("Apache Control Server Starting", flush=True)
    print("=" * 60, flush=True)
    print(f"Listening on port 8081", flush=True)
    print("=" * 60, flush=True)
    
    # Start Flask server
    app.run(host='0.0.0.0', port=8081, debug=False)

