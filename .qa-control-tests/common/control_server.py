#!/usr/bin/env python3

import os
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone

from flask import Flask, jsonify, request


app = Flask(__name__)

SERVER_MODE = os.environ.get("QA_SERVER", "")
PHP_VERSION = os.environ.get("QA_PHP_VERSION", "8.2")


def process(name, pidfile, pgrep, commands, logs):
    return {
        "name": name,
        "pidfile": pidfile,
        "pgrep": pgrep,
        "commands": commands,
        "logs": logs,
    }


APACHE = process(
    "apache",
    "/run/apache2/apache2.pid",
    ["pgrep", "-x", "apache2"],
    {
        "start": [["apachectl", "-k", "start"]],
        "stop": [["apachectl", "-k", "stop"]],
        "restart": [["apachectl", "-k", "restart"]],
        "graceful-restart": [["apachectl", "-k", "graceful"]],
        "graceful-stop": [["apachectl", "-k", "graceful-stop"]],
    },
    {
        "error": "/var/log/apache2/error.log",
        "access": "/var/log/apache2/access.log",
    },
)

NGINX = process(
    "nginx",
    "/run/nginx.pid",
    ["pgrep", "-x", "nginx"],
    {
        "start": [["nginx"]],
        "stop": [["nginx", "-s", "stop"]],
        "restart": [["nginx", "-s", "stop"], ["nginx"]],
        "graceful-restart": [["nginx", "-s", "reload"]],
        "graceful-stop": [["nginx", "-s", "quit"]],
    },
    {
        "error": "/var/log/nginx/error.log",
        "access": "/var/log/nginx/access.log",
    },
)

FPM = process(
    "fpm",
    f"/run/php/php{PHP_VERSION}-fpm.pid",
    ["pgrep", "-f", "php-fpm: master"],
    {
        "start": [[f"php-fpm{PHP_VERSION}"]],
        "stop": [["kill", "-TERM", "{pid}"]],
        "restart": [["kill", "-TERM", "{pid}"], [f"php-fpm{PHP_VERSION}"]],
        "graceful-restart": [["kill", "-USR2", "{pid}"]],
        "graceful-stop": [["kill", "-TERM", "{pid}"]],
    },
    {"error": f"/var/log/php{PHP_VERSION}-fpm.log"},
)

MODES = {
    "apache-mod-php": [APACHE],
    "apache-php-fpm": [FPM, APACHE],
    "nginx-php-fpm": [FPM, NGINX],
}

if SERVER_MODE not in MODES:
    raise RuntimeError(f"Unsupported QA_SERVER: {SERVER_MODE!r}")

PROCESSES = MODES[SERVER_MODE]
last_action = {"name": None, "time": None}


def live_pid(pid):
    try:
        with open(f"/proc/{pid}/status", encoding="utf-8") as status_file:
            state = next(
                line for line in status_file if line.startswith("State:")
            )
        return "Z" not in state
    except (FileNotFoundError, PermissionError, StopIteration):
        return False


def pidfile_pid(spec):
    try:
        with open(spec["pidfile"], encoding="utf-8") as pidfile:
            pid = int(pidfile.read().strip())
        return pid if live_pid(pid) else None
    except (FileNotFoundError, PermissionError, ValueError):
        return None


def process_pids(spec):
    pids = set()
    if pid := pidfile_pid(spec):
        pids.add(pid)

    result = subprocess.run(
        spec["pgrep"], capture_output=True, text=True, timeout=5, check=False
    )
    if result.returncode == 0:
        for value in result.stdout.splitlines():
            try:
                pids.add(int(value))
            except ValueError:
                pass
    return sorted(pid for pid in pids if live_pid(pid))


def state():
    process_state = {
        spec["name"]: {
            "status": "running" if (pids := process_pids(spec)) else "stopped",
            "pids": pids,
        }
        for spec in PROCESSES
    }
    return process_state


def wait_for_state(expected_running, timeout=30):
    deadline = time.monotonic() + timeout
    while True:
        current = state()
        matches = all(
            (details["status"] == "running") == expected_running
            for details in current.values()
        )
        if matches or time.monotonic() >= deadline:
            return current, matches
        time.sleep(1)


