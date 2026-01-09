#!/usr/bin/env python3
"""
Iridium Client Bot
Telegram bot for customers to purchase VPN subscriptions
"""

import os
import sys
import json
import qrcode
import io
import secrets
import string
from datetime import datetime, timedelta
from typing import Optional

import telebot
from telebot import types

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.shop_database import shop_db
from db.database import db as vpn_db
from clientbot.utils.keyboards import (
    main_menu_keyboard, tariff_type_keyboard, tariffs_keyboard,
    payment_method_keyboard, confirm_trial_keyboard, back_keyboard,
    profile_keyboard, support_keyboard, cancel_keyboard
)
from clientbot.utils.payment import PaymentManager


# ==================== CONFIGURATION ====================

def load_config():
    """Load bot configuration from environment file"""
    config_path = "/etc/hysteria/.clientbot.env"
    config = {
        "BOT_TOKEN": None,
        "YOOKASSA_SHOP_ID": None,
        "YOOKASSA_SECRET_KEY": None,
        "SUPPORT_USERNAME": None,
        "RETURN_URL": "https://t.me",  # Default return URL after payment
        "TRIAL_DAYS": 3,
        "TRIAL_TRAFFIC_GB": 999999,  # Essentially unlimited
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
payment_manager = PaymentManager(
    CONFIG.get("YOOKASSA_SHOP_ID"),
    CONFIG.get("YOOKASSA_SECRET_KEY")
)


# ==================== HELPERS ====================

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


def create_vpn_user(customer: dict, tariff: dict, extra_days: int = 0, extra_traffic_gb: int = 0) -> Optional[str]:
    """
    Create or update VPN user for customer
    Returns VPN username or None on error
    """
    vpn_username = customer.get("vpn_username") or generate_vpn_username(customer["telegram_id"])
    password = generate_vpn_password()
    
    # Calculate traffic and expiration based on tariff type
    if tariff["type"] == "traffic":
        traffic_gb = tariff["traffic_gb"] + extra_traffic_gb
        expiration_days = 36500  # ~100 years = unlimited
    elif tariff["type"] == "time":
        traffic_gb = 999999  # Essentially unlimited
        expiration_days = tariff["days"] + extra_days
    else:  # trial
        traffic_gb = int(CONFIG.get("TRIAL_TRAFFIC_GB", 999999))
        expiration_days = int(CONFIG.get("TRIAL_DAYS", 3))
    
    try:
        # Check if user already exists
        existing = vpn_db.get_user(vpn_username)
        
        if existing:
            # Update existing user - extend subscription
            if tariff["type"] == "traffic":
                # Add traffic
                new_traffic = existing.get("max_download_bytes", 0) + (traffic_gb * 1073741824)
                vpn_db.update_user(vpn_username, {"max_download_bytes": new_traffic})
            else:
                # Extend time
                current_days = existing.get("expiration_days", 0)
                vpn_db.update_user(vpn_username, {"expiration_days": current_days + expiration_days})
        else:
            # Create new user
            user_data = {
                "username": vpn_username,
                "password": password,
                "max_download_bytes": traffic_gb * 1073741824,
                "expiration_days": expiration_days,
                "blocked": False,
                "status": "Active",
                "account_creation_date": datetime.now().strftime("%Y-%m-%d")
            }
            vpn_db.add_user(user_data)
        
        # Update customer with VPN username
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
    traffic_limit = user.get("max_download_bytes", 0)
    expiration_days = user.get("expiration_days", 0)
    
    # Calculate remaining
    traffic_remaining = max(0, traffic_limit - traffic_used)
    
    return {
        "username": vpn_username,
        "password": user.get("password"),
        "traffic_used_gb": round(traffic_used / 1073741824, 2),
        "traffic_limit_gb": round(traffic_limit / 1073741824, 2),
        "traffic_remaining_gb": round(traffic_remaining / 1073741824, 2),
        "expiration_days": expiration_days,
        "status": user.get("status", "Unknown"),
        "is_unlimited_traffic": traffic_limit > 900000 * 1073741824,  # > 900TB
        "is_unlimited_time": expiration_days > 36000  # > 100 years
    }


def get_subscription_link(vpn_username: str) -> Optional[str]:
    """Get subscription link for user"""
    try:
        from hysteria2.show_user_uri import get_user_uri
        uri = get_user_uri(vpn_username)
        return uri
    except:
        # Fallback - read from config
        return None


# ==================== MESSAGE HANDLERS ====================

@bot.message_handler(commands=['start'])
def start_handler(message):
    """Handle /start command"""
    customer = get_or_create_customer(message)
    
    welcome_text = (
        "👋 *Добро пожаловать в Iridium VPN!*\n\n"
        "🚀 Быстрый и безопасный VPN на базе Hysteria2\n\n"
        "Выберите действие:"
    )
    
    bot.send_message(
        message.chat.id,
        welcome_text,
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard()
    )


@bot.message_handler(func=lambda m: m.text == "🛒 Купить подписку")
def buy_subscription_handler(message):
    """Show tariff types"""
    customer = get_or_create_customer(message)
    
    text = (
        "🛒 *Выберите тип подписки:*\n\n"
        "📦 *По трафику* — платите за объём, пользуйтесь когда угодно\n"
        "📅 *По времени* — безлимитный трафик на определённый срок\n"
        "🎁 *Пробный период* — 3 дня бесплатно для новых пользователей"
    )
    
    # Check if trial available
    if customer.get("trial_used"):
        text = (
            "🛒 *Выберите тип подписки:*\n\n"
            "📦 *По трафику* — платите за объём, пользуйтесь когда угодно\n"
            "📅 *По времени* — безлимитный трафик на определённый срок"
        )
    
    markup = tariff_type_keyboard()
    if customer.get("trial_used"):
        # Remove trial button
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("📦 По трафику (безлимит времени)", callback_data="tariff_type:traffic"),
            types.InlineKeyboardButton("📅 По времени (безлимит трафика)", callback_data="tariff_type:time")
        )
    
    bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=markup)


