#!/usr/bin/env python3
"""Minecraft skill — manage servers on a remote machine via SSH."""

import argparse
import json
import os
import subprocess
import sys

SSH_HOST = os.environ.get("MINECRAFT_SSH_HOST", "192.168.1.100")
SSH_USER = os.environ.get("MINECRAFT_SSH_USER", "minecraft")
SERVER_DIR = os.environ.get(
    "MINECRAFT_SERVER_DIR", "/usr/local/games/minecraft_server"
)
SSH_TIMEOUT = 180  # seconds — SSH can be slow on some setups


def ssh_cmd(command, timeout=SSH_TIMEOUT):
    """Run a command on the Minecraft server via SSH. Returns (stdout, stderr, returncode)."""
    ssh_args = [
        "ssh",
        "-o", "ConnectTimeout=30",
        "-o", "StrictHostKeyChecking=no",
        "-o", "BatchMode=yes",
        f"{SSH_USER}@{SSH_HOST}",
        command,
    ]
    try:
        result = subprocess.run(
            ssh_args,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.stdout.strip(), result.stderr.strip(), result.returncode
    except subprocess.TimeoutExpired:
        return "", "SSH connection timed out", 1
    except Exception as e:
        return "", str(e), 1


def mc_cmd(script, args=""):
    """Run a minecraft server script as the minecraft user."""
    cmd = f"sudo su minecraft -c '{SERVER_DIR}/{script} {args}'"
    return ssh_cmd(cmd)


def cmd_status(_args):
    """Check which servers are running."""
    stdout, stderr, rc = mc_cmd("status.sh")
    if rc != 0:
        print(json.dumps({"error": stderr or "Failed to get status"}))
        sys.exit(1)
    print(json.dumps({"status": stdout}))


def cmd_servers(_args):
    """List all configured servers from servers.yaml."""
    stdout, stderr, rc = ssh_cmd(f"cat {SERVER_DIR}/servers.yaml")
    if rc != 0:
        print(json.dumps({"error": stderr or "Failed to read servers.yaml"}))
        sys.exit(1)
    print(json.dumps({"servers_yaml": stdout}))


def cmd_start(args):
    """Start a server."""
    stdout, stderr, rc = mc_cmd("start.sh", args.server)
    if rc != 0:
        print(json.dumps({"error": stderr or f"Failed to start {args.server}"}))
        sys.exit(1)
    print(json.dumps({"success": True, "message": stdout or f"Started {args.server}"}))


def cmd_stop(args):
    """Stop a server."""
    stdout, stderr, rc = mc_cmd("stop.sh", args.server)
    if rc != 0:
        print(json.dumps({"error": stderr or f"Failed to stop {args.server}"}))
        sys.exit(1)
    print(json.dumps({"success": True, "message": stdout or f"Stopped {args.server}"}))


def cmd_restart(args):
    """Restart a server."""
    stdout, stderr, rc = mc_cmd("restart.sh", args.server)
    if rc != 0:
        print(json.dumps({"error": stderr or f"Failed to restart {args.server}"}))
        sys.exit(1)
    print(json.dumps({"success": True, "message": stdout or f"Restarted {args.server}"}))


def cmd_players(args):
    """List online players."""
    server = args.server or ""
    # Use status.sh which typically shows player count
    stdout, stderr, rc = mc_cmd("status.sh", server)
    if rc != 0:
        print(json.dumps({"error": stderr or "Failed to get players"}))
        sys.exit(1)
    print(json.dumps({"players": stdout}))


def cmd_log(args):
    """Show recent server logs."""
    lines = args.lines or 50
    log_args = f"{args.server} {lines}" if args.server else str(lines)
    stdout, stderr, rc = mc_cmd("log.sh", log_args)
    if rc != 0:
        print(json.dumps({"error": stderr or "Failed to get logs"}))
        sys.exit(1)
    print(json.dumps({"log": stdout}))


def cmd_backup(args):
    """Create a backup of a server world."""
    stdout, stderr, rc = mc_cmd("create-backup.sh", args.server)
    if rc != 0:
        print(json.dumps({"error": stderr or f"Failed to backup {args.server}"}))
        sys.exit(1)
    print(json.dumps({"success": True, "message": stdout or f"Backup created for {args.server}"}))


def cmd_say(args):
    """Broadcast a message to a server."""
    server = args.server
    message = " ".join(args.message)
    # Use screen to send a /say command to the server console
    cmd = (
        f"sudo su minecraft -c \""
        f"screen -S {server} -p 0 -X stuff '/say {message}\\n'"
        f"\""
    )
    stdout, stderr, rc = ssh_cmd(cmd)
    if rc != 0:
        print(json.dumps({"error": stderr or f"Failed to send message to {server}"}))
        sys.exit(1)
    print(json.dumps({"success": True, "message": f"Broadcast to {server}: {message}"}))


def main():
    parser = argparse.ArgumentParser(description="Minecraft server management")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("status", help="Check server status")
    subparsers.add_parser("servers", help="List configured servers")

    start_p = subparsers.add_parser("start", help="Start a server")
    start_p.add_argument("server", help="Server name")

    stop_p = subparsers.add_parser("stop", help="Stop a server")
    stop_p.add_argument("server", help="Server name")

    restart_p = subparsers.add_parser("restart", help="Restart a server")
    restart_p.add_argument("server", help="Server name")

    players_p = subparsers.add_parser("players", help="List online players")
    players_p.add_argument("server", nargs="?", default="", help="Server name")

    log_p = subparsers.add_parser("log", help="Show server logs")
    log_p.add_argument("server", help="Server name")
    log_p.add_argument("--lines", type=int, default=50, help="Number of lines")

    backup_p = subparsers.add_parser("backup", help="Backup a server")
    backup_p.add_argument("server", help="Server name")

    say_p = subparsers.add_parser("say", help="Broadcast message")
    say_p.add_argument("server", help="Server name")
    say_p.add_argument("message", nargs="+", help="Message to broadcast")

    args = parser.parse_args()

    commands = {
        "status": cmd_status,
        "servers": cmd_servers,
        "start": cmd_start,
        "stop": cmd_stop,
        "restart": cmd_restart,
        "players": cmd_players,
        "log": cmd_log,
        "backup": cmd_backup,
        "say": cmd_say,
    }

    if args.command in commands:
        commands[args.command](args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
