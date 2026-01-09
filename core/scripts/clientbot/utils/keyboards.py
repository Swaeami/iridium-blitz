"""
Keyboard utilities for Client Bot
"""

from telebot import types
from typing import List, Dict, Optional


def main_menu_keyboard() -> types.ReplyKeyboardMarkup:
    """Main menu keyboard"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(types.KeyboardButton("🛒 Купить подписку"))
    markup.row(types.KeyboardButton("👤 Мой профиль"), types.KeyboardButton("📊 Статистика"))
    markup.row(types.KeyboardButton("🎁 Ввести промокод"), types.KeyboardButton("💬 Поддержка"))
    return markup


def tariff_type_keyboard() -> types.InlineKeyboardMarkup:
    """Tariff type selection"""
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("📦 По трафику (безлимит времени)", callback_data="tariff_type:traffic"),
        types.InlineKeyboardButton("📅 По времени (безлимит трафика)", callback_data="tariff_type:time"),
        types.InlineKeyboardButton("🎁 Пробный период (3 дня)", callback_data="tariff_type:trial")
    )
    return markup


def tariffs_keyboard(tariffs: List[Dict], tariff_type: str) -> types.InlineKeyboardMarkup:
    """Display available tariffs"""
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    for t in tariffs:
        if tariff_type == "traffic":
            label = f"📦 {t['traffic_gb']} GB — {t['price']}₽"
            if t.get('price_stars'):
                label += f" / {t['price_stars']}⭐"
        else:  # time
            days = t.get('days', 30)
            if days >= 365:
                period = f"{days // 365} год" if days // 365 == 1 else f"{days // 365} года"
            elif days >= 30:
                months = days // 30
                period = f"{months} мес."
            else:
                period = f"{days} дн."
            label = f"📅 {period} — {t['price']}₽"
            if t.get('price_stars'):
                label += f" / {t['price_stars']}⭐"
        
        markup.add(types.InlineKeyboardButton(
            label,
            callback_data=f"tariff:{str(t['_id'])}"
        ))
    
    markup.add(types.InlineKeyboardButton("◀️ Назад", callback_data="back:tariff_type"))
    return markup


def payment_method_keyboard(tariff_id: str, price_rub: float, price_stars: int = None) -> types.InlineKeyboardMarkup:
    """Payment method selection"""
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    # YooKassa (always available)
    markup.add(types.InlineKeyboardButton(
        f"💳 Оплатить {price_rub}₽",
        callback_data=f"pay:yookassa:{tariff_id}"
    ))
    
    # Telegram Stars (if price set)
    if price_stars:
        markup.add(types.InlineKeyboardButton(
            f"⭐ Оплатить {price_stars} Stars",
            callback_data=f"pay:stars:{tariff_id}"
        ))
    
    markup.add(
        types.InlineKeyboardButton("🎁 Есть промокод", callback_data=f"promo:{tariff_id}"),
        types.InlineKeyboardButton("◀️ Назад", callback_data="back:tariffs")
    )
    return markup


def confirm_trial_keyboard() -> types.InlineKeyboardMarkup:
    """Confirm trial activation"""
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("✅ Активировать", callback_data="trial:confirm"),
        types.InlineKeyboardButton("❌ Отмена", callback_data="trial:cancel")
    )
    return markup


def back_keyboard(callback_data: str = "back:main") -> types.InlineKeyboardMarkup:
    """Simple back button"""
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("◀️ Назад", callback_data=callback_data))
    return markup


def profile_keyboard(has_subscription: bool = False) -> types.InlineKeyboardMarkup:
    """Profile actions keyboard"""
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    if has_subscription:
        markup.add(
            types.InlineKeyboardButton("📱 Показать QR-код", callback_data="profile:qr"),
            types.InlineKeyboardButton("📋 Копировать ссылку", callback_data="profile:link"),
            types.InlineKeyboardButton("🔄 Продлить подписку", callback_data="profile:renew")
        )
    else:
        markup.add(types.InlineKeyboardButton("🛒 Купить подписку", callback_data="buy"))
    
    return markup


def support_keyboard(support_username: str = None) -> types.InlineKeyboardMarkup:
    """Support keyboard"""
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    if support_username:
        markup.add(types.InlineKeyboardButton(
            "💬 Написать в поддержку",
            url=f"https://t.me/{support_username}"
        ))
    
    markup.add(types.InlineKeyboardButton(
        "📖 FAQ / Инструкция",
        callback_data="support:faq"
    ))
    return markup


def cancel_keyboard() -> types.ReplyKeyboardMarkup:
    """Cancel action keyboard"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(types.KeyboardButton("❌ Отмена"))
    return markup

