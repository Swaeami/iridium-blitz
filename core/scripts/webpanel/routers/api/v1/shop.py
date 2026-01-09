"""
Shop API Routes
Manage client bot, tariffs, promos, customers, payments
"""

import subprocess
import os
from datetime import datetime, timedelta
from typing import Optional, List
from pathlib import Path

from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel, Field

router = APIRouter(prefix="/shop", tags=["Shop"])

CLIENTBOT_ENV = Path("/etc/hysteria/.clientbot.env")
CLIENTBOT_SERVICE = "hysteria-client-bot.service"


def get_shop_db():
    """Lazy load shop database to handle connection errors gracefully"""
    try:
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
        from db.shop_database import shop_db
        return shop_db
    except Exception as e:
        print(f"Shop DB not available: {e}")
        return None


# ==================== SCHEMAS ====================

class ClientBotConfig(BaseModel):
    bot_token: str = Field(..., description="Telegram Bot Token")
    support_username: Optional[str] = Field("", description="Support Telegram username")
    trial_days: int = Field(3, description="Trial period days")
    trial_traffic_gb: int = Field(999999, description="Trial traffic limit")


class TariffCreate(BaseModel):
    name: str
    tariff_type: str  # "traffic" or "time"
    traffic_gb: Optional[int] = None
    price_1m: Optional[int] = None  # Price for 1 month
    price_3m: Optional[int] = None  # Price for 3 months
    price_6m: Optional[int] = None  # Price for 6 months
    price_12m: Optional[int] = None  # Price for 12 months


class PromoCreate(BaseModel):
    code: Optional[str] = None  # Auto-generate if empty
    promo_type: str  # "discount", "free_period", "extra_traffic"
    value: float
    max_uses: int = 1
    expire_days: Optional[int] = None  # 0 or None = never
    description: Optional[str] = ""


# ==================== CLIENT BOT MANAGEMENT ====================

@router.get("/clientbot/status")
async def get_clientbot_status():
    """Get client bot service status and config"""
    # Check service status
    result = subprocess.run(
        ["systemctl", "is-active", CLIENTBOT_SERVICE],
        capture_output=True, text=True
    )
    is_running = result.stdout.strip() == "active"
    
    # Read config if exists
    config = {
        "bot_token": "",
        "support_username": "",
        "trial_days": 3,
        "trial_traffic_gb": 999999
    }
    
    if CLIENTBOT_ENV.exists():
        try:
            for line in CLIENTBOT_ENV.read_text().split('\n'):
                line = line.strip()
                if '=' in line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    key_lower = key.lower()
                    if key_lower == 'bot_token':
                        config['bot_token'] = "***" if value else ""
                    elif key_lower == 'support_username':
                        config['support_username'] = value
                    elif key_lower == 'trial_days':
                        config['trial_days'] = int(value) if value.isdigit() else 3
                    elif key_lower == 'trial_traffic_gb':
                        config['trial_traffic_gb'] = int(value) if value.isdigit() else 999999
        except Exception as e:
            print(f"Error reading config: {e}")
    
    return {
        "is_running": is_running,
        "config": config
    }


