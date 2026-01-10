#!/usr/bin/env python3
"""
Iridium Client Bot
Telegram bot for customers to purchase VPN subscriptions
All navigation via inline buttons - single message editing
Simplified UX: main menu shows profile if subscription exists
"""

import os
import sys
import secrets
import string
from datetime import datetime
from typing import Optional

import telebot
from telebot import types

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.shop_database import shop_db
from db.database import db as vpn_db
from clientbot.utils.keyboards import (
    main_menu_keyboard, tariffs_keyboard, tariff_detail_keyboard,
    back_to_main_keyboard, support_keyboard,
    confirm_trial_keyboard, promo_keyboard, promo_result_keyboard, faq_keyboard
)
from clientbot.utils.payment import PaymentManager


# ==================== CONFIGURATION ====================

def load_config():
    """Load bot configuration from environment file"""
    config_path = "/etc/hysteria/.clientbot.env"
    config = {
        "BOT_TOKEN": None,
        "SUPPORT_USERNAME": None,
        "TRIAL_DAYS": 3,
    }
    
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            for line in f:
                line = line.strip()
                if '=' in line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    if key in config:
                        config[key] = value.strip('"\'')
    
    return config


CONFIG = load_config()
bot = telebot.TeleBot(CONFIG["BOT_TOKEN"]) if CONFIG["BOT_TOKEN"] else None
payment_manager = PaymentManager()

# Store users waiting for promo code input
waiting_for_promo = {}


# ==================== HELPERS ====================

def rub_to_stars(price_rub: int) -> int:
    """Convert price from rubles to Telegram Stars (1.5x multiplier)"""
    return int(price_rub * 1.5)


def get_tariff_stars(tariff: dict) -> int:
    """Get tariff price in stars (calculated from rubles)"""
    return rub_to_stars(tariff.get("price_rub", 0))


def generate_vpn_password(length: int = 32) -> str:
    """Generate random VPN password"""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def generate_vpn_username(telegram_id: int) -> str:
    """Generate unique VPN username from Telegram ID"""
    return f"tg{telegram_id}"


def get_or_create_customer(message) -> dict:
    """Get existing customer or create new one"""
    customer = shop_db.get_customer(message.from_user.id)
    if not customer:
        customer = shop_db.create_customer(
            telegram_id=message.from_user.id,
            telegram_username=message.from_user.username
        )
    return customer


def get_or_create_customer_by_id(telegram_id: int, username: str = None) -> dict:
    """Get existing customer or create new one by telegram_id"""
    customer = shop_db.get_customer(telegram_id)
    if not customer:
        customer = shop_db.create_customer(
            telegram_id=telegram_id,
            telegram_username=username
        )
    return customer


def create_or_extend_subscription(customer: dict, days: int, max_ips: int = None) -> Optional[str]:
    """Create new subscription or extend existing one"""
    vpn_username = customer.get("vpn_username") or generate_vpn_username(customer["telegram_id"])
    password = generate_vpn_password()
    
    try:
        existing = vpn_db.get_user(vpn_username)
        
        if existing:
            current_days = existing.get("expiration_days", 0)
            updates = {"expiration_days": current_days + days}
            if max_ips is not None:
                updates["max_ips"] = max_ips
            vpn_db.update_user(vpn_username, updates)
        else:
            user_data = {
                "username": vpn_username,
                "password": password,
                "max_download_bytes": 999999 * 1073741824,
                "expiration_days": days,
                "blocked": False,
                "status": "Active",
                "account_creation_date": datetime.now().strftime("%Y-%m-%d")
            }
            if max_ips is not None:
                user_data["max_ips"] = max_ips
            vpn_db.add_user(user_data)
        
        shop_db.update_customer(customer["telegram_id"], {"vpn_username": vpn_username})
        return vpn_username
    
    except Exception as e:
        print(f"Error creating VPN user: {e}")
        return None


def get_user_subscription_info(vpn_username: str) -> Optional[dict]:
    """Get VPN user subscription info"""
    user = vpn_db.get_user(vpn_username)
    if not user:
        return None
    
    traffic_used = user.get("download_bytes", 0) + user.get("upload_bytes", 0)
    expiration_days = user.get("expiration_days", 0)
    
    return {
        "username": vpn_username,
        "password": user.get("password"),
        "traffic_used_gb": round(traffic_used / 1073741824, 2),
        "expiration_days": expiration_days,
        "status": user.get("status", "Unknown"),
    }


