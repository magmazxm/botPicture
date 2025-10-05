import os
import requests
import io
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
import threading
from flask import Flask
import time # 👈 เพิ่มการใช้ time สำหรับการรอระหว่าง Polling

# โหลดตัวแปรสภาพแวดล้อม
load_dotenv()

# *********** 1. ตั้งค่า Environment Variables & Constants ***********
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
FREEPIK_API_KEY = os.getenv("FREEPIK_API_KEY")
RENDER_PORT = int(os.getenv("PORT", 8080)) 
ALLOWED_CHANNEL_ID = 1424193369646825482 

# *********** 2. ตั้งค่า Discord Bot & Intents ***********
intents = discord.Intents.default()
intents.message_content = True 
bot = commands.Bot(command_prefix=commands.when_mentioned_or(""), intents=intents) 

# *********** 3. Web Server Function (โค้ดเดิม) ***********
app = Flask(__name__)

@app.route('/')
def home():
    return "Discord Bot is running!", 200

def run_web_server():
    print(f"🌐 Starting Web Server on port {RENDER_PORT} for Render Health Check...")
    app.run(host='0.0.0.0', port=RENDER_PORT, debug=False, use_reloader=False)


# *********** 4. ฟังก์ชันสำหรับเรียกใช้ Freepik Mystic API (Mystic Polling) ***********

def check_mystic_status(job_id: str):
    """ฟังก์ชัน Polling เพื่อตรวจสอบสถานะงานสร้างภาพ"""
    # 🟢 Endpoint สำหรับตรวจสอบสถานะ
    url = f"https://api.freepik.com/v1/ai/mystic/{job_id}"
    headers = {
        "x-freepik-api-key": FREEPIK_API_KEY 
    }

    # จำกัดเวลา Polling (สูงสุด 60 วินาที)
    max_wait_time = 60
    start_time = time.time()
    
    while time.time() - start_time < max_wait_time:
        time.sleep(3) # รอ 3 วินาทีก่อนเช็คสถานะอีกครั้ง
        try:
            response = requests.get(url, headers=headers)
            data = response.json()

            if response.status_code == 200:
                status = data.get("status")
                
                if status == "completed":
                    # 🟢 ถ้าเสร็จแล้ว ให้คืนค่า URL ของรูปภาพ
                    return data.get("result", {}).get("image_url")
                elif status == "failed" or status == "cancelled":
                    return None # เกิดข้อผิดพลาด
                # ถ้า status เป็น "pending" หรือ "running" ให้วนลูปต่อไป

            else:
                print(f"Mystic Status Check Error: Status {response.status_code}, Response: {response.text}")
                return None

        except Exception as e:
            print(f"An error occurred during Mystic Status Check: {e}")
            return None
            
    print("Mystic generation timed out after 60 seconds.")
    return None # Time out

def generate_mystic_image(prompt: str):
    """ส่งคำสั่งสร้างภาพ Mystic และทำการ Polling จนกว่าจะเสร็จ"""
    # 🟢 Endpoint สำหรับส่งคำสั่งสร้าง
    url = "https://api.freepik.com/v1/ai/mystic"
    headers = {
        "content-type": "application/json",
        "x-freepik-api-key": FREEPIK_API_KEY 
    }

    payload = {
        "prompt": prompt,
        "resolution": "1k", # เลือก resolution ที่เล็กที่สุดเพื่อความเร็ว
        "aspect_ratio": "square_1_1", 
        "model": "realism" 
    }
    
    try:
        # 1. ส่งคำสั่งสร้าง
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code == 202: # 🟢 202 Accepted คือสำเร็จ
            job_id = response.json().get("job_id")
            if not job_id:
                print("Mystic failed to return a job_id.")
                return None
            
            # 2. ตรวจสอบสถานะงาน
            image_url = check_mystic_status(job_id)
            
            if image_url:
                # 3. ดาวน์โหลดรูปภาพจาก URL ที่ได้
                image_response = requests.get(image_url)
                if image_response.status_code == 200:
                    return image_response.content
                
            return None # ไม่สามารถดึงรูปภาพได้
            
        else:
            # 🚨 บรรทัด Debug ที่สำคัญที่สุด
            print(f"Mystic Submit Error: Status {response.status_code}")
            print("Mystic Response Content:", response.text) 
            return None
            
    except Exception as e:
        print(f"An error occurred during Mystic API call: {e}")
        return None


# *********** 5. Discord Events (โค้ดเดิม) ***********
@bot.event
async def on_ready():
    print(f'🤖 บอทเชื่อมต่อแล้ว: {bot.user}')
    print(f'🔒 บอทถูกจำกัดการใช้งานใน Channel ID: {ALLOWED_CHANNEL_ID}')
    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} slash commands.")
    except Exception as e:
        print(f"❌ Failed to sync slash commands: {e}")


# *********** 6. Slash Command ***********
@bot.tree.command(name="generate", description="สร้างรูปภาพจากข้อความ Prompt โดยใช้ Freepik Mystic AI")
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

    # 🟢 เรียกใช้ฟังก์ชัน Mystic ใหม่
    image_bytes = await bot.loop.run_in_executor(
        None, generate_mystic_image, prompt # 👈 เปลี่ยนชื่อฟังก์ชันเป็น generate_mystic_image
    )
    
    if image_bytes:
        image_file = discord.File(io.BytesIO(image_bytes), filename="freepik_mystic_image.jpg")
        
        await interaction.followup.send(
            f"✅ รูปภาพ Mystic ที่สร้างโดย Freepik จาก prompt: **{prompt}**",
            file=image_file
        )
    else:
        await interaction.followup.send(
            f"❌ ไม่สามารถเจนรูปภาพได้ โปรดตรวจสอบ **Prompt, Freepik API Key** หรือ **Log ใน Render**",
            ephemeral=True
        )

# *********** 7. รันบอท (โค้ดเดิม) ***********
if __name__ == "__main__":
    if not DISCORD_TOKEN or not FREEPIK_API_KEY:
        print("🚨 ERROR: กรุณาตั้งค่า DISCORD_TOKEN และ FREEPIK_API_KEY ใน Environment Variables")
    else:
        server_thread = threading.Thread(target=run_web_server)
        server_thread.start()
        bot.run(DISCORD_TOKEN)
