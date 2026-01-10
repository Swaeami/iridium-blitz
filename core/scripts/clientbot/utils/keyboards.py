"""
Keyboard utilities for Client Bot
All inline keyboards - single message navigation
"""

from telebot import types
from typing import List, Dict, Optional


def main_menu_keyboard() -> types.InlineKeyboardMarkup:
    """Main menu inline keyboard"""
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("🛒 Купить подписку", callback_data="menu:buy"),
        types.InlineKeyboardButton("👤 Мой профиль", callback_data="menu:profile"),
        types.InlineKeyboardButton("🎁 Ввести промокод", callback_data="menu:promo"),
        types.InlineKeyboardButton("💬 Поддержка", callback_data="menu:support")
    )
    return markup


def tariffs_keyboard(tariffs: List[Dict], show_trial: bool = True) -> types.InlineKeyboardMarkup:
    """Display available tariffs with prices"""
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    for t in tariffs:
        days = t.get('days', 30)
        price_rub = t.get('price_rub', 0)
        stars = int(price_rub * 1.5)
        
        label = f"📅 {t['name']} — {stars}⭐"
        
        markup.add(types.InlineKeyboardButton(
            label,
            callback_data=f"tariff:{str(t['_id'])}"
        ))
    
    if show_trial:
        markup.add(types.InlineKeyboardButton(
            "🎁 Пробный период (бесплатно)",
            callback_data="trial"
        ))
    
    markup.add(types.InlineKeyboardButton("◀️ Главное меню", callback_data="menu:main"))
    return markup


def tariff_detail_keyboard(tariff_id: str, price_stars: int) -> types.InlineKeyboardMarkup:
    """Tariff confirmation with pay button"""
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    markup.add(types.InlineKeyboardButton(
        f"⭐ Оплатить {price_stars} Stars",
        callback_data=f"pay:{tariff_id}"
    ))
    
    markup.add(types.InlineKeyboardButton("◀️ К тарифам", callback_data="menu:buy"))
    return markup


def confirm_trial_keyboard() -> types.InlineKeyboardMarkup:
    """Confirm trial activation"""
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("✅ Активировать", callback_data="trial:confirm"),
        types.InlineKeyboardButton("❌ Отмена", callback_data="menu:buy")
    )
    return markup


def profile_keyboard(has_subscription: bool = False) -> types.InlineKeyboardMarkup:
    """Profile actions keyboard"""
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    if has_subscription:
        markup.add(
            types.InlineKeyboardButton("📱 Показать QR-код", callback_data="profile:qr"),
            types.InlineKeyboardButton("📋 Скопировать ссылку", callback_data="profile:link"),
            types.InlineKeyboardButton("🔄 Продлить подписку", callback_data="menu:buy")
        )
    else:
        markup.add(types.InlineKeyboardButton("🛒 Купить подписку", callback_data="menu:buy"))
    
    markup.add(types.InlineKeyboardButton("◀️ Главное меню", callback_data="menu:main"))
    return markup


def profile_back_keyboard() -> types.InlineKeyboardMarkup:
    """Back to profile button"""
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("◀️ Назад к профилю", callback_data="menu:profile"))
    return markup


def support_keyboard(support_username: str = None) -> types.InlineKeyboardMarkup:
    """Support keyboard"""
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    if support_username:
        username = support_username.lstrip('@')
        markup.add(types.InlineKeyboardButton(
            "💬 Написать в поддержку",
            url=f"https://t.me/{username}"
        ))
    
    markup.add(types.InlineKeyboardButton(
        "📖 FAQ / Инструкция",
        callback_data="support:faq"
    ))
    markup.add(types.InlineKeyboardButton("◀️ Главное меню", callback_data="menu:main"))
    return markup


def promo_keyboard() -> types.InlineKeyboardMarkup:
    """Promo code input prompt"""
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("◀️ Главное меню", callback_data="menu:main"))
    return markup


def promo_result_keyboard(success: bool = True) -> types.InlineKeyboardMarkup:
    """After promo activation"""
    markup = types.InlineKeyboardMarkup(row_width=1)
    if success:
        markup.add(types.InlineKeyboardButton("👤 Мой профиль", callback_data="menu:profile"))
    markup.add(types.InlineKeyboardButton("◀️ Главное меню", callback_data="menu:main"))
    return markup


def faq_keyboard() -> types.InlineKeyboardMarkup:
    """FAQ back button"""
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("◀️ Назад", callback_data="menu:support"))
    return markup
