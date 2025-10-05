import os
import requests
import io
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
import threading
from flask import Flask 
import time 

# โหลดตัวแปรสภาพแวดล้อม
load_dotenv()

# *********** 1. ตั้งค่า Environment Variables & Constants ***********
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
FREEPIK_API_KEY = os.getenv("FREEPIK_API_KEY")

# 🌟 PORT สำหรับ Render Web Service
RENDER_PORT = int(os.getenv("PORT", 8080)) 

# 🔒 Channel ID ที่บอทจะตอบสนองเท่านั้น 
# ❗ ต้องเปลี่ยนเป็น Channel ID ที่ถูกต้อง
ALLOWED_CHANNEL_ID = 1424193369646825482 

# *********** 2. ตั้งค่า Discord Bot & Intents ***********
intents = discord.Intents.default()
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
    app.run(host='0.0.0.0', port=RENDER_PORT, debug=False, use_reloader=False)


# *********** 4. ฟังก์ชันสำหรับเรียกใช้ Freepik Mystic API (Asynchronous Polling) ***********

def check_mystic_status(job_id: str):
    """ฟังก์ชัน Polling เพื่อตรวจสอบสถานะงานสร้างภาพ"""
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
            
            # 🟢 บรรทัด Debug ที่สำคัญที่สุดในการหาปัญหา
            print(f"DEBUG: Polling Status Check - HTTP {response.status_code}")
            print(f"DEBUG: Polling Response: {data}")

            if response.status_code == 200:
                status = data.get("data", {}).get("status")
                
                if status == "completed":
                    print("DEBUG: Image completed successfully!")
                    
                    # 💥 การแก้ไขสำคัญ: ดึง URL จาก 'generated' array (ตาม Log ที่สำเร็จ)
                    image_url = None
                    generated_images = data.get("data", {}).get("generated")
                    if isinstance(generated_images, list) and len(generated_images) > 0:
                        image_url = generated_images[0]
                    # สำรอง: ดึงจาก result.image_url (กรณี Freepik เปลี่ยนโครงสร้าง)
                    elif data.get("data", {}).get("result", {}).get("image_url"):
                         image_url = data.get("data", {}).get("result", {}).get("image_url")

                    print("DEBUG: Final Image URL:", image_url)
                    return image_url

                elif status in ["failed", "cancelled"]:
                    # 🚨 ถ้า Freepik ตอบ failed/cancelled
                    print(f"DEBUG: Mystic job failed or cancelled. Final Status: {status}")
                    return None 
            else:
                # Log ข้อผิดพลาดของ Polling
                print(f"Mystic Status Check Error: Status {response.status_code}, Response: {response.text}")
                return None
        except Exception as e:
            print(f"An error occurred during Mystic Status Check: {e}")
            return None
            
    print("Mystic generation timed out after 60 seconds.")
    return None

def generate_mystic_image(prompt: str):
    """ส่งคำสั่งสร้างภาพ Mystic และทำการ Polling จนกว่าจะเสร็จ"""
    url = "https://api.freepik.com/v1/ai/mystic"
    headers = {
        "content-type": "application/json",
        "x-freepik-api-key": FREEPIK_API_KEY 
    }

    payload = {
        "prompt": prompt,
        "resolution": "1k", # เลือก 1k เพื่อความเร็วในการทดสอบ
        "aspect_ratio": "square_1_1", 
        "model": "realism" 
    }
    
    try:
        # 1. ส่งคำสั่งสร้าง
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code in [200, 202]: 
            job_id = response.json().get("data", {}).get("task_id")
            
            print("DEBUG: Job Submit Response:", response.json())

            if not job_id:
                print("Mystic failed to return a task_id/job_id.")
                print("Mystic Response Content:", response.text) 
                return None
            
            # 2. ตรวจสอบสถานะงาน
            image_url = check_mystic_status(job_id)
            
            if image_url:
                # 3. ดาวน์โหลดรูปภาพ
                image_response = requests.get(image_url)
                if image_response.status_code == 200:
                    return image_response.content
                
            return None
            
        else:
            # 🚨 บรรทัด Debug สำหรับการส่งคำสั่งครั้งแรก
            print(f"Mystic Submit Error: Status {response.status_code}")
            print("Mystic Response Content:", response.text) 
            return None
            
    except Exception as e:
        print(f"An error occurred during Mystic API call: {e}")
        return None


# *********** 5. Discord Events - การแก้ไขสุดท้ายเพื่อบังคับ Sync ***********
@bot.event
async def on_ready():
    print(f'🤖 บอทเชื่อมต่อแล้ว: {bot.user}')
    print(f'🔒 บอทถูกจำกัดการใช้งานใน Channel ID: {ALLOWED_CHANNEL_ID}')
    try:
        # 💥 บังคับล้างและลงทะเบียนคำสั่งใหม่ทั้งหมด
        bot.tree.clear_commands(guild=None)
        synced = await bot.tree.sync() 
        print(f"✅ FINAL SYNC: Synced {len(synced)} slash commands. การ Sync เสร็จสมบูรณ์.")
    except Exception as e:
        print(f"❌ Failed to perform final slash command sync: {e}")


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
    
    # 🌟 ต้อง Defer ทันทีเพื่อหลีกเลี่ยง 404 Unknown Interaction
    await interaction.response.defer() 

    print(f"DEBUG: Starting Mystic API call with prompt: {prompt}")

    # เรียกใช้ฟังก์ชัน Mystic ใน Thread แยก
    image_bytes = await bot.loop.run_in_executor(
        None, generate_mystic_image, prompt
    )
    
    # ตอบกลับไปยัง Discord
    if image_bytes:
        image_file = discord.File(io.BytesIO(image_bytes), filename="freepik_mystic_image.jpg")
        
        await interaction.followup.send(
            f"✅ รูปภาพ Mystic ที่สร้างโดย Freepik จาก prompt: **{prompt}**",
            file=image_file
        )
    else:
        # 🚨 แจ้งผู้ใช้ว่าล้มเหลวและให้ตรวจสอบ Log
        await interaction.followup.send(
            f"❌ ไม่สามารถเจนรูปภาพได้ (อาจจะ Timeout หรือ Freepik ไม่สามารถสร้างได้) โปรดตรวจสอบ **Log ใน Render Worker** เพื่อดูสาเหตุ.",
            ephemeral=True
        )

# *********** 7. รันบอท ***********
if __name__ == "__main__":
    if not DISCORD_TOKEN or not FREEPIK_API_KEY:
        print("🚨 ERROR: กรุณาตั้งค่า DISCORD_TOKEN และ FREEPIK_API_KEY ใน Environment Variables")
    else:
        server_thread = threading.Thread(target=run_web_server)
        server_thread.start()
        bot.run(DISCORD_TOKEN)
