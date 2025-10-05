import os
import requests
import io
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
import threading
from flask import Flask

# โหลดตัวแปรสภาพแวดล้อม
load_dotenv()

# *********** 1. ตั้งค่า Environment Variables & Constants ***********
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
FREEPIK_API_KEY = os.getenv("FREEPIK_API_KEY")

# 🌟 PORT สำหรับ Render Web Service
# Render จะกำหนดค่า PORT มาให้ใน Environment Variable 
RENDER_PORT = int(os.getenv("PORT", 8080)) 

# 🔒 Channel ID ที่บอทจะตอบสนองเท่านั้น (1424193369646825482)
ALLOWED_CHANNEL_ID = 1424193369646825482 

# *********** 2. ตั้งค่า Discord Bot & Intents ***********
intents = discord.Intents.default()
# จำเป็นสำหรับบอทที่ใช้ Prefix Commands แต่สำหรับ Slash Command อาจไม่จำเป็น
# อย่างไรก็ตาม หากมีปัญหา Intention ให้เปิดไว้ตามที่เคยแก้ไขไป
intents.message_content = True 
bot = commands.Bot(command_prefix=commands.when_mentioned_or(""), intents=intents) 


# *********** 3. Web Server Function (สำหรับ Render Health Check) ***********
app = Flask(__name__)

@app.route('/')
def home():
    """Endpoint สำหรับให้ Render ตรวจสอบสถานะ (Health Check)"""
    return "Discord Bot is running!", 200

def run_web_server():
    """ฟังก์ชันที่รัน Flask Web Server ใน Thread แยกเพื่อเปิด Port"""
    print(f"🌐 Starting Web Server on port {RENDER_PORT} for Render Health Check...")
    # host='0.0.0.0' สำคัญมาก: เพื่อให้ Web Server รับการเชื่อมต่อจากภายนอกได้
    # use_reloader=False: ป้องกันการรันซ้ำเมื่อใช้ threading
    app.run(host='0.0.0.0', port=RENDER_PORT, debug=False, use_reloader=False)

# *********** 4. ฟังก์ชันสำหรับเรียกใช้ Freepik API ***********
def generate_freepik_image(prompt: str):
    """เรียก Freepik API เพื่อเจนรูปภาพ โดยใช้ Header ที่ถูกต้อง"""
    # 🟢 ใช้ Endpoint สำหรับการสร้างแบบ Synchronous 
    url = "https://api.freepik.com/v1/image/generate" 
    
    # 🟢 ใช้ Header ที่ยืนยันแล้วว่าถูกต้องสำหรับ Freepik Key ของคุณ
    headers = {
        "accept": "image/jpeg",
        "content-type": "application/json",
        "x-freepik-api-key": FREEPIK_API_KEY 
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
            # 🚨 บรรทัด Debug ที่สำคัญที่สุดในการหาปัญหา API Key
            print(f"Freepik API Error: Status {response.status_code}")
            print("Freepik Response Content:", response.text) 
            return None
    except Exception as e:
        print(f"An error occurred during API call: {e}")
        return None

# *********** 5. Discord Events ***********
@bot.event
async def on_ready():
    """แสดงข้อความเมื่อบอทเชื่อมต่อสำเร็จ และทำการ Sync Slash Commands"""
    print(f'🤖 บอทเชื่อมต่อแล้ว: {bot.user}')
    print(f'🔒 บอทถูกจำกัดการใช้งานใน Channel ID: {ALLOWED_CHANNEL_ID}')
    
    # ทำการ Sync Slash Commands
    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} slash commands.")
    except Exception as e:
        print(f"❌ Failed to sync slash commands: {e}")

# *********** 6. Slash Command ***********
@bot.tree.command(name="generate", description="สร้างรูปภาพจากข้อความ Prompt โดยใช้ Freepik API")
@app_commands.describe(
    prompt="คำอธิบายของรูปภาพที่คุณต้องการสร้าง (ภาษาอังกฤษ)"
)
async def generate_slash(interaction: discord.Interaction, prompt: str):
    """จัดการคำสั่ง /generate [prompt] พร้อมการตรวจสอบ Channel ID"""
    
    # ตรวจสอบ Channel ID (ล็อกช่อง)
    if interaction.channel_id != ALLOWED_CHANNEL_ID:
        await interaction.response.send_message(
            f"❌ คำสั่ง **/generate** ใช้ได้เฉพาะในช่องทางที่อนุญาตเท่านั้น!",
            ephemeral=True
        )
        return
    
    # 🌟 แจ้ง Discord ว่ากำลังประมวลผล (ป้องกัน Time-out 10062)
    await interaction.response.defer() 

    # เรียกใช้ Freepik API ใน Thread แยก
    image_bytes = await bot.loop.run_in_executor(
        None, generate_freepik_image, prompt
    )
    
    # ส่งผลลัพธ์กลับ
    if image_bytes:
        image_file = discord.File(io.BytesIO(image_bytes), filename="freepik_image.jpg")
        
        # ใช้ followup.send หลัง defer()
        await interaction.followup.send(
            f"✅ รูปภาพที่สร้างโดย Freepik จาก prompt: **{prompt}**",
            file=image_file
        )
    else:
        await interaction.followup.send(
            f"❌ ไม่สามารถเจนรูปภาพได้ โปรดตรวจสอบ Prompt หรือ Freepik API Key.",
            ephemeral=True
        )

# *********** 7. รันบอท ***********
if __name__ == "__main__":
    if not DISCORD_TOKEN or not FREEPIK_API_KEY:
        print("🚨 ERROR: กรุณาตั้งค่า DISCORD_TOKEN และ FREEPIK_API_KEY ใน Environment Variables")
    else:
        # 1. เริ่ม Web Server ใน Thread แยก
        server_thread = threading.Thread(target=run_web_server)
        server_thread.start()
        
        # 2. เริ่ม Discord Bot ใน Main Thread
        bot.run(DISCORD_TOKEN)