@bot.message_handler(func=lambda m: m.text == "👤 Мой профиль")
def profile_handler(message):
    """Show user profile"""
    customer = get_or_create_customer(message)
    
    if not customer.get("vpn_username"):
        text = (
            "👤 *Ваш профиль*\n\n"
            "У вас пока нет активной подписки.\n"
            "Купите подписку или активируйте пробный период!"
        )
        bot.send_message(
            message.chat.id, text,
            parse_mode="Markdown",
            reply_markup=profile_keyboard(has_subscription=False)
        )
        return
    
    info = get_user_subscription_info(customer["vpn_username"])
    if not info:
        text = "❌ Ошибка получения информации о подписке"
        bot.send_message(message.chat.id, text)
        return
    
    # Format subscription info
    if info["is_unlimited_traffic"]:
        traffic_text = "♾️ Безлимит"
    else:
        traffic_text = f"{info['traffic_remaining_gb']} / {info['traffic_limit_gb']} GB"
    
    if info["is_unlimited_time"]:
        time_text = "♾️ Безлимит"
    else:
        time_text = f"{info['expiration_days']} дней"
    
    text = (
        f"👤 *Ваш профиль*\n\n"
        f"🔑 Логин: `{info['username']}`\n"
        f"📊 Трафик: {traffic_text}\n"
        f"⏰ Осталось: {time_text}\n"
        f"📶 Статус: {info['status']}"
    )
    
    bot.send_message(
        message.chat.id, text,
        parse_mode="Markdown",
        reply_markup=profile_keyboard(has_subscription=True)
    )


@bot.message_handler(func=lambda m: m.text == "📊 Статистика")
def stats_handler(message):
    """Show usage statistics"""
    customer = get_or_create_customer(message)
    
    if not customer.get("vpn_username"):
        bot.send_message(message.chat.id, "У вас нет активной подписки.")
        return
    
    info = get_user_subscription_info(customer["vpn_username"])
    if not info:
        bot.send_message(message.chat.id, "❌ Ошибка получения статистики")
        return
    
    text = (
        f"📊 *Статистика использования*\n\n"
        f"📥 Использовано: {info['traffic_used_gb']} GB\n"
        f"📦 Лимит: {info['traffic_limit_gb'] if not info['is_unlimited_traffic'] else '♾️'} GB\n"
        f"📈 Осталось: {info['traffic_remaining_gb'] if not info['is_unlimited_traffic'] else '♾️'} GB"
    )
    
    bot.send_message(message.chat.id, text, parse_mode="Markdown")


