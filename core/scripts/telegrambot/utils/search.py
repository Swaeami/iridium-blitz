from telebot import types
from utils.command import *

@bot.inline_handler(lambda query: is_admin(query.from_user.id))
def handle_inline_query(query):
    command = f"python3 {CLI_PATH} list-users"
    result = run_cli_command(command)
    try:
        users = json.loads(result)
    except json.JSONDecodeError:
        bot.answer_inline_query(query.id, results=[], switch_pm_text="Error retrieving users.", switch_pm_user_id=query.from_user.id)
        return

    query_text = query.query.lower().replace('\\_', '_')
    results = []

    def format_user_info(user):
        username = user['username']
        traffic_gb = user.get('max_download_bytes', 0) / (1024 ** 3)
        usage_gb = (user.get('download_bytes', 0) + user.get('upload_bytes', 0)) / (1024 ** 3)
        max_ips = user.get('max_ips')
        max_ips_str = str(max_ips) if max_ips else "Global"
        unlimited = "✅" if user.get('unlimited_user', False) else "❌"
        blocked = "🚫" if user.get('blocked', False) else "✅"
        status = user.get('status', 'N/A')
        note = user.get('note', '-')
        
        return (
            f"👤 *{username}*\n"
            f"━━━━━━━━━━━━━━━\n"
            f"📊 Traffic: `{usage_gb:.2f}` / `{traffic_gb:.2f}` GB\n"
            f"📅 Days: `{user.get('expiration_days', 'N/A')}`\n"
            f"🗓 Created: `{user.get('account_creation_date', 'N/A')}`\n"
            f"🌐 Max IPs: `{max_ips_str}`\n"
            f"♾ Unlimited IP: {unlimited}\n"
            f"🔓 Active: {blocked}\n"
            f"📍 Status: `{status}`\n"
            f"📝 Note: `{note}`"
        )

    if query_text == "block":
        for user in users:
            if user.get('blocked', False):
                username = user['username']
                title = f"🚫 {username} (Blocked)"
                description = f"Traffic: {user.get('max_download_bytes', 0) / (1024 ** 3):.2f} GB | Days: {user.get('expiration_days', 'N/A')}"
                results.append(types.InlineQueryResultArticle(
                    id=username,
                    title=title,
                    description=description,
                    input_message_content=types.InputTextMessageContent(
                        message_text=format_user_info(user),
                        parse_mode="Markdown"
                    )
                ))
    else:
        for user in users:
            username = user['username']
            if query_text in username.lower():
                status_icon = "🚫" if user.get('blocked', False) else "✅"
                title = f"{status_icon} {username}"
                description = f"Traffic: {user.get('max_download_bytes', 0) / (1024 ** 3):.2f} GB | Days: {user.get('expiration_days', 'N/A')}"
                results.append(types.InlineQueryResultArticle(
                    id=username,
                    title=title,
                    description=description,
                    input_message_content=types.InputTextMessageContent(
                        message_text=format_user_info(user),
                        parse_mode="Markdown"
                    )
                ))

    bot.answer_inline_query(query.id, results, cache_time=0)