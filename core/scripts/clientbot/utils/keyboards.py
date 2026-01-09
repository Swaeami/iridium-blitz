"""
Keyboard utilities for Client Bot
Time-based tariffs only
"""

from telebot import types
from typing import List, Dict, Optional


def main_menu_keyboard() -> types.ReplyKeyboardMarkup:
    """Main menu keyboard"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(types.KeyboardButton("🛒 Купить подписку"))
    markup.row(types.KeyboardButton("👤 Мой профиль"))
    markup.row(types.KeyboardButton("🎁 Ввести промокод"), types.KeyboardButton("💬 Поддержка"))
    return markup


def tariffs_keyboard(tariffs: List[Dict], show_trial: bool = True) -> types.InlineKeyboardMarkup:
    """Display available tariffs"""
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    for t in tariffs:
        days = t.get('days', 30)
        if days >= 365:
            period = f"{days // 365} год" if days // 365 == 1 else f"{days // 365} года"
        elif days >= 30:
            months = days // 30
            period = f"{months} мес."
        else:
            period = f"{days} дн."
        
        label = f"📅 {t['name']} — {t.get('price_stars', 0)}⭐"
        
        markup.add(types.InlineKeyboardButton(
            label,
            callback_data=f"tariff:{str(t['_id'])}"
        ))
    
    if show_trial:
        markup.add(types.InlineKeyboardButton(
            "🎁 Пробный период (бесплатно)",
            callback_data="trial"
        ))
    
    return markup


def payment_keyboard(tariff_id: str, price_stars: int) -> types.InlineKeyboardMarkup:
    """Payment confirmation keyboard"""
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    markup.add(types.InlineKeyboardButton(
        f"⭐ Оплатить {price_stars} Stars",
        callback_data=f"pay:{tariff_id}"
    ))
    
    markup.add(types.InlineKeyboardButton("◀️ Назад", callback_data="back:tariffs"))
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
        # Remove @ if present
        username = support_username.lstrip('@')
        markup.add(types.InlineKeyboardButton(
            "💬 Написать в поддержку",
            url=f"https://t.me/{username}"
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