@bot.message_handler(func=lambda m: m.text == "🎁 Ввести промокод")
def promo_input_handler(message):
    """Handle promo code input"""
    text = "🎁 Введите промокод:"
    bot.send_message(message.chat.id, text, reply_markup=cancel_keyboard())
    bot.register_next_step_handler(message, process_promo_code)


def process_promo_code(message):
    """Process entered promo code"""
    if message.text == "❌ Отмена":
        bot.send_message(message.chat.id, "Отменено", reply_markup=main_menu_keyboard())
        return
    
    code = message.text.strip().upper()
    is_valid, msg, promo = shop_db.validate_promo(code)
    
    if not is_valid:
        bot.send_message(
            message.chat.id,
            f"❌ {msg}",
            reply_markup=main_menu_keyboard()
        )
        return
    
    # Show promo info
    promo_type_text = {
        "discount": f"Скидка {promo['value']}%",
        "free_period": f"+{promo['value']} дней бесплатно",
        "extra_traffic": f"+{promo['value']} GB трафика"
    }.get(promo["type"], "Бонус")
    
    text = (
        f"✅ *Промокод активен!*\n\n"
        f"🎁 {promo_type_text}\n"
        f"📝 {promo.get('description', '')}\n\n"
        f"Промокод будет применён при покупке."
    )
    
    # Store promo in user session (temporary)
    # In production, you'd want to store this in database or cache
    bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=main_menu_keyboard())


@bot.message_handler(func=lambda m: m.text == "💬 Поддержка")
def support_handler(message):
    """Show support info"""
    support_username = CONFIG.get("SUPPORT_USERNAME")
    
    text = (
        "💬 *Поддержка*\n\n"
        "Если у вас возникли вопросы или проблемы, "
        "свяжитесь с нашей поддержкой."
    )
    
    bot.send_message(
        message.chat.id, text,
        parse_mode="Markdown",
        reply_markup=support_keyboard(support_username)
    )


# ==================== CALLBACK HANDLERS ====================

