#!/usr/bin/env python3
"""
Client Bot Runner
Manages the client Telegram bot service
"""

import sys
import subprocess
from pathlib import Path
import os

CLIENTBOT_ENV = Path("/etc/hysteria/.clientbot.env")
SERVICE_FILE = Path("/etc/systemd/system/hysteria-client-bot.service")


def update_env_file(
    bot_token: str,
    yookassa_shop_id: str = "",
    yookassa_secret_key: str = "",
    support_username: str = "",
    return_url: str = "https://t.me"
):
    """Update or create .clientbot.env file"""
    content = f"""# Iridium Client Bot Configuration
BOT_TOKEN={bot_token}

# YooKassa (optional)
YOOKASSA_SHOP_ID={yookassa_shop_id}
YOOKASSA_SECRET_KEY={yookassa_secret_key}

# Support
SUPPORT_USERNAME={support_username}
RETURN_URL={return_url}

# Trial settings
TRIAL_DAYS=3
TRIAL_TRAFFIC_GB=999999
"""
    CLIENTBOT_ENV.write_text(content)
    print(f"Configuration saved to {CLIENTBOT_ENV}")


def create_service_file():
    """Create systemd service file"""
    SERVICE_FILE.write_text("""[Unit]
Description=Iridium Client Telegram Bot
After=network.target mongodb.service

[Service]
ExecStart=/bin/bash -c 'source /etc/hysteria/hysteria2_venv/bin/activate && /etc/hysteria/hysteria2_venv/bin/python /etc/hysteria/core/scripts/clientbot/bot.py'
WorkingDirectory=/etc/hysteria/core/scripts/clientbot
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
""")
    print(f"Service file created at {SERVICE_FILE}")


def start_service(
    bot_token: str,
    yookassa_shop_id: str = "",
    yookassa_secret_key: str = "",
    support_username: str = ""
):
    """Start the client bot service"""
    # Check if already running
    if subprocess.run(
        ["systemctl", "is-active", "--quiet", "hysteria-client-bot.service"]
    ).returncode == 0:
        print("The hysteria-client-bot.service is already running.")
        return
    
    # Update config and create service
    update_env_file(bot_token, yookassa_shop_id, yookassa_secret_key, support_username)
    create_service_file()
    
    # Start service
    subprocess.run(["systemctl", "daemon-reload"])
    subprocess.run(
        ["systemctl", "enable", "hysteria-client-bot.service"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    subprocess.run(
        ["systemctl", "start", "hysteria-client-bot.service"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    
    # Check status
    if subprocess.run(
        ["systemctl", "is-active", "--quiet", "hysteria-client-bot.service"]
    ).returncode == 0:
        print("✅ Client bot setup completed. The service is now running.")
    else:
        print("❌ Client bot setup completed but the service failed to start.")
        print("Check logs with: journalctl -u hysteria-client-bot.service -f")


def stop_service():
    """Stop the client bot service"""
    subprocess.run(
        ["systemctl", "stop", "hysteria-client-bot.service"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    subprocess.run(
        ["systemctl", "disable", "hysteria-client-bot.service"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    print("✅ Client bot service stopped and disabled.")


def restart_service():
    """Restart the client bot service"""
    subprocess.run(["systemctl", "restart", "hysteria-client-bot.service"])
    print("✅ Client bot service restarted.")


def status_service():
    """Check service status"""
    result = subprocess.run(
        ["systemctl", "is-active", "hysteria-client-bot.service"],
        capture_output=True, text=True
    )
    status = result.stdout.strip()
    
    if status == "active":
        print("✅ Client bot is running")
    else:
        print(f"❌ Client bot is {status}")
    
    return status == "active"


def update_config(key: str, value: str):
    """Update a single config value"""
    if not CLIENTBOT_ENV.exists():
        print("Error: Configuration file does not exist. Start the bot first.")
        return False
    
    content = CLIENTBOT_ENV.read_text()
    lines = content.split('\n')
    found = False
    
    new_lines = []
    for line in lines:
        if line.strip().startswith(f"{key}="):
            new_lines.append(f"{key}={value}")
            found = True
        else:
            new_lines.append(line)
    
    if not found:
        new_lines.append(f"{key}={value}")
    
    CLIENTBOT_ENV.write_text('\n'.join(new_lines))
    print(f"✅ Updated {key}")
    
    # Restart to apply
    if subprocess.run(
        ["systemctl", "is-active", "--quiet", "hysteria-client-bot.service"]
    ).returncode == 0:
        restart_service()
    
    return True


def print_usage():
    """Print usage information"""
    print("""
Iridium Client Bot Manager

Usage:
  python3 runclientbot.py start <BOT_TOKEN> [YOOKASSA_SHOP_ID] [YOOKASSA_SECRET_KEY] [SUPPORT_USERNAME]
  python3 runclientbot.py stop
  python3 runclientbot.py restart
  python3 runclientbot.py status
  python3 runclientbot.py config <KEY> <VALUE>

Examples:
  python3 runclientbot.py start 123456:ABC-DEF
  python3 runclientbot.py start 123456:ABC-DEF shop_123 live_xxx support_user
  python3 runclientbot.py config TRIAL_DAYS 7
  python3 runclientbot.py config SUPPORT_USERNAME myusername

Config Keys:
  BOT_TOKEN, YOOKASSA_SHOP_ID, YOOKASSA_SECRET_KEY,
  SUPPORT_USERNAME, RETURN_URL, TRIAL_DAYS, TRIAL_TRAFFIC_GB
""")
    sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print_usage()
    
    action = sys.argv[1]
    
    if action == "start":
        if len(sys.argv) < 3:
            print_usage()
        
        bot_token = sys.argv[2]
        yookassa_shop_id = sys.argv[3] if len(sys.argv) > 3 else ""
        yookassa_secret_key = sys.argv[4] if len(sys.argv) > 4 else ""
        support_username = sys.argv[5] if len(sys.argv) > 5 else ""
        
        start_service(bot_token, yookassa_shop_id, yookassa_secret_key, support_username)
    
    elif action == "stop":
        stop_service()
    
    elif action == "restart":
        restart_service()
    
    elif action == "status":
        status_service()
    
    elif action == "config":
        if len(sys.argv) != 4:
            print_usage()
        update_config(sys.argv[2], sys.argv[3])
    
    else:
        print_usage()

