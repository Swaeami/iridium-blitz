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
    show_tariffs_list(message.chat.id)


def show_tariffs_list(chat_id, message_id=None):
    """Display tariffs list with inline buttons"""
    tariffs = shop_db.get_all_tariffs()
    
    if not tariffs:
        text = "📋 *Тарифы*\n\nНет созданных тарифов."
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("➕ Добавить", callback_data="add_tariff"))
    else:
        text = "📋 *Тарифы:*\n\n"
        markup = types.InlineKeyboardMarkup(row_width=2)
        
        for i, t in enumerate(tariffs):
            status = "✅" if t.get("is_active", True) else "❌"
            if t["type"] == "traffic":
                desc = f"{t.get('traffic_gb', 0)} GB"
            else:
                desc = f"{t.get('days', 0)} дней"
            
            stars = f" / {t.get('price_stars', 0)}⭐" if t.get('price_stars') else ""
            text += f"{i+1}. {status} *{t['name']}* — {desc}{stars}\n"
            
            # Add management buttons for each tariff
            tariff_id = str(t['_id'])
            markup.row(
                types.InlineKeyboardButton(f"✏️ {t['name']}", callback_data=f"edit_tariff:{tariff_id}"),
                types.InlineKeyboardButton("🗑️", callback_data=f"delete_tariff:{tariff_id}")
            )
        
        markup.row(
            types.InlineKeyboardButton("➕ Добавить", callback_data="add_tariff"),
            types.InlineKeyboardButton("🔄 Обновить", callback_data="refresh_tariffs")
        )
    
    if message_id:
        bot.edit_message_text(text, chat_id, message_id, parse_mode="Markdown", reply_markup=markup)
    else:
        bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=markup)


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


@bot.callback_query_handler(func=lambda call: is_admin(call.from_user.id) and call.data == "refresh_tariffs")
def refresh_tariffs_callback(call):
    """Refresh tariffs list"""
    show_tariffs_list(call.message.chat.id, call.message.message_id)
    bot.answer_callback_query(call.id, "Обновлено")


@bot.callback_query_handler(func=lambda call: is_admin(call.from_user.id) and call.data.startswith("delete_tariff:"))
def delete_tariff_callback(call):
    """Delete tariff confirmation"""
    tariff_id = call.data.split(":")[1]
    tariff = shop_db.get_tariff(tariff_id)
    
    if not tariff:
        bot.answer_callback_query(call.id, "❌ Тариф не найден", show_alert=True)
        return
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("✅ Да, удалить", callback_data=f"confirm_del_tariff:{tariff_id}"),
        types.InlineKeyboardButton("❌ Отмена", callback_data="cancel_del_tariff")
    )
    
    bot.edit_message_text(
        f"🗑️ *Удалить тариф?*\n\n{tariff['name']}",
        call.message.chat.id, call.message.message_id,
        parse_mode="Markdown",
        reply_markup=markup
    )


@bot.callback_query_handler(func=lambda call: is_admin(call.from_user.id) and call.data.startswith("confirm_del_tariff:"))
def confirm_delete_tariff_callback(call):
    """Confirm tariff deletion"""
    tariff_id = call.data.split(":")[1]
    
    if shop_db.delete_tariff(tariff_id):
        bot.answer_callback_query(call.id, "✅ Тариф удалён")
    else:
        bot.answer_callback_query(call.id, "❌ Ошибка удаления", show_alert=True)
    
    show_tariffs_list(call.message.chat.id, call.message.message_id)