def wait_for_process(spec, expected_running, timeout=30):
    deadline = time.monotonic() + timeout
    while True:
        running = bool(process_pids(spec))
        if running == expected_running or time.monotonic() >= deadline:
            return running == expected_running
        time.sleep(1)


def wait_for_ready_pidfile(spec, timeout=30):
    deadline = time.monotonic() + timeout
    while True:
        if pidfile_pid(spec) or time.monotonic() >= deadline:
            return
        time.sleep(1)


def run_command(command, capture_output=True):
    output_options = (
        {"capture_output": True, "text": True}
        if capture_output
        else {"stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
    )
    result = subprocess.run(command, timeout=50, check=False, **output_options)
    return {
        "command": command,
        "returncode": result.returncode,
        "stdout": result.stdout if capture_output else "",
        "stderr": result.stderr if capture_output else "",
    }


def run_process_action(spec, action):
    results = []
    commands = spec["commands"][action]
    for index, command in enumerate(commands):
        pids = process_pids(spec)
        resolved = [
            value.replace("{pid}", str(pids[0]) if pids else "")
            for value in command
        ]
        # Server daemons may retain inherited file descriptors after the
        # launcher exits. Do not capture those descriptors or the request can
        # wait forever for EOF even though the service started successfully.
        results.append(run_command(resolved, capture_output=False))
        if index < len(commands) - 1:
            wait_for_process(spec, False)
    return results


def run_lifecycle(action):
    expected_running = action not in {"stop", "graceful-stop"}
    current = state()
    ordered = PROCESSES if expected_running else list(reversed(PROCESSES))
    results = {}

    for spec in ordered:
        is_running = current[spec["name"]]["status"] == "running"
        effective_action = action
        if action == "start" and is_running:
            results[spec["name"]] = {"skipped": "already running"}
            continue
        if expected_running and not is_running:
            effective_action = "start"
        elif not expected_running and not is_running:
            results[spec["name"]] = {"skipped": "already stopped"}
            continue

        results[spec["name"]] = run_process_action(spec, effective_action)
        if expected_running:
            # A process can appear before its master PID file is updated. Wait
            # for the file so a following stop/restart cannot target a stale PID.
            wait_for_ready_pidfile(spec)

    final_state, reached_state = wait_for_state(expected_running)
    last_action.update(
        name=action,
        time=datetime.now(timezone.utc).isoformat(),
    )
    still_running = any(
        details["status"] == "running" for details in final_state.values()
    )

    return jsonify(
        {
            "status": "success" if reached_state else "partial",
            "is_running": (
                all(
                    details["status"] == "running"
                    for details in final_state.values()
                )
                if expected_running
                else still_running
            ),
            "processes": final_state,
            "results": results,
        }
    ), 200


@app.get("/health")
def health():
    return jsonify(
        {
            "status": "healthy",
            "service": f"{SERVER_MODE}-control-server",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )


@app.get("/status")
def status():
    current = state()
    is_running = all(
        details["status"] == "running" for details in current.values()
    )
    return jsonify(
        {
            "status": "running" if is_running else "stopped",
            "is_running": is_running,
            "processes": current,
            "last_action": last_action,
        }
    )


@app.post("/start_server")
def start_server():
    return run_lifecycle("start")


@app.post("/stop_server")
def stop_server():
    return run_lifecycle("stop")


@app.post("/restart")
def restart():
    return run_lifecycle("restart")


@app.post("/graceful-restart")
def graceful_restart():
    return run_lifecycle("graceful-restart")


@app.post("/graceful-stop")
def graceful_stop():
    return run_lifecycle("graceful-stop")


def tail(path, lines):
    if not os.path.exists(path):
        return "Log not found"
    result = subprocess.run(
        ["tail", f"-n{lines}", path],
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )
    return result.stdout


@app.get("/get-server-logs")
def get_server_logs():
    log_type = request.args.get("type", "error")
    try:
        lines = max(1, min(int(request.args.get("lines", "100")), 10000))
    except ValueError:
        lines = 100

    logs = {}
    for spec in PROCESSES:
        for kind, path in spec["logs"].items():
            if log_type in {kind, "all"}:
                logs[f"{spec['name']}_{kind}"] = tail(path, lines)
    return jsonify(status="success", logs=logs, lines=lines)


def php_has_aikido():
    result = subprocess.run(
        ["php", "-m"], capture_output=True, text=True, timeout=10, check=False
    )
    return result.returncode == 0 and "aikido" in result.stdout.lower(), result


@app.post("/uninstall-aikido")
def uninstall_aikido():
    subprocess.run(
        ["dpkg", "--purge", "aikido-php-firewall"],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    installed, result = php_has_aikido()
    uninstalled = result.returncode == 0 and not installed
    return (
        jsonify(
            status="success" if uninstalled else "error",
            message=(
                "Aikido uninstalled successfully"
                if uninstalled
                else "Failed to uninstall Aikido"
            ),
            stdout=result.stdout,
            stderr=result.stderr,
        ),
        200 if uninstalled else 500,
    )


@app.post("/install-aikido")
def install_aikido():
    install = subprocess.run(
        ["./.fly/scripts/aikido.sh"],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    installed, modules = php_has_aikido()
    return (
        jsonify(
            status="success" if installed else "error",
            message=(
                "Aikido installed successfully"
                if installed
                else "Failed to install Aikido"
            ),
            stdout=install.stdout + modules.stdout,
            stderr=install.stderr + modules.stderr,
        ),
        200 if installed else 500,
    )


@app.get("/config-test")
def config_test():
    command = (
        ["nginx", "-t"]
        if SERVER_MODE.startswith("nginx")
        else ["apachectl", "configtest"]
    )
    result = run_command(command)
    valid = result["returncode"] == 0
    return (
        jsonify(
            status="success" if valid else "error",
            config_valid=valid,
            **result,
        ),
        200 if valid else 400,
    )


@app.post("/install-aikido-version")
def install_aikido_version():
    version = (request.get_json(silent=True) or {}).get("version")
    if not version:
        return jsonify(status="error", message="Version parameter is required"), 400

    architecture = subprocess.run(
        ["uname", "-m"], capture_output=True, text=True, check=True
    ).stdout.strip()
    filename = f"{version}-aikido-php-firewall.{architecture}.deb"
    filepath = f"/tmp/{filename}"
    url = f"https://github.com/AikidoSec/firewall-php/releases/download/v{version}/aikido-php-firewall.{architecture}.deb"
    download = subprocess.run(
        ["curl", "--fail", "--location", "--output", filepath, url],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    if download.returncode != 0:
        return (
            jsonify(
                status="error",
                message="Failed to download package",
                stderr=download.stderr,
            ),
            500,
        )

    install = subprocess.run(
        ["dpkg", "-i", "-E", filepath],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    if install.returncode != 0:
        return (
            jsonify(
                status="error",
                message="Failed to install package",
                stdout=install.stdout,
                stderr=install.stderr,
            ),
            500,
        )
    return jsonify(
        status="success",
        message=f"Successfully installed Aikido v{version}",
        filename=filename,
    )


@app.post("/kill-aikido-agent")
def kill_aikido_agent():
    subprocess.run(
        ["pkill", "-f", "aikido-agent"],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        result = subprocess.run(
            ["pgrep", "-f", "aikido-agent"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if result.returncode != 0 or not any(
            live_pid(int(pid)) for pid in result.stdout.splitlines() if pid.isdigit()
        ):
            return jsonify(status="success", message="Aikido agent killed successfully")
        time.sleep(1)
    return jsonify(status="error", message="Aikido agent still running"), 500


def signal_handler(signum, _frame):
    print(f"Received signal {signum}; stopping managed services", flush=True)
    try:
        current = state()
        for spec in reversed(PROCESSES):
            if current[spec["name"]]["status"] == "running":
                run_process_action(spec, "stop")
    finally:
        sys.exit(0)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    print(f"Starting {SERVER_MODE} control server on port 8081", flush=True)
    app.run(host="0.0.0.0", port=8081, debug=False)
