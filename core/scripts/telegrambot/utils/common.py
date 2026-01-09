from telebot import types

def create_main_markup():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row('➕ Add User', '🔍 Show User')
    markup.row('🗑️ Delete User', '🖥️ Server Info')
    markup.row('💾 Backup Server', '⚙️ Settings')
    markup.row('🏪 Магазин')  # Shop management
    return markup

def create_settings_markup():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row('🔗 Get Webpanel URL')
    markup.row('⬅️ Back')
    return markup