def get_subscription_url(vpn_username: str) -> Optional[str]:
    """Get subscription URL for user (https:// format for apps)"""
    try:
        # Get user from database
        user = vpn_db.get_user(vpn_username)
        if not user:
            print(f"User {vpn_username} not found in database")
            return None
        
        # Load normalsub config
        normalsub_env = "/etc/hysteria/core/scripts/normalsub/.env"
        env_vars = {}
        
        if os.path.exists(normalsub_env):
            with open(normalsub_env, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        env_vars[key] = value
        
        domain = env_vars.get("HYSTERIA_DOMAIN", "")
        port = env_vars.get("HYSTERIA_PORT", "")
        subpath = env_vars.get("SUBPATH", "")
        
        if not domain or not port:
            print("Normal-SUB not configured")
            return None
        
        # Get sub name from main config
        config_env = "/etc/hysteria/.configs.env"
        sub_name = "Iridium"
        
        if os.path.exists(config_env):
            with open(config_env, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        if key == "SUB_NAME":
                            sub_name = value
        
        # Build subscription URL
        auth_password = user["password"]
        url = f"https://{domain}:{port}/{subpath}/{auth_password}"
        
        return url
    except Exception as e:
        print(f"Error getting subscription URL: {e}")
        import traceback
        traceback.print_exc()
        return None


def format_days(days: int) -> str:
    """Format days to human readable string"""
    if days >= 36500:
        return "навсегда ♾️"
    elif days >= 365:
        years = days // 365
        return f"{years} год" if years == 1 else f"{years} года"
    elif days >= 30:
        months = days // 30
        if months == 1:
            return "1 месяц"
        elif months < 5:
            return f"{months} месяца"
        else:
            return f"{months} месяцев"
    else:
        return f"{days} дней"


# ==================== MENU CONTENT ====================

def get_main_menu_text(customer: dict) -> tuple:
    """
    Get main menu text based on subscription status.
    Returns (text, has_subscription, sub_url, vpn_username)
    """
    vpn_username = customer.get("vpn_username")
    
    if not vpn_username:
        # No subscription - show welcome text
        text = (
            "┏━━━━━━━━━━━━━━━━━━━━┓\n"
            "┃    🌐 *IRIDIUM VPN*    ┃\n"
            "┗━━━━━━━━━━━━━━━━━━━━┛\n\n"
            "⚡ Быстрый и безопасный VPN\n"
            "🔒 На базе протокола Hysteria2\n"
            "🌍 Без ограничений по трафику\n\n"
            "─────────────────────\n"
            "Выберите действие ниже 👇"
        )
        return text, False, None, None
    
    # Has subscription - show profile with link
    info = get_user_subscription_info(vpn_username)
    if not info:
        text = (
            "┏━━━━━━━━━━━━━━━━━━━━┓\n"
            "┃    🌐 *IRIDIUM VPN*    ┃\n"
            "┗━━━━━━━━━━━━━━━━━━━━┛\n\n"
            "❌ Ошибка получения информации.\n"
            "Обратитесь в поддержку."
        )
        return text, False, None, None
    
    # Get subscription URL
    sub_url = get_subscription_url(vpn_username)
    
    # Check if subscription expired
    days_left = info['expiration_days']
    if days_left <= 0:
        status_emoji = "🔴"
        status_text = "Подписка истекла"
        days_text = "Продлите для восстановления доступа"
    elif days_left <= 3:
        status_emoji = "🟡"
        status_text = "Скоро истекает"
        days_text = f"Осталось: *{format_days(days_left)}*"
    else:
        status_emoji = "🟢"
        status_text = "Активна"
        days_text = f"Осталось: *{format_days(days_left)}*"
    
    link_text = f"\n📋 *Ссылка подписки:*\n`{sub_url}`" if sub_url else "\n❌ Ссылка недоступна"
    
    text = (
        f"┏━━━━━━━━━━━━━━━━━━━━┓\n"
        f"┃    🌐 *IRIDIUM VPN*    ┃\n"
        f"┗━━━━━━━━━━━━━━━━━━━━┛\n\n"
        f"{status_emoji} Статус: *{status_text}*\n"
        f"⏰ {days_text}\n"
        f"─────────────────────"
        f"{link_text}"
    )
    
    return text, True, sub_url, vpn_username


def get_tariffs_text(customer):
    """Get tariffs selection text"""
    tariffs = shop_db.get_active_tariffs()
    if not tariffs:
        return "😔 Нет доступных тарифов.", None
    
    # Check if extending or buying new
    has_sub = customer.get("vpn_username") is not None
    
    if has_sub:
        text = (
            "┏━━━━━━━━━━━━━━━━━━━━┓\n"
            "┃   🔄 *ПРОДЛЕНИЕ*      ┃\n"
            "┗━━━━━━━━━━━━━━━━━━━━┛\n\n"
            "Дни добавятся к текущей подписке\n"
            "─────────────────────\n"
        )
    else:
        text = (
            "┏━━━━━━━━━━━━━━━━━━━━┓\n"
            "┃    🛒 *ТАРИФЫ*         ┃\n"
            "┗━━━━━━━━━━━━━━━━━━━━┛\n\n"
            "Выберите подходящий тариф\n"
            "─────────────────────\n"
        )
    
    for t in tariffs:
        days = t.get("days", 30)
        period = format_days(days)
        stars = get_tariff_stars(t)
        text += f"▸ *{t['name']}* — {period} — {stars}⭐\n"
    
    if not customer.get("trial_used"):
        trial_days = int(CONFIG.get("TRIAL_DAYS", 3))
        text += f"\n─────────────────────\n🎁 Пробный период: {trial_days} дня бесплатно!"
    
    return text, tariffs


def get_support_text(vpn_username: str = None):
    """Get support page text with user login info"""
    login_info = ""
    if vpn_username:
        login_info = (
            f"\n─────────────────────\n"
            f"🔑 *Ваш логин:* `{vpn_username}`\n"
            f"_Укажите при обращении в поддержку_"
        )
    
    return (
        "┏━━━━━━━━━━━━━━━━━━━━┓\n"
        "┃    💬 *ПОДДЕРЖКА*     ┃\n"
        "┗━━━━━━━━━━━━━━━━━━━━┛\n\n"
        "Возникли вопросы или проблемы?\n"
        "Мы всегда готовы помочь!"
        f"{login_info}"
    )


# ==================== MESSAGE HANDLERS ====================

@bot.message_handler(commands=['start'])
def start_handler(message):
    """Handle /start command - send main menu"""
    customer = get_or_create_customer(message)
    text, has_subscription, sub_url, vpn_username = get_main_menu_text(customer)
    
    bot.send_message(
        message.chat.id,
        text,
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard(has_subscription=has_subscription, sub_url=sub_url)
    )


@bot.message_handler(func=lambda m: m.from_user.id in waiting_for_promo)
def promo_text_handler(message):
    """Handle promo code text input"""
    user_id = message.from_user.id
    msg_id = waiting_for_promo.pop(user_id, None)
    
    code = message.text.strip().upper()
    customer = get_or_create_customer(message)
    telegram_id = customer["telegram_id"]
    telegram_username = customer.get("telegram_username")
    
    # Delete user's message
    try:
        bot.delete_message(message.chat.id, message.message_id)
    except:
        pass
    
    # Validate promo
    is_valid, msg, promo = shop_db.validate_promo(code, telegram_id, telegram_username)
    
    if not is_valid:
        text = f"❌ {msg}"
        try:
            bot.edit_message_text(
                text, message.chat.id, msg_id,
                reply_markup=promo_result_keyboard(success=False)
            )
        except:
            bot.send_message(message.chat.id, text, reply_markup=back_to_main_keyboard())
        return
    
    # Process promo by type
    result_text = process_promo(customer, code, promo)
    
    try:
        bot.edit_message_text(
            result_text, message.chat.id, msg_id,
            parse_mode="Markdown",
            reply_markup=promo_result_keyboard(success=True)
        )
    except:
        bot.send_message(message.chat.id, result_text, parse_mode="Markdown", reply_markup=back_to_main_keyboard())


def process_promo(customer, code, promo):
    """Process validated promo code and return result text"""
    telegram_id = customer["telegram_id"]
    
    if promo["type"] == "lifetime":
        max_ips = promo.get("max_ips")
        vpn_username = create_or_extend_subscription(customer, 36500, max_ips)
        
        if vpn_username:
            shop_db.use_promo(code, telegram_id)
            ips_text = f"📱 Лимит устройств: {max_ips}\n" if max_ips else ""
            return (
                f"✅ *Промокод активирован!*\n\n"
                f"🎁 Подписка навсегда! ♾️\n"
                f"{ips_text}\n"
                f"Вернитесь в главное меню для просмотра ссылки."
            )
        return "❌ Ошибка активации промокода"
    
    elif promo["type"] == "free_period":
        days = int(promo["value"])
        max_ips = promo.get("max_ips")
        vpn_username = create_or_extend_subscription(customer, days, max_ips)
        
        if vpn_username:
            shop_db.use_promo(code, telegram_id)
            info = get_user_subscription_info(vpn_username)
            ips_text = f"📱 Лимит устройств: {max_ips}\n" if max_ips else ""
            return (
                f"✅ *Промокод активирован!*\n\n"
                f"🎁 +{days} дней подписки\n"
                f"⏰ Всего осталось: {info['expiration_days']} дней\n"
                f"{ips_text}\n"
                f"Вернитесь в главное меню для просмотра ссылки."
            )
        return "❌ Ошибка активации промокода"
    
    elif promo["type"] == "discount":
        shop_db.update_customer(telegram_id, {"pending_promo": code})
        return (
            f"✅ *Промокод сохранён!*\n\n"
            f"🎁 Скидка {int(promo['value'])}%\n"
            f"Промокод будет применён при покупке."
        )
    
    return "❌ Неизвестный тип промокода"


# ==================== CALLBACK HANDLERS ====================

@bot.callback_query_handler(func=lambda call: call.data.startswith("menu:"))
def menu_callback(call):
    """Handle menu navigation"""
    action = call.data.split(":")[1]
    customer = get_or_create_customer_by_id(call.from_user.id, call.from_user.username)
    
    if action == "main" or action == "refresh":
        text, has_subscription, sub_url, vpn_username = get_main_menu_text(customer)
        bot.edit_message_text(
            text,
            call.message.chat.id, call.message.message_id,
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard(has_subscription=has_subscription, sub_url=sub_url)
        )
        if action == "refresh":
            bot.answer_callback_query(call.id, "✅ Информация обновлена")
            return
    
    elif action == "buy":
        text, tariffs = get_tariffs_text(customer)
        if tariffs:
            bot.edit_message_text(
                text, call.message.chat.id, call.message.message_id,
                parse_mode="Markdown",
                reply_markup=tariffs_keyboard(tariffs, show_trial=not customer.get("trial_used"))
            )
        else:
            bot.edit_message_text(
                text, call.message.chat.id, call.message.message_id,
                reply_markup=back_to_main_keyboard()
            )
    
    elif action == "promo":
        waiting_for_promo[call.from_user.id] = call.message.message_id
        text = (
            "┏━━━━━━━━━━━━━━━━━━━━┓\n"
            "┃    🎁 *ПРОМОКОД*      ┃\n"
            "┗━━━━━━━━━━━━━━━━━━━━┛\n\n"
            "Отправьте промокод сообщением 👇"
        )
        bot.edit_message_text(
            text,
            call.message.chat.id, call.message.message_id,
            parse_mode="Markdown",
            reply_markup=promo_keyboard()
        )
    
    elif action == "support":
        vpn_username = customer.get("vpn_username")
        bot.edit_message_text(
            get_support_text(vpn_username),
            call.message.chat.id, call.message.message_id,
            parse_mode="Markdown",
            reply_markup=support_keyboard(CONFIG.get("SUPPORT_USERNAME"))
        )
    
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda call: call.data == "trial")
def trial_callback(call):
    """Handle trial selection"""
    customer = get_or_create_customer_by_id(call.from_user.id, call.from_user.username)
    
    if customer.get("trial_used"):
        bot.answer_callback_query(call.id, "❌ Пробный период уже использован", show_alert=True)
        return
    
    trial_days = int(CONFIG.get("TRIAL_DAYS", 3))
    
    text = (
        "┏━━━━━━━━━━━━━━━━━━━━┓\n"
        "┃   🎁 *ПРОБНЫЙ ПЕРИОД* ┃\n"
        "┗━━━━━━━━━━━━━━━━━━━━┛\n\n"
        f"⏰ Срок: *{trial_days} дня*\n"
        "📊 Трафик: *Безлимит*\n"
        "💰 Цена: *Бесплатно*\n"
        "─────────────────────\n"
        "Активировать пробный период?"
    )
    
    bot.edit_message_text(
        text, call.message.chat.id, call.message.message_id,
        parse_mode="Markdown",
        reply_markup=confirm_trial_keyboard()
    )
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda call: call.data.startswith("trial:"))
def trial_action_callback(call):
    """Handle trial confirmation"""
    action = call.data.split(":")[1]
    
    if action != "confirm":
        bot.answer_callback_query(call.id)
        return
    
    customer = get_or_create_customer_by_id(call.from_user.id, call.from_user.username)
    
    if customer.get("trial_used"):
        bot.answer_callback_query(call.id, "❌ Пробный период уже использован", show_alert=True)
        return
    
    trial_days = int(CONFIG.get("TRIAL_DAYS", 3))
    vpn_username = create_or_extend_subscription(customer, trial_days)
    
    if not vpn_username:
        bot.answer_callback_query(call.id, "❌ Ошибка активации", show_alert=True)
        return
    
    shop_db.mark_trial_used(customer["telegram_id"])
    
    # Refresh customer to get updated vpn_username
    customer = get_or_create_customer_by_id(call.from_user.id, call.from_user.username)
    
    text = (
        f"✅ *Пробный период активирован!*\n\n"
        f"⏰ Срок: {trial_days} дня\n"
        f"📊 Трафик: Безлимит\n\n"
        f"Вернитесь в главное меню для просмотра ссылки."
    )
    
    bot.edit_message_text(
        text, call.message.chat.id, call.message.message_id,
        parse_mode="Markdown",
        reply_markup=back_to_main_keyboard()
    )
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda call: call.data.startswith("tariff:"))
def tariff_select_callback(call):
    """Handle tariff selection"""
    tariff_id = call.data.split(":")[1]
    tariff = shop_db.get_tariff(tariff_id)
    
    if not tariff:
        bot.answer_callback_query(call.id, "Тариф не найден", show_alert=True)
        return
    
    customer = get_or_create_customer_by_id(call.from_user.id, call.from_user.username)
    
    base_price = get_tariff_stars(tariff)
    final_price = base_price
    promo_text = ""
    
    promo_code = customer.get("pending_promo")
    if promo_code:
        is_valid, msg, promo = shop_db.validate_promo(
            promo_code, customer["telegram_id"], customer.get("telegram_username"), tariff_id
        )
        if is_valid and promo["type"] == "discount":
            discount = int(promo["value"])
            final_price = int(base_price * (100 - discount) / 100)
            promo_text = f"🎁 Скидка {discount}%: -{base_price - final_price}⭐\n"
    
    period = format_days(tariff.get("days", 30))
    
    text = (
        "┏━━━━━━━━━━━━━━━━━━━━┓\n"
        "┃    🛒 *ОПЛАТА*         ┃\n"
        "┗━━━━━━━━━━━━━━━━━━━━┛\n\n"
        f"📋 Тариф: *{tariff['name']}*\n"
        f"📅 Срок: *{period}*\n"
        f"{promo_text}"
        "─────────────────────\n"
        f"💰 К оплате: *{final_price}⭐*\n\n"
        "Подтвердить оплату?"
    )
    
    bot.edit_message_text(
        text, call.message.chat.id, call.message.message_id,
        parse_mode="Markdown",
        reply_markup=tariff_detail_keyboard(tariff_id, final_price)
    )
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda call: call.data.startswith("pay:"))
def payment_callback(call):
    """Handle payment"""
    tariff_id = call.data.split(":")[1]
    
    tariff = shop_db.get_tariff(tariff_id)
    if not tariff:
        bot.answer_callback_query(call.id, "Тариф не найден", show_alert=True)
        return
    
    if not tariff.get("price_rub"):
        bot.answer_callback_query(call.id, "❌ Тариф не настроен", show_alert=True)
        return
    
    customer = get_or_create_customer_by_id(call.from_user.id, call.from_user.username)
    
    base_price = get_tariff_stars(tariff)
    final_price = base_price
    promo_code = customer.get("pending_promo")
    
    if promo_code:
        is_valid, msg, promo = shop_db.validate_promo(
            promo_code, customer["telegram_id"], customer.get("telegram_username"), tariff_id
        )
        if is_valid and promo["type"] == "discount":
            discount = int(promo["value"])
            final_price = int(base_price * (100 - discount) / 100)
    
    payment = shop_db.create_payment(
        customer_id=customer["telegram_id"],
        tariff_id=tariff_id,
        amount=final_price,
        payment_method="stars",
        promo_code=promo_code
    )
    
    success = payment_manager.create_stars_invoice(
        bot=bot,
        chat_id=call.message.chat.id,
        title=f"Подписка: {tariff['name']}",
        description=f"Iridium VPN - {tariff['name']} ({format_days(tariff.get('days', 30))})",
        payload=f"{payment['_id']}:{tariff_id}",
        amount=final_price
    )
    
    if not success:
        bot.answer_callback_query(call.id, "❌ Ошибка создания платежа", show_alert=True)
    else:
        bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda call: call.data.startswith("support:"))
