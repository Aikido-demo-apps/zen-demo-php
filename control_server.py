#!/usr/bin/env python3
"""
Control Server for Nginx + PHP-FPM
Manages the Nginx web server and PHP-FPM process for the PHP demo app
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
NGINX_LOG_ERROR = "/var/log/nginx/error.log"
NGINX_LOG_ACCESS = "/var/log/nginx/access.log"
NGINX_PIDFILE = "/run/nginx.pid"
PHP_FPM_PIDFILE = "/run/php/php8.2-fpm.pid"
PHP_FPM_LOG = "/var/log/php8.2-fpm.log"

# Global state
nginx_process = None
fpm_process = None
server_state = {
    "nginx_status": "stopped",
    "fpm_status": "stopped",
    "last_action": None,
    "last_action_time": None,
    "nginx_pid": None,
    "fpm_pid": None
}


def log_action(action, status="success", message=""):
    """Log server actions"""
    timestamp = datetime.now().isoformat()
    server_state["last_action"] = action
    server_state["last_action_time"] = timestamp
    print(f"[{timestamp}] {action}: {status} - {message}", flush=True)


def get_nginx_pids():
    """Return a list of active Nginx PIDs (from pidfile or pgrep)."""
    pids = []

    # Try pidfile first
    if os.path.exists(NGINX_PIDFILE):
        try:
            with open(NGINX_PIDFILE, "r") as f:
                pid = int(f.read().strip())
                if pid > 0:
                    pids.append(pid)
        except Exception as e:
            print(f"[WARN] Could not read PID file: {e}", flush=True)

    # Fallback to pgrep
    try:
        result = subprocess.run(
            ["pgrep", "-x", "nginx"],
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


def check_nginx_status():
    """Return True if Nginx is running, False otherwise."""
    pids = get_nginx_pids()
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


def get_fpm_pids():
    """Return a list of active PHP-FPM PIDs."""
    pids = []

    # Try pidfile first
    if os.path.exists(PHP_FPM_PIDFILE):
        try:
            with open(PHP_FPM_PIDFILE, "r") as f:
                pid = int(f.read().strip())
                if pid > 0:
                    pids.append(pid)
        except Exception as e:
            print(f"[WARN] Could not read PHP-FPM PID file: {e}", flush=True)

    # Fallback to pgrep
    try:
        result = subprocess.run(
            ["pgrep", "-f", "php-fpm: master"],
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
        print(f"[WARN] Could not run pgrep for PHP-FPM: {e}", flush=True)

    return sorted(set(pids))


def check_fpm_status():
    """Return True if PHP-FPM is running, False otherwise."""
    pids = get_fpm_pids()
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
    nginx_running, _ = check_nginx_status()
    fpm_running, _ = check_fpm_status()
    
    return jsonify({
        "status": "healthy",
        "service": "nginx-fpm-control-server",
        "nginx_running": nginx_running,
        "fpm_running": fpm_running,
        "timestamp": datetime.now().isoformat()
    })


@app.route('/status', methods=['GET'])
def status():
    """Get server status"""
    is_running, nginx_pid = check_nginx_status()
    fpm_running, fpm_pid = check_fpm_status()
    
    server_state["nginx_status"] = "running" if is_running else "stopped"
    server_state["fpm_status"] = "running" if fpm_running else "stopped"
    server_state["nginx_pid"] = nginx_pid
    server_state["fpm_pid"] = fpm_pid
    
    return jsonify({
        "nginx_status": server_state["nginx_status"],
        "nginx_pid": nginx_pid,
        "fpm_status": server_state["fpm_status"],
        "fpm_pid": fpm_pid,
        "last_action": server_state["last_action"],
        "last_action_time": server_state["last_action_time"],
        "timestamp": datetime.now().isoformat()
    })


@app.route('/start_server', methods=['POST'])
def start_server():
    """Start Nginx and PHP-FPM"""
    try:
        nginx_running, nginx_pid = check_nginx_status()
        fpm_running, fpm_pid = check_fpm_status()
        
        results = {"nginx": {}, "fpm": {}}
        
        # Start PHP-FPM first
        if not fpm_running:
            fpm_result = subprocess.run(
                ["service", "php8.2-fpm", "start"],
                capture_output=True,
                text=True,
                timeout=10
            )
            time.sleep(1)
            fpm_running, fpm_pid = check_fpm_status()
            results["fpm"] = {
                "status": "success" if fpm_running else "error",
                "pid": fpm_pid,
                "stdout": fpm_result.stdout,
                "stderr": fpm_result.stderr
            }
        else:
            results["fpm"] = {"status": "already_running", "pid": fpm_pid}
        
        # Start Nginx
        if not nginx_running:
            try:
                nginx_result = subprocess.run(
                    ["service", "nginx", "start"],
                    capture_output=True,
                    text=True,
                    timeout=3
                )
            except subprocess.TimeoutExpired:
                # Service command might hang, but check if nginx actually started
                pass
            time.sleep(1)
            nginx_running, nginx_pid = check_nginx_status()
            results["nginx"] = {
                "status": "success" if nginx_running else "error",
                "pid": nginx_pid,
                "stdout": "",
                "stderr": ""
            }
        else:
            results["nginx"] = {"status": "already_running", "pid": nginx_pid}
        
        server_state["nginx_status"] = "running" if nginx_running else "stopped"
        server_state["fpm_status"] = "running" if fpm_running else "stopped"
        server_state["nginx_pid"] = nginx_pid
        server_state["fpm_pid"] = fpm_pid
        
        overall_status = "success" if (nginx_running and fpm_running) else "partial"
        log_action("start_server", overall_status, f"Nginx: {nginx_running}, FPM: {fpm_running}")
        
        return jsonify({
            "status": overall_status,
            "message": f"Nginx: {'running' if nginx_running else 'stopped'}, FPM: {'running' if fpm_running else 'stopped'}",
            "nginx_running": nginx_running,
            "fpm_running": fpm_running,
            "results": results,
            "is_running": fpm_running and nginx_running
        }), 200
            
    except Exception as e:
        log_action("start_server", "error", str(e))
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.route('/stop_server', methods=['POST'])
def stop_server():
    """Stop Nginx and PHP-FPM"""
    try:
        nginx_running, nginx_pid = check_nginx_status()
        fpm_running, fpm_pid = check_fpm_status()
        
        results = {"nginx": {}, "fpm": {}}
        
        # Stop Nginx first
        if nginx_running:
            nginx_result = subprocess.run(
                ["service", "nginx", "stop"],
                capture_output=True,
                text=True,
                timeout=10
            )
            time.sleep(2)
            nginx_running, nginx_pid = check_nginx_status()
            results["nginx"] = {
                "status": "success" if not nginx_running else "error",
                "pid": nginx_pid,
                "stdout": nginx_result.stdout,
                "stderr": nginx_result.stderr
            }
        else:
            results["nginx"] = {"status": "not_running"}
        
        # Stop PHP-FPM
        if fpm_running:
            fpm_result = subprocess.run(
                ["service", "php8.2-fpm", "stop"],
                capture_output=True,
                text=True,
                timeout=50
            )
            time.sleep(2)
            fpm_running, fpm_pid = check_fpm_status()
            results["fpm"] = {
                "status": "success" if not fpm_running else "error",
                "pid": fpm_pid,
                "stdout": fpm_result.stdout,
                "stderr": fpm_result.stderr
            }
        else:
            results["fpm"] = {"status": "not_running"}
        
        server_state["nginx_status"] = "running" if nginx_running else "stopped"
        server_state["fpm_status"] = "running" if fpm_running else "stopped"
        server_state["nginx_pid"] = nginx_pid
        server_state["fpm_pid"] = fpm_pid
        
        overall_status = "success" if (not nginx_running and not fpm_running) else "partial"
        log_action("stop_server", overall_status, f"Nginx: {not nginx_running}, FPM: {not fpm_running}")
        
        return jsonify({
            "status": overall_status,
            "message": f"Nginx: {'stopped' if not nginx_running else 'running'}, FPM: {'stopped' if not fpm_running else 'running'}",
            "nginx_running": nginx_running,
            "fpm_running": fpm_running,
            "results": results,
            "is_running": fpm_running or nginx_running
        }), 200
            
    except Exception as e:
        log_action("stop_server", "error", str(e))
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.route('/restart', methods=['POST'])
def restart():
    """Restart Nginx and PHP-FPM (hard restart)"""
    try:
        results = {"nginx": {}, "fpm": {}}
        
        # Restart PHP-FPM
        fpm_result = subprocess.run(
            ["service", "php8.2-fpm", "restart"],
            capture_output=True,
            text=True,
            timeout=50
        )
        time.sleep(1)
        fpm_running, fpm_pid = check_fpm_status()
        results["fpm"] = {
            "status": "success" if fpm_running else "error",
            "pid": fpm_pid,
            "stdout": fpm_result.stdout,
            "stderr": fpm_result.stderr
        }
        
        # Restart Nginx
        try:
            nginx_result = subprocess.run(
                ["service", "nginx", "restart"],
                capture_output=True,
                text=True,
                timeout=3
            )
        except subprocess.TimeoutExpired:
            # Service command might hang, but check if nginx actually restarted
            pass
        time.sleep(1)
        nginx_running, nginx_pid = check_nginx_status()
        results["nginx"] = {
            "status": "success" if nginx_running else "error",
            "pid": nginx_pid,
            "stdout": "",
            "stderr": ""
        }
        
        server_state["nginx_status"] = "running" if nginx_running else "stopped"
        server_state["fpm_status"] = "running" if fpm_running else "stopped"
        server_state["nginx_pid"] = nginx_pid
        server_state["fpm_pid"] = fpm_pid
        
        overall_status = "success" if (nginx_running and fpm_running) else "partial"
        log_action("restart", overall_status, f"Nginx PID: {nginx_pid}, FPM PID: {fpm_pid}")
        
        return jsonify({
            "status": overall_status,
            "message": f"Nginx: {'running' if nginx_running else 'stopped'}, FPM: {'running' if fpm_running else 'stopped'}",
            "nginx_running": nginx_running,
            "fpm_running": fpm_running,
            "results": results,
            "is_running": fpm_running and nginx_running
        }), 200
            
    except Exception as e:
        log_action("restart", "error", str(e))
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.route('/graceful-restart', methods=['POST'])
def graceful_restart():
    """Gracefully restart Nginx and PHP-FPM"""
    try:
        results = {"nginx": {}, "fpm": {}}
        fpm_running, fpm_pid = check_fpm_status()
        if not fpm_running:
            # start php-fpm
            fpm_result = subprocess.run(
                ["service", "php8.2-fpm", "start"],
                capture_output=True,
                text=True,
                timeout=50
            )
            
        else:
            # Gracefully reload PHP-FPM
            fpm_result = subprocess.run(
                ["service", "php8.2-fpm", "reload"],
                capture_output=True,
                text=True,
                timeout=50
            )

        time.sleep(1)
        fpm_running, fpm_pid = check_fpm_status()
        results["fpm"] = {
            "status": "success" if fpm_running else "error",
            "pid": fpm_pid,
            "stdout": fpm_result.stdout,
            "stderr": fpm_result.stderr
        }
        
        # Gracefully reload Nginx
        nginx_running_before, _ = check_nginx_status()
        try:
            if not nginx_running_before:
                # If not running, start it
                nginx_result = subprocess.run(
                    ["service", "nginx", "start"],
                    capture_output=True,
                    text=True,
                    timeout=3
                )
            else:
                # If running, reload it
                nginx_result = subprocess.run(
                    ["service", "nginx", "reload"],
                    capture_output=True,
                    text=True,
                    timeout=3
                )
        except subprocess.TimeoutExpired:
            # Service command might hang, but check if nginx is running
            pass
        time.sleep(1)
        nginx_running, nginx_pid = check_nginx_status()
        results["nginx"] = {
            "status": "success" if nginx_running else "error",
            "pid": nginx_pid,
            "stdout": "",
            "stderr": ""
        }
        
        server_state["nginx_status"] = "running" if nginx_running else "stopped"
        server_state["fpm_status"] = "running" if fpm_running else "stopped"
        server_state["nginx_pid"] = nginx_pid
        server_state["fpm_pid"] = fpm_pid
        
        overall_status = "success" if (nginx_running and fpm_running) else "partial"
        log_action("graceful-restart", overall_status, f"Nginx PID: {nginx_pid}, FPM PID: {fpm_pid}")
        
        return jsonify({
            "status": overall_status,
            "message": f"Nginx: {'running' if nginx_running else 'stopped'}, FPM: {'running' if fpm_running else 'stopped'}",
            "nginx_running": nginx_running,
            "fpm_running": fpm_running,
            "results": results,
            "is_running": fpm_running and nginx_running
        }), 200
            
    except Exception as e:
        log_action("graceful-restart", "error", str(e))
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/graceful-stop', methods=['POST'])
def graceful_stop():
    """Gracefully stop Nginx and PHP-FPM"""
    try:
        results = {"nginx": {}, "fpm": {}}
        
        # Gracefully stop Nginx
        nginx_result = subprocess.run(
            ["service", "nginx", "stop"],
            capture_output=True,
            text=True,
            timeout=10
        )
        time.sleep(2)
        nginx_running, nginx_pid = check_nginx_status()
        results["nginx"] = {
            "status": "success" if not nginx_running else "error",
            "pid": nginx_pid,
            "stdout": nginx_result.stdout,
            "stderr": nginx_result.stderr
        }
        
        # Stop PHP-FPM
        fpm_result = subprocess.run(
            ["service", "php8.2-fpm", "stop"],
            capture_output=True,
            text=True,
            timeout=50
        )
        time.sleep(2)
        fpm_running, fpm_pid = check_fpm_status()
        results["fpm"] = {
            "status": "success" if not fpm_running else "error",
            "pid": fpm_pid,
            "stdout": fpm_result.stdout,
            "stderr": fpm_result.stderr
        }
        
        server_state["nginx_status"] = "running" if nginx_running else "stopped"
        server_state["fpm_status"] = "running" if fpm_running else "stopped"
        server_state["nginx_pid"] = nginx_pid
        server_state["fpm_pid"] = fpm_pid
        
        overall_status = "success" if (not nginx_running and not fpm_running) else "partial"
        log_action("graceful-stop", overall_status, f"Nginx: {not nginx_running}, FPM: {not fpm_running}")
        
        return jsonify({
            "status": overall_status,
            "message": f"Nginx: {'stopped' if not nginx_running else 'running'}, FPM: {'stopped' if not fpm_running else 'running'}",
            "nginx_running": nginx_running,
            "fpm_running": fpm_running,
            "results": results
        }), 200
            
    except Exception as e:
        log_action("graceful-stop", "error", str(e))
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/get-server-logs', methods=['GET'])
def get_server_logs():
    """Get Nginx server logs"""
    try:
        log_type = request.args.get('type', 'error')  # error, access, or all
        lines = request.args.get('lines', '100')
        
        try:
            lines = int(lines)
        except ValueError:
            lines = 100
        
        logs = {}
        
        if log_type in ['error', 'all']:
            if os.path.exists(NGINX_LOG_ERROR):
                result = subprocess.run(
                    ["tail", f"-n{lines}", NGINX_LOG_ERROR],
                    capture_output=True,
                    text=True
                )
                logs['error'] = result.stdout
            else:
                logs['error'] = "Error log not found"
        
        if log_type in ['access', 'all']:
            if os.path.exists(NGINX_LOG_ACCESS):
                result = subprocess.run(
                    ["tail", f"-n{lines}", NGINX_LOG_ACCESS],
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
    """Test Nginx configuration"""
    try:
        result = subprocess.run(
            ["nginx", "-t"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        # nginx -t writes to stderr even on success
        is_success = result.returncode == 0 or "syntax is ok" in result.stderr
        
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

#/install-aikido-version
@app.route('/install-aikido-version', methods=['POST'])
def install_aikido_version():
    try:
        data = request.get_json()
        version = data.get('version')
        
        if not version:
            return jsonify({'error': 'Version parameter is required'}), 400
        
        # Get architecture
        arch_result = subprocess.run(['uname', '-i'], capture_output=True, text=True)
        arch = arch_result.stdout.strip()
        
        # Construct filename with version prefix
        filename = f"{version}-aikido-php-firewall.{arch}.deb"
        filepath = f"/tmp/{filename}"
        
        # Download the package
        download_url = f"https://github.com/AikidoSec/firewall-php/releases/download/v{version}/aikido-php-firewall.{arch}.deb"
        
        print(f"Downloading Aikido v{version} from {download_url}...", flush=True)
        curl_result = subprocess.run(
            ['curl', '-L', '-o', filepath, download_url],
            capture_output=True,
            text=True
        )
        
        if curl_result.returncode != 0:
            return jsonify({
                'error': f'Failed to download package: {curl_result.stderr}'
            }), 500
        
        # Install the package
        print(f"Installing {filename}...", flush=True)
        dpkg_result = subprocess.run(
            ['dpkg', '-i', '-E', filepath],
            capture_output=True,
            text=True
        )
        
        if dpkg_result.returncode != 0:
            return jsonify({
                'error': f'Failed to install package: {dpkg_result.stderr}',
                'stdout': dpkg_result.stdout
            }), 500
        
        return jsonify({
            'status': 'success',
            'message': f'Successfully installed Aikido v{version}',
            'filename': filename,
            'output': dpkg_result.stdout
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/kill-aikido-agent', methods=['POST'])
def kill_aikido_agent():
    try:
        subprocess.run(["pkill", "-f", "aikido-agent"], capture_output=True, text=True, timeout=10)
        time.sleep(1)
        # search for aikido-agent in the process list to see if it is still running
        result = subprocess.run(["ps", "-ef"], capture_output=True, text=True, timeout=10)
        # remove zombies from the process list
        result.stdout = [line for line in result.stdout.splitlines() if "Z" not in line]
        if "aikido-agent" in result.stdout:
            return jsonify({
                "status": "error",
                "message": "Aikido agent still running",
            }), 500
        else:
            return jsonify({
                "status": "success",
                "message": "Aikido agent killed successfully",
            }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    print(f"\nReceived signal {signum}, shutting down gracefully...", flush=True)
    
    # Stop Nginx if running
    nginx_running, _ = check_nginx_status()
    if nginx_running:
        print("Stopping Nginx...", flush=True)
        subprocess.run(["service", "nginx", "stop"], timeout=10)
    
    # Stop PHP-FPM if running
    fpm_running, _ = check_fpm_status()
    if fpm_running:
        print("Stopping PHP-FPM...", flush=True)
        subprocess.run(["service", "php8.2-fpm", "stop"], timeout=50)
    
    sys.exit(0)


if __name__ == '__main__':
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print("=" * 60, flush=True)
    print("Nginx + PHP-FPM Control Server Starting", flush=True)
    print("=" * 60, flush=True)
    print(f"Listening on port 8081", flush=True)
    print("=" * 60, flush=True)
    
    # Start Flask server
    app.run(host='0.0.0.0', port=8081, debug=False)
