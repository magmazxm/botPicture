import os
import requests
import io
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
import threading # สำหรับการรัน Web Server แยกจากบอท
from flask import Flask # สำหรับเปิด Port

# *********** ตั้งค่า Environment Variables & Constants ***********
load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
FREEPIK_API_KEY = os.getenv("FREEPIK_API_KEY")

# 🌟 Render จะกำหนดค่า PORT มาให้ใน Environment Variable
# ถ้าหาไม่เจอ ให้ตั้งค่าเริ่มต้นเป็น 8080
RENDER_PORT = int(os.getenv("PORT", 8080)) 

ALLOWED_CHANNEL_ID = 1424193369646825482 

# *********** ตั้งค่า Discord Bot & Intents ***********
intents = discord.Intents.default()
intents.message_content = True 
bot = commands.Bot(command_prefix=commands.when_mentioned_or(""), intents=intents) 

# *********** Web Server Function (สำหรับ Render) ***********
app = Flask(__name__)

@app.route('/')
def home():
    """Endpoint สำหรับให้ Render ตรวจสอบสถานะ (Health Check)"""
    return "Discord Bot is running!", 200

def run_web_server():
    """ฟังก์ชันที่จะรัน Flask Web Server ใน Thread แยก"""
    print(f"🌐 Starting Web Server on port {RENDER_PORT} for Render Health Check...")
    # host='0.0.0.0' สำคัญมาก เพื่อให้ Web Server รับการเชื่อมต่อจากภายนอกได้
    app.run(host='0.0.0.0', port=RENDER_PORT, debug=False, use_reloader=False)

# *********** ฟังก์ชันสำหรับเรียกใช้ Freepik API (โค้ดเดิม) ***********
def generate_freepik_image(prompt: str):
    # ... (โค้ด Freepik API ยังคงเดิม) ...
    url = "https://api.freepik.com/v1/image/generate" 
    headers = {
        "accept": "image/jpeg",
        "content-type": "application/json",
        "Authorization": f"Bearer {FREEPIK_API_KEY}"
    }
    payload = {
        "prompt": prompt,
        "aspect_ratio": "1:1", 
        "style": "photorealistic", 
    }
    try:
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 200 and response.content:
            return response.content
        else:
            print(f"Freepik API Error: Status {response.status_code}, Response: {response.text}")
            return None
    except Exception as e:
        print(f"An error occurred during API call: {e}")
        return None

# *********** Event & Slash Command (โค้ดเดิม) ***********
@bot.event
async def on_ready():
    print(f'🤖 บอทเชื่อมต่อแล้ว: {bot.user}')
    print(f'🔒 บอทถูกจำกัดการใช้งานใน Channel ID: {ALLOWED_CHANNEL_ID}')
    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} slash commands.")
    except Exception as e:
        print(f"❌ Failed to sync slash commands: {e}")

@bot.tree.command(name="generate", description="สร้างรูปภาพจากข้อความ Prompt โดยใช้ Freepik API")
@app_commands.describe(
    prompt="คำอธิบายของรูปภาพที่คุณต้องการสร้าง (ภาษาอังกฤษ)"
)
async def generate_slash(interaction: discord.Interaction, prompt: str):
    
    if interaction.channel_id != ALLOWED_CHANNEL_ID:
        await interaction.response.send_message(
            f"❌ คำสั่ง **/generate** ใช้ได้เฉพาะในช่องทางที่อนุญาตเท่านั้น!",
            ephemeral=True 
        )
        return
    
    await interaction.response.defer() 

    image_bytes = await bot.loop.run_in_executor(
        None, generate_freepik_image, prompt
    )
    
    if image_bytes:
        image_file = discord.File(io.BytesIO(image_bytes), filename="freepik_image.jpg")
        await interaction.followup.send(
            f"✅ รูปภาพที่สร้างโดย Freepik จาก prompt: **{prompt}**",
            file=image_file
        )
    else:
        await interaction.followup.send(
            f"❌ ไม่สามารถเจนรูปภาพได้ โปรดตรวจสอบ Prompt หรือ Freepik API Key.",
            ephemeral=True
        )

# *********** รันบอท ***********
if __name__ == "__main__":
    if not DISCORD_TOKEN or not FREEPIK_API_KEY:
        print("🚨 ERROR: กรุณาตั้งค่า DISCORD_TOKEN และ FREEPIK_API_KEY ใน Environment Variables")
    else:
        # 1. เริ่ม Web Server ใน Thread แยก (เพื่อให้รันพร้อมกับ Discord Bot ได้)
        server_thread = threading.Thread(target=run_web_server)
        server_thread.start()
        
        # 2. เริ่ม Discord Bot ใน Main Thread
        bot.run(DISCORD_TOKEN)