@bot.callback_query_handler(func=lambda call: call.data.startswith("tariff_type:"))
def tariff_type_callback(call):
    """Handle tariff type selection"""
    tariff_type = call.data.split(":")[1]
    customer = shop_db.get_customer(call.from_user.id)
    
    if tariff_type == "trial":
        # Check if trial already used
        if customer and customer.get("trial_used"):
            bot.answer_callback_query(call.id, "❌ Пробный период уже использован", show_alert=True)
            return
        
        text = (
            f"🎁 *Пробный период*\n\n"
            f"⏰ Срок: {CONFIG.get('TRIAL_DAYS', 3)} дня\n"
            f"📊 Трафик: Безлимит\n"
            f"💰 Цена: Бесплатно\n\n"
            f"Активировать пробный период?"
        )
        
        bot.edit_message_text(
            text, call.message.chat.id, call.message.message_id,
            parse_mode="Markdown",
            reply_markup=confirm_trial_keyboard()
        )
        return
    
    # Get tariffs of selected type
    tariffs = shop_db.get_active_tariffs(tariff_type)
    
    if not tariffs:
        bot.answer_callback_query(call.id, "Нет доступных тарифов", show_alert=True)
        return
    
    type_name = "по трафику" if tariff_type == "traffic" else "по времени"
    text = f"📋 *Тарифы {type_name}:*\n\nВыберите подходящий тариф:"
    
    bot.edit_message_text(
        text, call.message.chat.id, call.message.message_id,
        parse_mode="Markdown",
        reply_markup=tariffs_keyboard(tariffs, tariff_type)
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("tariff:"))
def tariff_select_callback(call):
    """Handle tariff selection"""
    tariff_id = call.data.split(":")[1]
    tariff = shop_db.get_tariff(tariff_id)
    
    if not tariff:
        bot.answer_callback_query(call.id, "Тариф не найден", show_alert=True)
        return
    
    # Format tariff description
    if tariff["type"] == "traffic":
        desc = f"📦 {tariff['traffic_gb']} GB (безлимит времени)"
    else:
        days = tariff.get('days', 30)
        if days >= 365:
            period = f"{days // 365} год" if days // 365 == 1 else f"{days // 365} года"
        elif days >= 30:
            period = f"{days // 30} мес."
        else:
            period = f"{days} дн."
        desc = f"📅 {period} (безлимит трафика)"
    
    text = (
        f"🛒 *Оформление подписки*\n\n"
        f"📋 Тариф: {tariff['name']}\n"
        f"📦 {desc}\n"
        f"💰 Цена: {tariff['price']}₽"
    )
    
    if tariff.get('price_stars'):
        text += f" / {tariff['price_stars']}⭐"
    
    text += "\n\nВыберите способ оплаты:"
    
    bot.edit_message_text(
        text, call.message.chat.id, call.message.message_id,
        parse_mode="Markdown",
        reply_markup=payment_method_keyboard(
            tariff_id, tariff["price"], tariff.get("price_stars")
        )
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("trial:"))
def trial_callback(call):
    """Handle trial activation"""
    action = call.data.split(":")[1]
    
    if action == "cancel":
        bot.edit_message_text(
            "Отменено",
            call.message.chat.id, call.message.message_id
        )
        return
    
    customer = shop_db.get_customer(call.from_user.id)
    if not customer:
        customer = shop_db.create_customer(call.from_user.id, call.from_user.username)
    
    if customer.get("trial_used"):
        bot.answer_callback_query(call.id, "❌ Пробный период уже использован", show_alert=True)
        return
    
    # Create trial tariff data
    trial_tariff = {
        "type": "trial",
        "traffic_gb": int(CONFIG.get("TRIAL_TRAFFIC_GB", 999999)),
        "days": int(CONFIG.get("TRIAL_DAYS", 3))
    }
    
    # Create VPN user
    vpn_username = create_vpn_user(customer, trial_tariff)
    
    if not vpn_username:
        bot.edit_message_text(
            "❌ Ошибка активации. Попробуйте позже.",
            call.message.chat.id, call.message.message_id
        )
        return
    
    # Mark trial as used
    shop_db.mark_trial_used(customer["telegram_id"])
    
    # Get subscription info
    info = get_user_subscription_info(vpn_username)
    
    text = (
        f"✅ *Пробный период активирован!*\n\n"
        f"🔑 Логин: `{vpn_username}`\n"
        f"⏰ Срок: {CONFIG.get('TRIAL_DAYS', 3)} дня\n"
        f"📊 Трафик: Безлимит\n\n"
        f"Перейдите в «👤 Мой профиль» для получения ссылки подключения."
    )
    
    bot.edit_message_text(
        text, call.message.chat.id, call.message.message_id,
        parse_mode="Markdown"
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("pay:"))
def payment_callback(call):
    """Handle payment method selection"""
    parts = call.data.split(":")
    method = parts[1]  # stars or yookassa
    tariff_id = parts[2]
    
    tariff = shop_db.get_tariff(tariff_id)
    if not tariff:
        bot.answer_callback_query(call.id, "Тариф не найден", show_alert=True)
        return
    
    customer = shop_db.get_customer(call.from_user.id)
    if not customer:
        customer = shop_db.create_customer(call.from_user.id, call.from_user.username)
    
    # Create payment record
    payment = shop_db.create_payment(
        customer_id=customer["telegram_id"],
        tariff_id=tariff_id,
        amount=tariff["price"],
        payment_method=method
    )
    
    if method == "stars":
        # Create Telegram Stars invoice
        success = payment_manager.create_stars_invoice(
            bot=bot,
            chat_id=call.message.chat.id,
            title=f"Подписка: {tariff['name']}",
            description=f"Iridium VPN - {tariff['name']}",
            payload=f"{payment['_id']}:{tariff_id}",
            amount=tariff["price_stars"]
        )
        
        if not success:
            bot.answer_callback_query(call.id, "❌ Ошибка создания платежа", show_alert=True)
            return
        
        bot.answer_callback_query(call.id)
        
    elif method == "yookassa":
        # Create YooKassa payment
        payment_data = payment_manager.create_yookassa_payment(
            amount=tariff["price"],
            description=f"Iridium VPN - {tariff['name']}",
            return_url=CONFIG.get("RETURN_URL", "https://t.me"),
            metadata={
                "payment_id": str(payment["_id"]),
                "tariff_id": tariff_id,
                "customer_id": customer["telegram_id"]
            }
        )
        
        if not payment_data:
            bot.answer_callback_query(call.id, "❌ Ошибка создания платежа", show_alert=True)
            return
        
        # Update payment with external ID
        shop_db.update_payment(payment["_id"], {"external_id": payment_data["payment_id"]})
        
        # Send payment link
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton(
            "💳 Перейти к оплате",
            url=payment_data["confirmation_url"]
        ))
        markup.add(types.InlineKeyboardButton(
            "✅ Я оплатил",
            callback_data=f"check_payment:{payment['_id']}"
        ))
        
        text = (
            f"💳 *Оплата через ЮKassa*\n\n"
            f"Сумма: {tariff['price']}₽\n\n"
            f"Нажмите кнопку ниже для оплаты.\n"
            f"После оплаты нажмите «✅ Я оплатил»."
        )
        
        bot.edit_message_text(
            text, call.message.chat.id, call.message.message_id,
            parse_mode="Markdown",
            reply_markup=markup
        )