def support_action_callback(call):
    """Handle support actions"""
    action = call.data.split(":")[1]
    
    if action == "faq":
        text = (
            "┏━━━━━━━━━━━━━━━━━━━━┓\n"
            "┃   📖 *ИНСТРУКЦИЯ*     ┃\n"
            "┗━━━━━━━━━━━━━━━━━━━━┛\n\n"
            "*Как подключиться?*\n"
            "1️⃣ Скачайте приложение\n"
            "2️⃣ Скопируйте ссылку из главного меню\n"
            "3️⃣ Добавьте профиль в приложение\n"
            "4️⃣ Нажмите «Подключиться»\n"
            "─────────────────────\n"
            "*📱 Приложения:*\n"
            "• iOS: Streisand, Shadowrocket\n"
            "• Android: Hiddify, NekoBox\n"
            "• Windows/Mac: Hiddify\n"
            "─────────────────────\n"
            "*❓ Не работает VPN?*\n"
            "Переподключитесь или напишите в поддержку"
        )
        
        bot.edit_message_text(
            text, call.message.chat.id, call.message.message_id,
            parse_mode="Markdown",
            reply_markup=faq_keyboard()
        )
    
    bot.answer_callback_query(call.id)


# ==================== PAYMENT HANDLERS ====================

@bot.pre_checkout_query_handler(func=lambda query: True)
def pre_checkout_handler(pre_checkout_query):
    """Handle pre-checkout query"""
    bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)


