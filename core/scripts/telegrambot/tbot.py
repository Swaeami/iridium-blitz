from telebot import types
from utils import *
import threading
import time

@bot.message_handler(commands=['start'])
def send_welcome(message):
    if is_admin(message.from_user.id):
        markup = create_main_markup()
        bot.reply_to(message, "Welcome to the User Management Bot!", reply_markup=markup)
    else:
        bot.reply_to(message, "Unauthorized access. You do not have permission to use this bot.")


@bot.message_handler(content_types=['photo'])
def photo_handler(message):
    """Handle photo messages - return file_id for client bot cover image"""
    if not is_admin(message.from_user.id):
        return
    
    # Get the largest photo (last in the list)
    photo = message.photo[-1]
    file_id = photo.file_id
    
    bot.reply_to(
        message,
        f"📷 *File ID для обложки клиентского бота:*\n\n"
        f"`{file_id}`\n\n"
        f"Установите на сервере:\n"
        f"`python3 /etc/hysteria/core/scripts/clientbot/runclientbot.py config COVER_IMAGE {file_id}`",
        parse_mode="Markdown"
    )

def monitoring_thread():
    while True:
        monitor_system_resources()
        time.sleep(60)

if __name__ == '__main__':
    monitor_thread = threading.Thread(target=monitoring_thread, daemon=True)
    monitor_thread.start()
    version_thread = threading.Thread(target=version_monitoring, daemon=True)
    version_thread.start()
    bot.polling(none_stop=True)