@bot.callback_query_handler(func=lambda call: call.data.startswith("check_payment:"))
def check_payment_callback(call):
    """Check YooKassa payment status"""
    payment_id = call.data.split(":")[1]
    
    payment = shop_db.get_payment(payment_id)
    if not payment:
        bot.answer_callback_query(call.id, "Платёж не найден", show_alert=True)
        return
    
    if payment["status"] == "completed":
        bot.answer_callback_query(call.id, "✅ Платёж уже обработан", show_alert=True)
        return
    
    # Check with YooKassa
    if payment.get("external_id"):
        if payment_manager.is_payment_successful(payment["external_id"]):
            # Process successful payment
            process_successful_payment(call.message.chat.id, payment)
            bot.answer_callback_query(call.id, "✅ Оплата подтверждена!")
            return
    
    bot.answer_callback_query(call.id, "⏳ Платёж ещё не получен. Попробуйте позже.", show_alert=True)


@bot.callback_query_handler(func=lambda call: call.data.startswith("profile:"))
def profile_action_callback(call):
    """Handle profile actions"""
    action = call.data.split(":")[1]
    customer = shop_db.get_customer(call.from_user.id)
    
    if not customer or not customer.get("vpn_username"):
        bot.answer_callback_query(call.id, "Нет активной подписки", show_alert=True)
        return
    
    if action == "qr":
        # Generate and send QR code
        link = get_subscription_link(customer["vpn_username"])
        if not link:
            bot.answer_callback_query(call.id, "❌ Ошибка получения ссылки", show_alert=True)
            return
        
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(link)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        
        bio = io.BytesIO()
        img.save(bio, 'PNG')
        bio.seek(0)
        
        bot.send_photo(
            call.message.chat.id,
            bio,
            caption="📱 Отсканируйте QR-код в приложении"
        )
        bot.answer_callback_query(call.id)
        
    elif action == "link":
        # Send subscription link
        link = get_subscription_link(customer["vpn_username"])
        if not link:
            bot.answer_callback_query(call.id, "❌ Ошибка получения ссылки", show_alert=True)
            return
        
        bot.send_message(
            call.message.chat.id,
            f"🔗 *Ссылка подключения:*\n\n`{link}`\n\n"
            f"Скопируйте и вставьте в приложение.",
            parse_mode="Markdown"
        )
        bot.answer_callback_query(call.id)
        
    elif action == "renew":
        # Go to buy subscription
        buy_subscription_handler(call.message)
        bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda call: call.data.startswith("back:"))
def back_callback(call):
    """Handle back navigation"""
    destination = call.data.split(":")[1]
    
    if destination == "main":
        bot.edit_message_text(
            "Выберите действие:",
            call.message.chat.id, call.message.message_id,
            reply_markup=None
        )
    elif destination == "tariff_type":
        # Return to tariff type selection
        customer = shop_db.get_customer(call.from_user.id)
        text = "🛒 *Выберите тип подписки:*"
        
        markup = tariff_type_keyboard()
        if customer and customer.get("trial_used"):
            markup = types.InlineKeyboardMarkup(row_width=1)
            markup.add(
                types.InlineKeyboardButton("📦 По трафику", callback_data="tariff_type:traffic"),
                types.InlineKeyboardButton("📅 По времени", callback_data="tariff_type:time")
            )
        
        bot.edit_message_text(
            text, call.message.chat.id, call.message.message_id,
            parse_mode="Markdown",
            reply_markup=markup
        )


