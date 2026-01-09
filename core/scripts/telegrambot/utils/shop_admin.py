"""
Shop Administration for Admin Bot
Manage tariffs, promos, and view customers/payments
"""

import sys
import os
from datetime import datetime, timedelta
from telebot import types

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from utils.command import bot, is_admin
from utils.common import create_main_markup
from db.shop_database import shop_db


# ==================== KEYBOARDS ====================

def shop_admin_keyboard():
    """Shop admin main menu"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(types.KeyboardButton("📋 Тарифы"), types.KeyboardButton("🎁 Промокоды"))
    markup.row(types.KeyboardButton("👥 Клиенты"), types.KeyboardButton("💰 Платежи"))
    markup.row(types.KeyboardButton("🏠 Главное меню"))
    return markup


def promo_type_keyboard():
    """Promo type selection"""
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("💸 Скидка %", callback_data="promo_type:discount"),
        types.InlineKeyboardButton("📅 Бесплатные дни", callback_data="promo_type:free_period"),
        types.InlineKeyboardButton("📦 Доп. трафик GB", callback_data="promo_type:extra_traffic"),
        types.InlineKeyboardButton("❌ Отмена", callback_data="promo_cancel")
    )
    return markup


def tariff_type_admin_keyboard():
    """Tariff type selection for admin"""
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("📦 По трафику (GB)", callback_data="admin_tariff_type:traffic"),
        types.InlineKeyboardButton("📅 По времени (дни)", callback_data="admin_tariff_type:time"),
        types.InlineKeyboardButton("❌ Отмена", callback_data="tariff_cancel")
    )
    return markup


# ==================== SHOP ADMIN MENU ====================

@bot.message_handler(func=lambda message: is_admin(message.from_user.id) and message.text == '🏪 Магазин')
def shop_admin_menu(message):
    """Shop admin main menu"""
    text = (
        "🏪 *Управление магазином*\n\n"
        "📋 Тарифы - управление тарифами\n"
        "🎁 Промокоды - создание и управление\n"
        "👥 Клиенты - список клиентов\n"
        "💰 Платежи - история платежей"
    )
    bot.send_message(
        message.chat.id, text,
        parse_mode="Markdown",
        reply_markup=shop_admin_keyboard()
    )


# ==================== TARIFFS ====================

@bot.message_handler(func=lambda message: is_admin(message.from_user.id) and message.text == '📋 Тарифы')
def tariffs_menu(message):
    """List all tariffs"""
    tariffs = shop_db.get_all_tariffs()
    
    if not tariffs:
        text = "📋 *Тарифы*\n\nНет созданных тарифов."
    else:
        text = "📋 *Тарифы:*\n\n"
        for t in tariffs:
            status = "✅" if t.get("is_active", True) else "❌"
            if t["type"] == "traffic":
                desc = f"{t['traffic_gb']} GB"
            else:
                desc = f"{t.get('days', 0)} дней"
            
            stars = f" / {t['price_stars']}⭐" if t.get('price_stars') else ""
            text += f"{status} *{t['name']}* — {desc} — {t['price']}₽{stars}\n"
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("➕ Добавить", callback_data="add_tariff"),
        types.InlineKeyboardButton("🔄 Обновить", callback_data="refresh_tariffs")
    )
    
    bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: is_admin(call.from_user.id) and call.data == "add_tariff")
def add_tariff_callback(call):
    """Start adding new tariff"""
    bot.edit_message_text(
        "📋 *Создание тарифа*\n\nВыберите тип:",
        call.message.chat.id, call.message.message_id,
        parse_mode="Markdown",
        reply_markup=tariff_type_admin_keyboard()
    )


@bot.callback_query_handler(func=lambda call: is_admin(call.from_user.id) and call.data.startswith("admin_tariff_type:"))
def tariff_type_selected(call):
    """Handle tariff type selection"""
    tariff_type = call.data.split(":")[1]
    
    text = (
        f"📋 *Новый тариф ({tariff_type})*\n\n"
        f"Введите данные в формате:\n"
        f"`название|{'GB' if tariff_type == 'traffic' else 'дни'}|цена_руб|цена_звезды`\n\n"
        f"Пример: `{'100GB|100|250|125' if tariff_type == 'traffic' else '1 месяц|30|200|100'}`"
    )
    
    bot.edit_message_text(
        text, call.message.chat.id, call.message.message_id,
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(call.message, process_tariff_creation, tariff_type)


def process_tariff_creation(message, tariff_type):
    """Process tariff creation"""
    try:
        parts = message.text.strip().split("|")
        if len(parts) < 3:
            bot.reply_to(message, "❌ Неверный формат. Попробуйте снова.")
            return
        
        name = parts[0].strip()
        value = int(parts[1].strip())
        price = float(parts[2].strip())
        price_stars = int(parts[3].strip()) if len(parts) > 3 else None
        
        if tariff_type == "traffic":
            shop_db.create_tariff(name, "traffic", price, traffic_gb=value, price_stars=price_stars)
        else:
            shop_db.create_tariff(name, "time", price, days=value, price_stars=price_stars)
        
        bot.reply_to(message, f"✅ Тариф «{name}» создан!", reply_markup=shop_admin_keyboard())
        
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {e}", reply_markup=shop_admin_keyboard())


# ==================== PROMO CODES ====================

@bot.message_handler(func=lambda message: is_admin(message.from_user.id) and message.text == '🎁 Промокоды')
def promos_menu(message):
    """List all promo codes"""
    promos = shop_db.get_all_promos()
    
    if not promos:
        text = "🎁 *Промокоды*\n\nНет созданных промокодов."
    else:
        text = "🎁 *Промокоды:*\n\n"
        for p in promos:
            status = "✅" if p.get("is_active", True) else "❌"
            type_text = {
                "discount": f"скидка {p['value']}%",
                "free_period": f"+{p['value']} дней",
                "extra_traffic": f"+{p['value']} GB"
            }.get(p["type"], "бонус")
            
            uses = f"{p['uses_count']}/{p['max_uses']}"
            text += f"{status} `{p['code']}` — {type_text} ({uses})\n"
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("➕ Создать", callback_data="add_promo"),
        types.InlineKeyboardButton("🔄 Обновить", callback_data="refresh_promos")
    )
    
    bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: is_admin(call.from_user.id) and call.data == "add_promo")
def add_promo_callback(call):
    """Start creating promo code"""
    bot.edit_message_text(
        "🎁 *Создание промокода*\n\nВыберите тип:",
        call.message.chat.id, call.message.message_id,
        parse_mode="Markdown",
        reply_markup=promo_type_keyboard()
    )


@bot.callback_query_handler(func=lambda call: is_admin(call.from_user.id) and call.data.startswith("promo_type:"))
def promo_type_selected(call):
    """Handle promo type selection"""
    promo_type = call.data.split(":")[1]
    
    type_text = {
        "discount": "скидки (0-100%)",
        "free_period": "бесплатных дней",
        "extra_traffic": "доп. трафика (GB)"
    }.get(promo_type)
    
    text = (
        f"🎁 *Новый промокод*\n\n"
        f"Введите данные в формате:\n"
        f"`код|значение_{type_text}|макс_использований|срок_дней`\n\n"
        f"Пример: `SALE50|50|100|30`\n"
        f"(код SALE50, значение 50, 100 использований, 30 дней)\n\n"
        f"Для бесконечного срока укажите 0"
    )
    
    bot.edit_message_text(
        text, call.message.chat.id, call.message.message_id,
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(call.message, process_promo_creation, promo_type)


def process_promo_creation(message, promo_type):
    """Process promo code creation"""
    try:
        parts = message.text.strip().split("|")
        if len(parts) < 3:
            bot.reply_to(message, "❌ Неверный формат. Попробуйте снова.")
            return
        
        code = parts[0].strip().upper()
        value = float(parts[1].strip())
        max_uses = int(parts[2].strip())
        expire_days = int(parts[3].strip()) if len(parts) > 3 else 0
        
        expires_at = None
        if expire_days > 0:
            expires_at = datetime.utcnow() + timedelta(days=expire_days)
        
        promo = shop_db.create_promo(
            code=code,
            promo_type=promo_type,
            value=value,
            max_uses=max_uses,
            expires_at=expires_at
        )
        
        type_text = {
            "discount": f"скидка {value}%",
            "free_period": f"+{int(value)} дней",
            "extra_traffic": f"+{int(value)} GB"
        }.get(promo_type)
        
        bot.reply_to(
            message,
            f"✅ Промокод создан!\n\n"
            f"🎁 Код: `{code}`\n"
            f"📋 Тип: {type_text}\n"
            f"🔢 Макс. использований: {max_uses}\n"
            f"⏰ Истекает: {'никогда' if not expires_at else expires_at.strftime('%Y-%m-%d')}",
            parse_mode="Markdown",
            reply_markup=shop_admin_keyboard()
        )
        
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {e}", reply_markup=shop_admin_keyboard())


@bot.callback_query_handler(func=lambda call: is_admin(call.from_user.id) and call.data == "promo_cancel")
def promo_cancel_callback(call):
    """Cancel promo creation"""
    bot.edit_message_text(
        "Отменено",
        call.message.chat.id, call.message.message_id
    )


# ==================== CUSTOMERS ====================

@bot.message_handler(func=lambda message: is_admin(message.from_user.id) and message.text == '👥 Клиенты')
def customers_menu(message):
    """List customers"""
    customers = shop_db.get_all_customers()
    
    if not customers:
        text = "👥 *Клиенты*\n\nНет зарегистрированных клиентов."
    else:
        text = f"👥 *Клиенты ({len(customers)}):*\n\n"
        for c in customers[:20]:  # Show first 20
            username = c.get("telegram_username") or "—"
            vpn = c.get("vpn_username") or "—"
            trial = "✅" if c.get("trial_used") else "❌"
            text += f"• @{username} → `{vpn}` (trial: {trial})\n"
        
        if len(customers) > 20:
            text += f"\n... и ещё {len(customers) - 20}"
    
    bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=shop_admin_keyboard())


# ==================== PAYMENTS ====================

@bot.message_handler(func=lambda message: is_admin(message.from_user.id) and message.text == '💰 Платежи')
def payments_menu(message):
    """Show payment statistics"""
    stats = shop_db.get_payments_stats(30)
    
    text = "💰 *Статистика платежей (30 дней):*\n\n"
    
    total = 0
    total_count = 0
    
    for method, data in stats.items():
        method_name = {"stars": "⭐ Telegram Stars", "yookassa": "💳 ЮKassa"}.get(method, method)
        text += f"{method_name}:\n"
        text += f"  Сумма: {data['total']}₽\n"
        text += f"  Кол-во: {data['count']}\n\n"
        total += data['total']
        total_count += data['count']
    
    text += f"📊 *Итого:* {total}₽ ({total_count} платежей)"
    
    bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=shop_admin_keyboard())


@bot.message_handler(func=lambda message: is_admin(message.from_user.id) and message.text == '🏠 Главное меню')
def back_to_main(message):
    """Return to main menu"""
    bot.send_message(
        message.chat.id,
        "🏠 Главное меню",
        reply_markup=create_main_markup()
    )

