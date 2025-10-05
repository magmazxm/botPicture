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

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
FREEPIK_API_KEY = os.getenv("FREEPIK_API_KEY")
RENDER_PORT = int(os.getenv("PORT", 8080)) 

ALLOWED_CHANNEL_ID = 1424193369646825482 

intents = discord.Intents.default()
intents.message_content = True 
bot = commands.Bot(command_prefix=commands.when_mentioned_or(""), intents=intents) 

app = Flask(__name__)

@app.route('/')
def home():
    return "Discord Bot is running!", 200

def run_web_server():
    print(f"🌐 Starting Web Server on port {RENDER_PORT} for Render Health Check...")
    app.run(host='0.0.0.0', port=RENDER_PORT, debug=False, use_reloader=False)


# *********** Freepik Mystic API ***********
def check_mystic_status(job_id: str):
    url = f"https://api.freepik.com/v1/ai/mystic/{job_id}"
    headers = {
        "x-freepik-api-key": FREEPIK_API_KEY 
    }

    max_wait_time = 60
    start_time = time.time()
    
    while time.time() - start_time < max_wait_time:
        time.sleep(3)
        try:
            response = requests.get(url, headers=headers)
            data = response.json()
            
            print(f"DEBUG: Polling Status Check - HTTP {response.status_code}")
            print(f"DEBUG: Polling Response: {data}")

            if response.status_code == 200:
                status = data.get("data", {}).get("status")
                
                if status == "completed":
                    print("DEBUG: Image completed successfully!")
                    result = data.get("data", {}).get("result", {})

                    # ✅ ดักหลายกรณี
                    image_url = result.get("image_url")
                    if not image_url:
                        images = result.get("images")
                        if isinstance(images, list) and len(images) > 0:
                            image_url = images[0].get("url")

                    print("DEBUG: Final Image URL:", image_url)
                    return image_url

                elif status in ["failed", "cancelled"]:
                    print(f"DEBUG: Mystic job failed or cancelled. Final Status: {status}")
                    return None 
            else:
                print(f"Mystic Status Check Error: {response.status_code}, Response: {response.text}")
                return None
        except Exception as e:
            print(f"An error occurred during Mystic Status Check: {e}")
            return None
            
    print("Mystic generation timed out after 60 seconds.")
    return None

def generate_mystic_image(prompt: str):
    url = "https://api.freepik.com/v1/ai/mystic"
    headers = {
        "content-type": "application/json",
        "x-freepik-api-key": FREEPIK_API_KEY 
    }

    payload = {
        "prompt": prompt,
        "resolution": "1k",
        "aspect_ratio": "square_1_1", 
        "model": "realism" 
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code in [200, 202]: 
            job_id = response.json().get("data", {}).get("task_id")
            
            print("DEBUG: Job Submit Response:", response.json())

            if not job_id:
                print("Mystic failed to return a task_id/job_id.")
                return None
            
            image_url = check_mystic_status(job_id)
            
            if image_url:
                image_response = requests.get(image_url)
                if image_response.status_code == 200:
                    return image_response.content
                
            return None
            
        else:
            print(f"Mystic Submit Error: Status {response.status_code}")
            print("Mystic Response Content:", response.text) 
            return None
            
    except Exception as e:
        print(f"An error occurred during Mystic API call: {e}")
        return None


# *********** Discord Events ***********
@bot.event
async def on_ready():
    print(f'🤖 บอทเชื่อมต่อแล้ว: {bot.user}')
    print(f'🔒 บอทถูกจำกัดการใช้งานใน Channel ID: {ALLOWED_CHANNEL_ID}')
    try:
        synced = await bot.tree.sync() 
        print(f"✅ Synced {len(synced)} slash commands.")
    except Exception as e:
        print(f"❌ Failed to sync slash commands: {e}")


# *********** Slash Command ***********
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

    print(f"DEBUG: Starting Mystic API call with prompt: {prompt}")

    image_bytes = await bot.loop.run_in_executor(
        None, generate_mystic_image, prompt
    )
    
    if image_bytes:
        image_file = discord.File(io.BytesIO(image_bytes), filename="freepik_mystic_image.jpg")
        await interaction.followup.send(
            f"✅ รูปภาพ Mystic ที่สร้างโดย Freepik จาก prompt: **{prompt}**",
            file=image_file
        )
    else:
        await interaction.followup.send(
            f"❌ ไม่สามารถเจนรูปภาพได้ โปรดตรวจสอบ **Log ใน Render Worker** เพื่อดูสาเหตุจาก Freepik.",
            ephemeral=True
        )


# *********** Run Bot ***********
if __name__ == "__main__":
    if not DISCORD_TOKEN or not FREEPIK_API_KEY:
        print("🚨 ERROR: กรุณาตั้งค่า DISCORD_TOKEN และ FREEPIK_API_KEY ใน Environment Variables")
    else:
        server_thread = threading.Thread(target=run_web_server)
        server_thread.start()
        bot.run(DISCORD_TOKEN)