# ==================== PAYMENT HANDLERS ====================

@bot.pre_checkout_query_handler(func=lambda query: True)
def pre_checkout_handler(pre_checkout_query):
    """Handle pre-checkout query for Telegram Stars"""
    success, msg = payment_manager.process_stars_payment(pre_checkout_query)
    bot.answer_pre_checkout_query(pre_checkout_query.id, ok=success, error_message=msg if not success else None)


@bot.message_handler(content_types=['successful_payment'])
def successful_payment_handler(message):
    """Handle successful Telegram Stars payment"""
    payment_info = payment_manager.confirm_stars_payment(message.successful_payment)
    
    # Parse payload
    parts = payment_info["payload"].split(":")
    payment_id = parts[0]
    tariff_id = parts[1]
    
    payment = shop_db.get_payment(payment_id)
    if payment:
        process_successful_payment(message.chat.id, payment, payment_info["payment_id"])


def process_successful_payment(chat_id: int, payment: dict, external_id: str = None):
    """Process successful payment and create/extend subscription"""
    # Mark payment as completed
    shop_db.complete_payment(payment["_id"], external_id)
    
    # Use promo if applied
    if payment.get("promo_code"):
        shop_db.use_promo(payment["promo_code"])
    
    # Get customer and tariff
    customer = shop_db.get_customer(payment["customer_id"])
    tariff = shop_db.get_tariff(payment["tariff_id"])
    
    if not customer or not tariff:
        bot.send_message(chat_id, "❌ Ошибка обработки платежа. Свяжитесь с поддержкой.")
        return
    
    # Calculate bonuses from promo
    extra_days = 0
    extra_traffic = 0
    
    if payment.get("promo_code"):
        _, _, promo = shop_db.validate_promo(payment["promo_code"])
        if promo:
            if promo["type"] == "free_period":
                extra_days = int(promo["value"])
            elif promo["type"] == "extra_traffic":
                extra_traffic = int(promo["value"])
    
    # Create or extend VPN subscription
    vpn_username = create_vpn_user(customer, tariff, extra_days, extra_traffic)
    
    if not vpn_username:
        bot.send_message(chat_id, "❌ Ошибка создания подписки. Свяжитесь с поддержкой.")
        return
    
    # Send success message
    info = get_user_subscription_info(vpn_username)
    
    if tariff["type"] == "traffic":
        desc = f"📦 {tariff['traffic_gb']} GB"
        if extra_traffic:
            desc += f" + {extra_traffic} GB (промо)"
    else:
        desc = f"📅 {tariff.get('days', 30)} дней"
        if extra_days:
            desc += f" + {extra_days} дней (промо)"
    
    text = (
        f"✅ *Оплата успешна!*\n\n"
        f"📋 Тариф: {tariff['name']}\n"
        f"{desc}\n\n"
        f"🔑 Логин: `{vpn_username}`\n\n"
        f"Перейдите в «👤 Мой профиль» для получения ссылки подключения."
    )
    
    bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=main_menu_keyboard())


# ==================== MAIN ====================

def main():
    """Run the bot"""
    if not bot:
        print("Error: Bot token not configured")
        print("Please set BOT_TOKEN in /etc/hysteria/.clientbot.env")
        sys.exit(1)
    
    print("🚀 Iridium Client Bot started")
    
    # Initialize default tariffs if none exist
    if shop_db and len(shop_db.get_all_tariffs()) == 0:
        print("Creating default tariffs...")
        # Traffic-based tariffs
        shop_db.create_tariff("50 GB", "traffic", 150, traffic_gb=50, price_stars=75)
        shop_db.create_tariff("100 GB", "traffic", 250, traffic_gb=100, price_stars=125)
        shop_db.create_tariff("300 GB", "traffic", 500, traffic_gb=300, price_stars=250)
        
        # Time-based tariffs
        shop_db.create_tariff("1 месяц", "time", 200, days=30, price_stars=100)
        shop_db.create_tariff("3 месяца", "time", 500, days=90, price_stars=250)
        shop_db.create_tariff("6 месяцев", "time", 900, days=180, price_stars=450)
        shop_db.create_tariff("12 месяцев", "time", 1500, days=365, price_stars=750)
        
        print("Default tariffs created!")
    
    bot.infinity_polling()


if __name__ == "__main__":
    main()