@bot.callback_query_handler(func=lambda call: is_admin(call.from_user.id) and call.data == "cancel_del_tariff")
def cancel_delete_tariff_callback(call):
    """Cancel tariff deletion"""
    show_tariffs_list(call.message.chat.id, call.message.message_id)
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda call: is_admin(call.from_user.id) and call.data.startswith("edit_tariff:"))
def edit_tariff_callback(call):
    """Edit tariff menu"""
    tariff_id = call.data.split(":")[1]
    tariff = shop_db.get_tariff(tariff_id)
    
    if not tariff:
        bot.answer_callback_query(call.id, "❌ Тариф не найден", show_alert=True)
        return
    
    if tariff["type"] == "traffic":
        desc = f"{tariff.get('traffic_gb', 0)} GB"
    else:
        desc = f"{tariff.get('days', 0)} дней"
    
    text = (
        f"✏️ *Редактирование тарифа*\n\n"
        f"📋 Название: {tariff['name']}\n"
        f"📦 Значение: {desc}\n"
        f"💰 Цена: {tariff.get('price', 0)}₽\n"
        f"⭐ Звёзды: {tariff.get('price_stars', 'не задано')}\n\n"
        f"Введите новую цену в звёздах (только число):"
    )
    
    bot.edit_message_text(
        text, call.message.chat.id, call.message.message_id,
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(call.message, process_tariff_edit, tariff_id)


def process_tariff_edit(message, tariff_id):
    """Process tariff edit"""
    try:
        new_price_stars = int(message.text.strip())
        
        # Update tariff
        from bson import ObjectId
        shop_db.tariffs.update_one(
            {"_id": ObjectId(tariff_id)},
            {"$set": {"price_stars": new_price_stars}}
        )
        
        bot.reply_to(message, f"✅ Цена обновлена: {new_price_stars}⭐", reply_markup=shop_admin_keyboard())
        
    except ValueError:
        bot.reply_to(message, "❌ Введите число", reply_markup=shop_admin_keyboard())
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {e}", reply_markup=shop_admin_keyboard())


@bot.callback_query_handler(func=lambda call: is_admin(call.from_user.id) and call.data == "tariff_cancel")
def tariff_cancel_callback(call):
    """Cancel tariff creation"""
    show_tariffs_list(call.message.chat.id, call.message.message_id)
    bot.answer_callback_query(call.id)


# ==================== PROMO CODES ====================

@bot.message_handler(func=lambda message: is_admin(message.from_user.id) and message.text == '🎁 Промокоды')
def promos_menu(message):
    """List all promo codes"""
    show_promos_list(message.chat.id)


def show_promos_list(chat_id, message_id=None):
    """Display promos list with inline buttons"""
    promos = shop_db.get_all_promos()
    
    if not promos:
        text = "🎁 *Промокоды*\n\nНет созданных промокодов."
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("➕ Создать", callback_data="add_promo"))
    else:
        text = "🎁 *Промокоды:*\n\n"
        markup = types.InlineKeyboardMarkup(row_width=2)
        
        for p in promos:
            status = "✅" if p.get("is_active", True) else "❌"
            type_text = {
                "discount": f"скидка {p['value']}%",
                "free_period": f"+{int(p['value'])} дней",
                "extra_traffic": f"+{int(p['value'])} GB"
            }.get(p["type"], "бонус")
            
            uses = f"{p.get('uses_count', 0)}/{p.get('max_uses', 0)}"
            text += f"{status} `{p['code']}` — {type_text} ({uses})\n"
            
            # Add delete button for each promo
            markup.row(
                types.InlineKeyboardButton(f"📋 {p['code']}", callback_data=f"view_promo:{p['code']}"),
                types.InlineKeyboardButton("🗑️", callback_data=f"delete_promo:{p['code']}")
            )
        
        markup.row(
            types.InlineKeyboardButton("➕ Создать", callback_data="add_promo"),
            types.InlineKeyboardButton("🔄 Обновить", callback_data="refresh_promos")
        )
    
    if message_id:
        bot.edit_message_text(text, chat_id, message_id, parse_mode="Markdown", reply_markup=markup)
    else:
        bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=markup)


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
    show_promos_list(call.message.chat.id, call.message.message_id)
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda call: is_admin(call.from_user.id) and call.data == "refresh_promos")
def refresh_promos_callback(call):
    """Refresh promos list"""
    show_promos_list(call.message.chat.id, call.message.message_id)
    bot.answer_callback_query(call.id, "Обновлено")


@bot.callback_query_handler(func=lambda call: is_admin(call.from_user.id) and call.data.startswith("view_promo:"))
def view_promo_callback(call):
    """View promo details"""
    code = call.data.split(":")[1]
    is_valid, msg, promo = shop_db.validate_promo(code)
    
    if not promo:
        bot.answer_callback_query(call.id, "❌ Промокод не найден", show_alert=True)
        return
    
    type_text = {
        "discount": f"скидка {promo['value']}%",
        "free_period": f"+{int(promo['value'])} дней",
        "extra_traffic": f"+{int(promo['value'])} GB"
    }.get(promo["type"], "бонус")
    
    status = "✅ Активен" if promo.get("is_active", True) else "❌ Деактивирован"
    
    text = (
        f"🎁 *Промокод: {code}*\n\n"
        f"📋 Тип: {type_text}\n"
        f"🔢 Использований: {promo.get('uses_count', 0)}/{promo.get('max_uses', 0)}\n"
        f"📊 Статус: {status}\n"
    )
    
    if promo.get('expires_at'):
        text += f"⏰ Истекает: {promo['expires_at'].strftime('%Y-%m-%d')}\n"
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("◀️ Назад", callback_data="refresh_promos"))
    
    bot.edit_message_text(
        text, call.message.chat.id, call.message.message_id,
        parse_mode="Markdown",
        reply_markup=markup
    )


@bot.callback_query_handler(func=lambda call: is_admin(call.from_user.id) and call.data.startswith("delete_promo:"))
def delete_promo_callback(call):
    """Delete promo confirmation"""
    code = call.data.split(":")[1]
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("✅ Да, удалить", callback_data=f"confirm_del_promo:{code}"),
        types.InlineKeyboardButton("❌ Отмена", callback_data="refresh_promos")
    )
    
    bot.edit_message_text(
        f"🗑️ *Удалить промокод?*\n\n`{code}`",
        call.message.chat.id, call.message.message_id,
        parse_mode="Markdown",
        reply_markup=markup
    )


@bot.callback_query_handler(func=lambda call: is_admin(call.from_user.id) and call.data.startswith("confirm_del_promo:"))
def confirm_delete_promo_callback(call):
    """Confirm promo deletion"""
    code = call.data.split(":")[1]
    
    if shop_db.deactivate_promo(code):
        bot.answer_callback_query(call.id, "✅ Промокод удалён")
    else:
        bot.answer_callback_query(call.id, "❌ Ошибка удаления", show_alert=True)
    
    show_promos_list(call.message.chat.id, call.message.message_id)


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

