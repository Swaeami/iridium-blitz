#!/usr/bin/env python3
"""
Iridium Client Bot
Telegram bot for customers to purchase VPN subscriptions
Time-based tariffs only (unlimited traffic)
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
    main_menu_keyboard, tariffs_keyboard,
    payment_keyboard, confirm_trial_keyboard, back_keyboard,
    profile_keyboard, support_keyboard, cancel_keyboard
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


def get_or_create_customer_by_id(telegram_id: int, username: str = None) -> dict:
    """Get existing customer or create new one by telegram_id"""
    customer = shop_db.get_customer(telegram_id)
    if not customer:
        customer = shop_db.create_customer(
            telegram_id=telegram_id,
            telegram_username=username
        )
    return customer


def create_or_extend_subscription(customer: dict, days: int) -> Optional[str]:
    """
    Create new subscription or extend existing one
    Returns VPN username or None on error
    """
    vpn_username = customer.get("vpn_username") or generate_vpn_username(customer["telegram_id"])
    password = generate_vpn_password()
    
    try:
        # Check if user already exists
        existing = vpn_db.get_user(vpn_username)
        
        if existing:
            # Extend existing subscription
            current_days = existing.get("expiration_days", 0)
            vpn_db.update_user(vpn_username, {"expiration_days": current_days + days})
        else:
            # Create new user with unlimited traffic
            user_data = {
                "username": vpn_username,
                "password": password,
                "max_download_bytes": 999999 * 1073741824,  # ~1PB = unlimited
                "expiration_days": days,
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
    expiration_days = user.get("expiration_days", 0)
    
    return {
        "username": vpn_username,
        "password": user.get("password"),
        "traffic_used_gb": round(traffic_used / 1073741824, 2),
        "expiration_days": expiration_days,
        "status": user.get("status", "Unknown"),
    }


def get_subscription_link(vpn_username: str) -> Optional[str]:
    """Get subscription link for user"""
    try:
        from hysteria2.show_user_uri import get_user_uri
        uri = get_user_uri(vpn_username)
        return uri
    except:
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
    
    # Check for personal promo codes
    username = message.from_user.username
    if username:
        personal_promos = shop_db.get_promos_for_username(username)
        for promo in personal_promos:
            promo_type_text = f"{int(promo['value'])}% скидка" if promo['type'] == 'discount' else f"{int(promo['value'])} бесплатных дней"
            bot.send_message(
                message.chat.id,
                f"🎁 *У вас есть персональный промокод!*\n\n"
                f"Код: `{promo['code']}`\n"
                f"Бонус: {promo_type_text}\n\n"
                f"Нажмите «🎁 Ввести промокод» чтобы активировать!",
                parse_mode="Markdown"
            )


@bot.message_handler(func=lambda m: m.text == "🛒 Купить подписку")
def buy_subscription_handler(message):
    """Show available tariffs"""
    customer = get_or_create_customer(message)
    tariffs = shop_db.get_active_tariffs()
    
    if not tariffs:
        bot.send_message(
            message.chat.id,
            "😔 К сожалению, нет доступных тарифов.",
            reply_markup=main_menu_keyboard()
        )
        return
    
    text = "🛒 *Выберите тариф:*\n\n"
    
    for t in tariffs:
        days = t.get("days", 30)
        period = format_days(days)
        text += f"• *{t['name']}* — {period} — {t['price_stars']}⭐\n"
    
    # Check if trial available
    trial_text = ""
    if not customer.get("trial_used"):
        trial_days = int(CONFIG.get("TRIAL_DAYS", 3))
        trial_text = f"\n🎁 Также доступен пробный период на {trial_days} дня!"
    
    bot.send_message(
        message.chat.id,
        text + trial_text,
        parse_mode="Markdown",
        reply_markup=tariffs_keyboard(tariffs, show_trial=not customer.get("trial_used"))
    )


def format_days(days: int) -> str:
    """Format days to human readable string"""
    if days >= 365:
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
    
    text = (
        f"👤 *Ваш профиль*\n\n"
        f"🔑 Логин: `{info['username']}`\n"
        f"📊 Использовано: {info['traffic_used_gb']} GB\n"
        f"⏰ Осталось: {info['expiration_days']} дней\n"
        f"📶 Статус: {info['status']}"
    )
    
    bot.send_message(
        message.chat.id, text,
        parse_mode="Markdown",
        reply_markup=profile_keyboard(has_subscription=True)
    )


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
    customer = get_or_create_customer(message)
    telegram_id = customer["telegram_id"]
    telegram_username = customer.get("telegram_username")
    
    # Validate promo with user check (pass both ID and username)
    is_valid, msg, promo = shop_db.validate_promo(code, telegram_id, telegram_username)
    
    if not is_valid:
        bot.send_message(
            message.chat.id,
            f"❌ {msg}",
            reply_markup=main_menu_keyboard()
        )
        return
    
    # Handle free_period promo - apply immediately
    if promo["type"] == "free_period":
        days = int(promo["value"])
        
        # Create or extend subscription
        vpn_username = create_or_extend_subscription(customer, days)
        
        if vpn_username:
            # Mark promo as used
            shop_db.use_promo(code, telegram_id)
            
            # Get updated info
            info = get_user_subscription_info(vpn_username)
            
            text = (
                f"✅ *Промокод активирован!*\n\n"
                f"🎁 +{days} дней подписки\n"
                f"⏰ Всего осталось: {info['expiration_days']} дней\n\n"
            )
            
            if not customer.get("vpn_username"):
                text += f"🔑 Ваш логин: `{vpn_username}`\n\n"
            
            text += "Перейдите в «👤 Мой профиль» для получения ссылки."
            
            bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=main_menu_keyboard())
        else:
            bot.send_message(message.chat.id, "❌ Ошибка активации промокода", reply_markup=main_menu_keyboard())
        return
    
    # Discount promo - save for purchase
    if promo["type"] == "discount":
        shop_db.update_customer(telegram_id, {"pending_promo": code})
        
        text = (
            f"✅ *Промокод сохранён!*\n\n"
            f"🎁 Скидка {int(promo['value'])}%\n"
            f"📝 {promo.get('description', '')}\n\n"
            f"Промокод будет применён при покупке."
        )
        
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

@bot.callback_query_handler(func=lambda call: call.data == "trial")
def trial_callback(call):
    """Handle trial activation"""
    customer = get_or_create_customer_by_id(call.from_user.id, call.from_user.username)
    
    if customer.get("trial_used"):
        bot.answer_callback_query(call.id, "❌ Пробный период уже использован", show_alert=True)
        return
    
    trial_days = int(CONFIG.get("TRIAL_DAYS", 3))
    
    text = (
        f"🎁 *Пробный период*\n\n"
        f"⏰ Срок: {trial_days} дня\n"
        f"📊 Трафик: Безлимит\n"
        f"💰 Цена: Бесплатно\n\n"
        f"Активировать?"
    )
    
    bot.edit_message_text(
        text, call.message.chat.id, call.message.message_id,
        parse_mode="Markdown",
        reply_markup=confirm_trial_keyboard()
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("trial:"))
def trial_action_callback(call):
    """Handle trial confirmation"""
    action = call.data.split(":")[1]
    
    if action == "cancel":
        bot.edit_message_text(
            "Отменено",
            call.message.chat.id, call.message.message_id
        )
        return
    
    customer = get_or_create_customer_by_id(call.from_user.id, call.from_user.username)
    
    if customer.get("trial_used"):
        bot.answer_callback_query(call.id, "❌ Пробный период уже использован", show_alert=True)
        return
    
    trial_days = int(CONFIG.get("TRIAL_DAYS", 3))
    
    # Create subscription
    vpn_username = create_or_extend_subscription(customer, trial_days)
    
    if not vpn_username:
        bot.edit_message_text(
            "❌ Ошибка активации. Попробуйте позже.",
            call.message.chat.id, call.message.message_id
        )
        return
    
    # Mark trial as used
    shop_db.mark_trial_used(customer["telegram_id"])
    
    text = (
        f"✅ *Пробный период активирован!*\n\n"
        f"🔑 Логин: `{vpn_username}`\n"
        f"⏰ Срок: {trial_days} дня\n"
        f"📊 Трафик: Безлимит\n\n"
        f"Перейдите в «👤 Мой профиль» для получения ссылки подключения."
    )
    
    bot.edit_message_text(
        text, call.message.chat.id, call.message.message_id,
        parse_mode="Markdown"
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("tariff:"))
def tariff_select_callback(call):
    """Handle tariff selection"""
    tariff_id = call.data.split(":")[1]
    tariff = shop_db.get_tariff(tariff_id)
    
    if not tariff:
        bot.answer_callback_query(call.id, "Тариф не найден", show_alert=True)
        return
    
    customer = get_or_create_customer_by_id(call.from_user.id, call.from_user.username)
    
    # Check for pending promo
    promo_code = customer.get("pending_promo")
    final_price = tariff["price_stars"]
    promo_text = ""
    
    if promo_code:
        is_valid, msg, promo = shop_db.validate_promo(
            promo_code, customer["telegram_id"], customer.get("telegram_username"), tariff_id
        )
        if is_valid and promo["type"] == "discount":
            discount = int(promo["value"])
            final_price = int(final_price * (100 - discount) / 100)
            promo_text = f"🎁 Скидка {discount}%: -{tariff['price_stars'] - final_price}⭐\n"
    
    period = format_days(tariff.get("days", 30))
    
    text = (
        f"🛒 *Оформление подписки*\n\n"
        f"📋 Тариф: {tariff['name']}\n"
        f"📅 Срок: {period}\n"
        f"📊 Трафик: Безлимит\n"
        f"{promo_text}"
        f"💰 К оплате: {final_price}⭐\n\n"
        f"Подтвердить оплату?"
    )
    
    bot.edit_message_text(
        text, call.message.chat.id, call.message.message_id,
        parse_mode="Markdown",
        reply_markup=payment_keyboard(tariff_id, final_price)
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("pay:"))
def payment_callback(call):
    """Handle payment"""
    tariff_id = call.data.split(":")[1]
    
    tariff = shop_db.get_tariff(tariff_id)
    if not tariff:
        bot.answer_callback_query(call.id, "Тариф не найден", show_alert=True)
        return
    
    if not tariff.get("price_stars"):
        bot.answer_callback_query(call.id, "❌ Тариф не настроен для оплаты", show_alert=True)
        return
    
    customer = get_or_create_customer_by_id(call.from_user.id, call.from_user.username)
    
    # Calculate final price with promo
    final_price = tariff["price_stars"]
    promo_code = customer.get("pending_promo")
    
    if promo_code:
        is_valid, msg, promo = shop_db.validate_promo(
            promo_code, customer["telegram_id"], customer.get("telegram_username"), tariff_id
        )
        if is_valid and promo["type"] == "discount":
            discount = int(promo["value"])
            final_price = int(final_price * (100 - discount) / 100)
    
    # Create payment record
    payment = shop_db.create_payment(
        customer_id=customer["telegram_id"],
        tariff_id=tariff_id,
        amount=final_price,
        payment_method="stars",
        promo_code=promo_code
    )
    
    # Create Telegram Stars invoice
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
        return
    
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda call: call.data.startswith("profile:"))
def profile_action_callback(call):
    """Handle profile actions"""
    action = call.data.split(":")[1]
    customer = shop_db.get_customer(call.from_user.id)
    
    if not customer or not customer.get("vpn_username"):
        bot.answer_callback_query(call.id, "Нет активной подписки", show_alert=True)
        return
    
    if action == "qr":
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
        buy_subscription_handler(call.message)
        bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda call: call.data == "buy")
def buy_inline_callback(call):
    """Handle buy button from profile"""
    buy_subscription_handler(call.message)
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda call: call.data == "support:faq")
def support_faq_callback(call):
    """Handle FAQ button"""
    text = (
        "📖 *FAQ / Часто задаваемые вопросы*\n\n"
        "*Как подключиться?*\n"
        "1. Скачайте приложение (Hiddify, V2rayNG, Streisand)\n"
        "2. Получите ссылку в разделе «Мой профиль»\n"
        "3. Добавьте ссылку в приложение\n\n"
        "*Какие приложения использовать?*\n"
        "• iOS: Streisand, Shadowrocket\n"
        "• Android: Hiddify, V2rayNG\n"
        "• Windows/Mac: Hiddify, Nekoray\n\n"
        "*Не работает VPN?*\n"
        "Попробуйте переключить сервер или свяжитесь с поддержкой."
    )
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("◀️ Назад", callback_data="back:support"))
    
    bot.edit_message_text(
        text, call.message.chat.id, call.message.message_id,
        parse_mode="Markdown",
        reply_markup=markup
    )
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda call: call.data.startswith("back:"))
def back_callback(call):
    """Handle back navigation"""
    destination = call.data.split(":")[1]
    
    if destination == "main":
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.send_message(
            call.message.chat.id,
            "Выберите действие:",
            reply_markup=main_menu_keyboard()
        )
    elif destination == "tariffs":
        customer = shop_db.get_customer(call.from_user.id)
        tariffs = shop_db.get_active_tariffs()
        
        text = "🛒 *Выберите тариф:*"
        
        bot.edit_message_text(
            text, call.message.chat.id, call.message.message_id,
            parse_mode="Markdown",
            reply_markup=tariffs_keyboard(tariffs, show_trial=not customer.get("trial_used") if customer else True)
        )
    elif destination == "support":
        support_username = CONFIG.get("SUPPORT_USERNAME")
        text = (
            "💬 *Поддержка*\n\n"
            "Если у вас возникли вопросы или проблемы, "
            "свяжитесь с нашей поддержкой."
        )
        bot.edit_message_text(
            text, call.message.chat.id, call.message.message_id,
            parse_mode="Markdown",
            reply_markup=support_keyboard(support_username)
        )
    
    bot.answer_callback_query(call.id)


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
        process_successful_payment(message.chat.id, message.from_user.id, payment, payment_info["payment_id"])


def process_successful_payment(chat_id: int, telegram_id: int, payment: dict, external_id: str = None):
    """Process successful payment and create/extend subscription"""
    # Mark payment as completed
    shop_db.complete_payment(payment["_id"], external_id)
    
    # Get customer and tariff
    customer = shop_db.get_customer(payment["customer_id"])
    tariff = shop_db.get_tariff(payment["tariff_id"])
    
    if not customer or not tariff:
        bot.send_message(chat_id, "❌ Ошибка обработки платежа. Свяжитесь с поддержкой.")
        return
    
    # Calculate extra days from promo
    extra_days = 0
    promo_code = payment.get("promo_code")
    
    if promo_code:
        is_valid, _, promo = shop_db.validate_promo(
            promo_code, telegram_id, customer.get("telegram_username")
        )
        if is_valid:
            # Mark promo as used
            shop_db.use_promo(promo_code, telegram_id)
            # Clear pending promo
            shop_db.update_customer(telegram_id, {"pending_promo": None})
            
            if promo["type"] == "free_period":
                extra_days = int(promo["value"])
    
    # Create or extend subscription
    days = tariff.get("days", 30) + extra_days
    vpn_username = create_or_extend_subscription(customer, days)
    
    if not vpn_username:
        bot.send_message(chat_id, "❌ Ошибка создания подписки. Свяжитесь с поддержкой.")
        return
    
    # Get updated info
    info = get_user_subscription_info(vpn_username)
    period = format_days(tariff.get("days", 30))
    
    bonus_text = ""
    if extra_days > 0:
        bonus_text = f"🎁 +{extra_days} дней (промокод)\n"
    
    text = (
        f"✅ *Оплата успешна!*\n\n"
        f"📋 Тариф: {tariff['name']}\n"
        f"📅 Добавлено: {period}\n"
        f"{bonus_text}"
        f"⏰ Всего осталось: {info['expiration_days']} дней\n\n"
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
        shop_db.create_tariff("1 месяц", 30, 100, order=1)
        shop_db.create_tariff("3 месяца", 90, 250, order=2)
        shop_db.create_tariff("6 месяцев", 180, 450, order=3)
        shop_db.create_tariff("12 месяцев", 365, 750, order=4)
        print("Default tariffs created!")
    
    bot.infinity_polling()


if __name__ == "__main__":
    main()