@router.post("/clientbot/start")
async def start_clientbot(config: ClientBotConfig):
    """Start client bot service"""
    # Check if already running
    result = subprocess.run(
        ["systemctl", "is-active", "--quiet", CLIENTBOT_SERVICE]
    )
    if result.returncode == 0:
        raise HTTPException(400, "Client bot is already running")
    
    # Ensure parent directory exists
    CLIENTBOT_ENV.parent.mkdir(parents=True, exist_ok=True)
    
    # Write config
    content = f"""# Iridium Client Bot Configuration
BOT_TOKEN={config.bot_token}
SUPPORT_USERNAME={config.support_username or ''}
RETURN_URL=https://t.me
TRIAL_DAYS={config.trial_days}
TRIAL_TRAFFIC_GB={config.trial_traffic_gb}
"""
    CLIENTBOT_ENV.write_text(content)
    
    # Create service file
    service_content = """[Unit]
Description=Iridium Client Telegram Bot
After=network.target mongodb.service

[Service]
ExecStart=/bin/bash -c 'source /etc/hysteria/hysteria2_venv/bin/activate && /etc/hysteria/hysteria2_venv/bin/python /etc/hysteria/core/scripts/clientbot/bot.py'
WorkingDirectory=/etc/hysteria/core/scripts/clientbot
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
"""
    service_path = Path(f"/etc/systemd/system/{CLIENTBOT_SERVICE}")
    service_path.write_text(service_content)
    
    # Start service
    subprocess.run(["systemctl", "daemon-reload"])
    subprocess.run(["systemctl", "enable", CLIENTBOT_SERVICE], capture_output=True)
    result = subprocess.run(["systemctl", "start", CLIENTBOT_SERVICE], capture_output=True)
    
    # Check if started (wait a moment)
    import time
    time.sleep(1)
    check = subprocess.run(["systemctl", "is-active", "--quiet", CLIENTBOT_SERVICE])
    if check.returncode != 0:
        # Get error from journalctl
        err = subprocess.run(
            ["journalctl", "-u", CLIENTBOT_SERVICE, "-n", "5", "--no-pager"],
            capture_output=True, text=True
        )
        raise HTTPException(500, f"Failed to start client bot: {err.stdout or err.stderr}")
    
    return {"detail": "Client bot started successfully"}


@router.post("/clientbot/stop")
async def stop_clientbot():
    """Stop client bot service"""
    subprocess.run(["systemctl", "stop", CLIENTBOT_SERVICE], capture_output=True)
    subprocess.run(["systemctl", "disable", CLIENTBOT_SERVICE], capture_output=True)
    return {"detail": "Client bot stopped"}


@router.post("/clientbot/restart")
async def restart_clientbot():
    """Restart client bot service"""
    result = subprocess.run(["systemctl", "is-active", "--quiet", CLIENTBOT_SERVICE])
    if result.returncode != 0:
        raise HTTPException(400, "Client bot is not running")
    
    subprocess.run(["systemctl", "restart", CLIENTBOT_SERVICE])
    return {"detail": "Client bot restarted"}


@router.post("/clientbot/config")
async def update_clientbot_config(config: ClientBotConfig):
    """Update client bot configuration (save only, don't start)"""
    # Ensure parent directory exists
    CLIENTBOT_ENV.parent.mkdir(parents=True, exist_ok=True)
    
    # Read existing config to preserve token if masked
    existing_token = ""
    if CLIENTBOT_ENV.exists():
        try:
            for line in CLIENTBOT_ENV.read_text().split('\n'):
                if line.startswith('BOT_TOKEN='):
                    existing_token = line.split('=', 1)[1]
                    break
        except:
            pass
    
    # Use existing token if new one is masked
    bot_token = config.bot_token if config.bot_token != "***" else existing_token
    
    if not bot_token:
        raise HTTPException(400, "Bot token is required")
    
    content = f"""# Iridium Client Bot Configuration
BOT_TOKEN={bot_token}
SUPPORT_USERNAME={config.support_username or ''}
RETURN_URL=https://t.me
TRIAL_DAYS={config.trial_days}
TRIAL_TRAFFIC_GB={config.trial_traffic_gb}
"""
    CLIENTBOT_ENV.write_text(content)
    
    # Restart if running
    result = subprocess.run(["systemctl", "is-active", "--quiet", CLIENTBOT_SERVICE])
    if result.returncode == 0:
        subprocess.run(["systemctl", "restart", CLIENTBOT_SERVICE])
    
    return {"detail": "Configuration saved"}


# ==================== TARIFFS ====================

@router.get("/tariffs")
async def get_tariffs():
    """Get all tariffs"""
    shop_db = get_shop_db()
    if not shop_db:
        return {"tariffs": []}
    
    try:
        tariffs = shop_db.get_all_tariffs()
        for t in tariffs:
            t["_id"] = str(t["_id"])
        return {"tariffs": tariffs}
    except Exception as e:
        print(f"Error loading tariffs: {e}")
        return {"tariffs": []}