@bot.message_handler(content_types=['successful_payment'])
def successful_payment_handler(message):
    """Handle successful payment"""
    payment_info = message.successful_payment
    payload = payment_info.invoice_payload
    
    try:
        payment_id, tariff_id = payload.split(":")
    except:
        bot.send_message(message.chat.id, "❌ Ошибка обработки платежа")
        return
    
    from bson.objectid import ObjectId
    payment = shop_db.get_payment(ObjectId(payment_id))
    
    if not payment:
        bot.send_message(message.chat.id, "❌ Платёж не найден")
        return
    
    telegram_id = payment["customer_id"]
    shop_db.complete_payment(payment["_id"], payment_info.telegram_payment_charge_id)
    
    customer = shop_db.get_customer(telegram_id)
    tariff = shop_db.get_tariff(payment["tariff_id"])
    
    if not customer or not tariff:
        bot.send_message(message.chat.id, "❌ Ошибка обработки платежа")
        return
    
    # Handle promo
    extra_days = 0
    promo_code = payment.get("promo_code")
    
    if promo_code:
        is_valid, _, promo = shop_db.validate_promo(
            promo_code, telegram_id, customer.get("telegram_username")
        )
        if is_valid:
            shop_db.use_promo(promo_code, telegram_id)
            shop_db.update_customer(telegram_id, {"pending_promo": None})
            if promo["type"] == "free_period":
                extra_days = int(promo["value"])
    
    days = tariff.get("days", 30) + extra_days
    vpn_username = create_or_extend_subscription(customer, days)
    
    if not vpn_username:
        bot.send_message(message.chat.id, "❌ Ошибка создания подписки")
        return
    
    extra_text = f"\n🎁 +{extra_days} дней по промокоду!" if extra_days > 0 else ""
    
    text = (
        f"✅ *Оплата прошла успешно!*\n\n"
        f"📅 Тариф: {tariff['name']}\n"
        f"⏰ Срок: {format_days(days)}{extra_text}\n\n"
        f"Вернитесь в главное меню для просмотра ссылки."
    )
    
    bot.send_message(
        message.chat.id, text,
        parse_mode="Markdown",
        reply_markup=back_to_main_keyboard()
    )


# ==================== RUN ====================

def run():
    """Run the bot"""
    if not bot:
        print("Error: BOT_TOKEN not configured")
        return
    
    print("Client bot starting...")
    bot.infinity_polling()


if __name__ == "__main__":
    run()
