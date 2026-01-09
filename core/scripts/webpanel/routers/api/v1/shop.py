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

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from db.shop_database import shop_db

router = APIRouter(prefix="/shop", tags=["Shop"])

CLIENTBOT_ENV = Path("/etc/hysteria/.clientbot.env")
CLIENTBOT_SERVICE = "hysteria-client-bot.service"


# ==================== SCHEMAS ====================

class ClientBotConfig(BaseModel):
    bot_token: str = Field(..., description="Telegram Bot Token")
    yookassa_shop_id: Optional[str] = Field("", description="YooKassa Shop ID")
    yookassa_secret_key: Optional[str] = Field("", description="YooKassa Secret Key")
    support_username: Optional[str] = Field("", description="Support Telegram username")
    trial_days: int = Field(3, description="Trial period days")
    trial_traffic_gb: int = Field(999999, description="Trial traffic limit")


class TariffCreate(BaseModel):
    name: str
    tariff_type: str  # "traffic" or "time"
    price: float
    traffic_gb: Optional[int] = None
    days: Optional[int] = None
    price_stars: Optional[int] = None


class TariffUpdate(BaseModel):
    name: Optional[str] = None
    price: Optional[float] = None
    traffic_gb: Optional[int] = None
    days: Optional[int] = None
    price_stars: Optional[int] = None
    is_active: Optional[bool] = None


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
        "yookassa_shop_id": "",
        "yookassa_secret_key": "",
        "support_username": "",
        "trial_days": 3,
        "trial_traffic_gb": 999999
    }
    
    if CLIENTBOT_ENV.exists():
        for line in CLIENTBOT_ENV.read_text().split('\n'):
            line = line.strip()
            if '=' in line and not line.startswith('#'):
                key, value = line.split('=', 1)
                key_lower = key.lower()
                if key_lower in config:
                    # Mask sensitive data
                    if 'token' in key_lower or 'secret' in key_lower:
                        config[key_lower] = "***" if value else ""
                    elif key_lower in ['trial_days', 'trial_traffic_gb']:
                        config[key_lower] = int(value) if value.isdigit() else config[key_lower]
                    else:
                        config[key_lower] = value
    
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
    
    # Write config
    content = f"""# Iridium Client Bot Configuration
BOT_TOKEN={config.bot_token}
YOOKASSA_SHOP_ID={config.yookassa_shop_id or ''}
YOOKASSA_SECRET_KEY={config.yookassa_secret_key or ''}
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
    Path(f"/etc/systemd/system/{CLIENTBOT_SERVICE}").write_text(service_content)
    
    # Start service
    subprocess.run(["systemctl", "daemon-reload"])
    subprocess.run(["systemctl", "enable", CLIENTBOT_SERVICE], capture_output=True)
    subprocess.run(["systemctl", "start", CLIENTBOT_SERVICE], capture_output=True)
    
    # Check if started
    result = subprocess.run(["systemctl", "is-active", "--quiet", CLIENTBOT_SERVICE])
    if result.returncode != 0:
        raise HTTPException(500, "Failed to start client bot")
    
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
    """Update client bot configuration"""
    if not CLIENTBOT_ENV.exists():
        raise HTTPException(400, "Client bot not configured. Start it first.")
    
    # Read existing config to preserve token if masked
    existing = {}
    for line in CLIENTBOT_ENV.read_text().split('\n'):
        if '=' in line and not line.startswith('#'):
            key, value = line.split('=', 1)
            existing[key] = value
    
    # Update only if new value is not masked
    bot_token = config.bot_token if config.bot_token != "***" else existing.get("BOT_TOKEN", "")
    yookassa_secret = config.yookassa_secret_key if config.yookassa_secret_key != "***" else existing.get("YOOKASSA_SECRET_KEY", "")
    
    content = f"""# Iridium Client Bot Configuration
BOT_TOKEN={bot_token}
YOOKASSA_SHOP_ID={config.yookassa_shop_id or ''}
YOOKASSA_SECRET_KEY={yookassa_secret}
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
    
    return {"detail": "Configuration updated"}


# ==================== TARIFFS ====================

@router.get("/tariffs")
async def get_tariffs():
    """Get all tariffs"""
    if not shop_db:
        raise HTTPException(500, "Database not available")
    
    tariffs = shop_db.get_all_tariffs()
    # Convert ObjectId to string
    for t in tariffs:
        t["_id"] = str(t["_id"])
    return {"tariffs": tariffs}


@router.post("/tariffs")
async def create_tariff(tariff: TariffCreate):
    """Create new tariff"""
    if not shop_db:
        raise HTTPException(500, "Database not available")
    
    result = shop_db.create_tariff(
        name=tariff.name,
        tariff_type=tariff.tariff_type,
        price=tariff.price,
        traffic_gb=tariff.traffic_gb,
        days=tariff.days,
        price_stars=tariff.price_stars
    )
    result["_id"] = str(result["_id"])
    return {"detail": "Tariff created", "tariff": result}


@router.put("/tariffs/{tariff_id}")
async def update_tariff(tariff_id: str, tariff: TariffUpdate):
    """Update tariff"""
    if not shop_db:
        raise HTTPException(500, "Database not available")
    
    updates = {k: v for k, v in tariff.dict().items() if v is not None}
    if not updates:
        raise HTTPException(400, "No updates provided")
    
    success = shop_db.update_tariff(tariff_id, updates)
    if not success:
        raise HTTPException(404, "Tariff not found")
    
    return {"detail": "Tariff updated"}


@router.delete("/tariffs/{tariff_id}")
async def delete_tariff(tariff_id: str):
    """Delete (deactivate) tariff"""
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
    if not shop_db:
        raise HTTPException(500, "Database not available")
    
    promos = shop_db.get_all_promos()
    for p in promos:
        p["_id"] = str(p["_id"])
        if p.get("expires_at"):
            p["expires_at"] = p["expires_at"].isoformat()
        if p.get("created_at"):
            p["created_at"] = p["created_at"].isoformat()
    return {"promos": promos}


@router.post("/promos")
async def create_promo(promo: PromoCreate):
    """Create new promo code"""
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
    if not shop_db:
        raise HTTPException(500, "Database not available")
    
    customers = shop_db.get_all_customers()
    for c in customers:
        if c.get("_id"):
            c["_id"] = str(c["_id"])
        if c.get("created_at"):
            c["created_at"] = c["created_at"].isoformat()
        if c.get("last_active"):
            c["last_active"] = c["last_active"].isoformat()
    return {"customers": customers}


# ==================== PAYMENTS / STATS ====================

@router.get("/payments/stats")
async def get_payment_stats(days: int = 30):
    """Get payment statistics"""
    if not shop_db:
        raise HTTPException(500, "Database not available")
    
    stats = shop_db.get_payments_stats(days)
    return {"stats": stats, "period_days": days}


@router.get("/payments")
async def get_payments(limit: int = 50):
    """Get recent payments"""
    if not shop_db:
        raise HTTPException(500, "Database not available")
    
    # Get all payments sorted by date
    payments = list(shop_db.payments.find({}).sort("created_at", -1).limit(limit))
    
    for p in payments:
        p["_id"] = str(p["_id"])
        if p.get("tariff_id"):
            p["tariff_id"] = str(p["tariff_id"])
        if p.get("created_at"):
            p["created_at"] = p["created_at"].isoformat()
        if p.get("completed_at"):
            p["completed_at"] = p["completed_at"].isoformat()
    
    return {"payments": payments}