@router.post("/tariffs")
async def create_tariff(tariff: TariffCreate):
    """Create new tariff"""
    shop_db = get_shop_db()
    if not shop_db:
        raise HTTPException(500, "Database not available")
    
    # Create tariff with multi-period pricing
    tariff_data = {
        "name": tariff.name,
        "type": tariff.tariff_type,
        "traffic_gb": tariff.traffic_gb,
        "price_1m": tariff.price_1m,
        "price_3m": tariff.price_3m,
        "price_6m": tariff.price_6m,
        "price_12m": tariff.price_12m,
        "price_stars": tariff.price_1m,  # Default for compatibility
        "is_active": True,
        "created_at": datetime.utcnow()
    }
    
    result = shop_db.tariffs.insert_one(tariff_data)
    tariff_data["_id"] = str(result.inserted_id)
    
    return {"detail": "Tariff created", "tariff": tariff_data}


@router.delete("/tariffs/{tariff_id}")
async def delete_tariff(tariff_id: str):
    """Delete (deactivate) tariff"""
    shop_db = get_shop_db()
    if not shop_db:
        raise HTTPException(500, "Database not available")
    
    success = shop_db.delete_tariff(tariff_id)
    if not success:
        raise HTTPException(404, "Tariff not found")
    
    return {"detail": "Tariff deleted"}


# ==================== PROMO CODES ====================

@router.get("/promos")
async def get_promos():
    """Get all promo codes"""
    shop_db = get_shop_db()
    if not shop_db:
        return {"promos": []}
    
    try:
        promos = shop_db.get_all_promos()
        for p in promos:
            p["_id"] = str(p["_id"])
            if p.get("expires_at"):
                p["expires_at"] = p["expires_at"].isoformat()
            if p.get("created_at"):
                p["created_at"] = p["created_at"].isoformat()
        return {"promos": promos}
    except Exception as e:
        print(f"Error loading promos: {e}")
        return {"promos": []}


@router.post("/promos")
async def create_promo(promo: PromoCreate):
    """Create new promo code"""
    shop_db = get_shop_db()
    if not shop_db:
        raise HTTPException(500, "Database not available")
    
    expires_at = None
    if promo.expire_days and promo.expire_days > 0:
        expires_at = datetime.utcnow() + timedelta(days=promo.expire_days)
    
    result = shop_db.create_promo(
        code=promo.code if promo.code else None,
        promo_type=promo.promo_type,
        value=promo.value,
        max_uses=promo.max_uses,
        expires_at=expires_at,
        description=promo.description or ""
    )
    result["_id"] = str(result["_id"])
    if result.get("expires_at"):
        result["expires_at"] = result["expires_at"].isoformat()
    if result.get("created_at"):
        result["created_at"] = result["created_at"].isoformat()
    
    return {"detail": "Promo created", "promo": result}


@router.delete("/promos/{code}")
async def delete_promo(code: str):
    """Deactivate promo code"""
    shop_db = get_shop_db()
    if not shop_db:
        raise HTTPException(500, "Database not available")
    
    success = shop_db.deactivate_promo(code)
    if not success:
        raise HTTPException(404, "Promo not found")
    
    return {"detail": "Promo deactivated"}


# ==================== CUSTOMERS ====================

@router.get("/customers")
async def get_customers():
    """Get all customers"""
    shop_db = get_shop_db()
    if not shop_db:
        return {"customers": []}
    
    try:
        customers = shop_db.get_all_customers()
        for c in customers:
            if c.get("_id"):
                c["_id"] = str(c["_id"])
            if c.get("created_at"):
                c["created_at"] = c["created_at"].isoformat()
            if c.get("last_active"):
                c["last_active"] = c["last_active"].isoformat()
        return {"customers": customers}
    except Exception as e:
        print(f"Error loading customers: {e}")
        return {"customers": []}


# ==================== PAYMENTS / STATS ====================

@router.get("/payments/stats")
async def get_payment_stats(days: int = 30):
    """Get payment statistics"""
    shop_db = get_shop_db()
    if not shop_db:
        return {"stats": {}, "period_days": days}
    
    try:
        stats = shop_db.get_payments_stats(days)
        return {"stats": stats, "period_days": days}
    except Exception as e:
        print(f"Error loading stats: {e}")
        return {"stats": {}, "period_days": days}
