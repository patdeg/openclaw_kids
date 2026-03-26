# Minecraft — Server Management

Manage Minecraft servers running on **the remote server** (configured via `MINECRAFT_SSH_HOST`) via SSH.

The server setup uses `servers.yaml` as the source of truth for active
servers. Each server runs in a `screen` session under the `minecraft` user.
Shell scripts handle start/stop/restart/status.

## Usage

```
exec: python3 ~/skills/minecraft/minecraft.py status
exec: python3 ~/skills/minecraft/minecraft.py servers
exec: python3 ~/skills/minecraft/minecraft.py start <server>
exec: python3 ~/skills/minecraft/minecraft.py stop <server>
exec: python3 ~/skills/minecraft/minecraft.py restart <server>
exec: python3 ~/skills/minecraft/minecraft.py players [server]
exec: python3 ~/skills/minecraft/minecraft.py log <server> [--lines 50]
exec: python3 ~/skills/minecraft/minecraft.py backup <server>
exec: python3 ~/skills/minecraft/minecraft.py say <server> <message>
```

## Environment Variables

- `MINECRAFT_SSH_HOST` — Server hostname/IP (required)
- `MINECRAFT_SSH_USER` — SSH user (required)
- `MINECRAFT_SERVER_DIR` — Server directory (default: /usr/local/games/minecraft_server)

## Notes

- SSH to the Minecraft server can take 1-2 minutes (being investigated).
- Commands run as `sudo su minecraft -c '...'` since servers run under the
  `minecraft` user.
- Known worlds: pokemonserver, hame100day, VTR.v1, test
