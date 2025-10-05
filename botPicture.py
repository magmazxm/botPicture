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


# --- Flask Health Check (คงไว้) ---
app = Flask(__name__)
@app.route('/')
def home():
    return "Discord Bot is running!", 200
def run_web_server():
    app.run(host='0.0.0.0', port=RENDER_PORT, debug=False, use_reloader=False)
# -----------------------------------


# *********** ฟังก์ชันทดสอบ Freepik API (ไม่มี Polling) ***********

def test_freepik_submission(prompt: str):
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
        
        # 🚨 บรรทัด Debug สำคัญที่สุด: พิมพ์ Status และ Response Content ทั้งหมด
        print(f"DEBUG-TEST: Initial Freepik Status: {response.status_code}")
        print("DEBUG-TEST: Full Freepik Response Content:", response.text)
        
        # ส่ง Status กลับไป
        return response.status_code
            
    except Exception as e:
        print(f"An error occurred during Freepik API call: {e}")
        return 500 # รหัสสำหรับ Internal Server Error

# *********** Slash Command ***********
@bot.tree.command(name="testsubmit", description="ทดสอบส่งคำสั่งสร้างภาพไป Freepik และแสดง Log การตอบกลับครั้งแรกเท่านั้น")
@app_commands.describe(
    prompt="คำอธิบายของรูปภาพที่คุณต้องการสร้าง (ภาษาอังกฤษ)"
)
async def test_submit_slash(interaction: discord.Interaction, prompt: str):
    
    if interaction.channel_id != ALLOWED_CHANNEL_ID:
        await interaction.response.send_message(
            f"❌ คำสั่ง **/testsubmit** ใช้ได้เฉพาะในช่องทางที่อนุญาตเท่านั้น!",
            ephemeral=True
        )
        return
    
    await interaction.response.defer() 

    # เรียกใช้ฟังก์ชันทดสอบใน Thread แยก
    status_code = await bot.loop.run_in_executor(
        None, test_freepik_submission, prompt
    )
    
    # ตอบกลับด้วยสถานะที่ได้รับ
    if status_code in [200, 202]:
        await interaction.followup.send(
            f"✅ Submission Successful! Freepik responded with status **{status_code}**. กรุณาตรวจสอบ **Render Log** เพื่อดู Task ID และ JSON Response ทั้งหมด!",
        )
    else:
        await interaction.followup.send(
            f"❌ Submission Failed! Freepik responded with status **{status_code}**. กรุณาตรวจสอบ **Render Log** เพื่อดูข้อผิดพลาด.",
        )

# *********** รันบอท ***********
if __name__ == "__main__":
    if not DISCORD_TOKEN or not FREEPIK_API_KEY:
        print("🚨 ERROR: กรุณาตั้งค่า DISCORD_TOKEN และ FREEPIK_API_KEY ใน Environment Variables")
    else:
        server_thread = threading.Thread(target=run_web_server)
        server_thread.start()
        bot.run(DISCORD_TOKEN)
