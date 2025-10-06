import os
import discord
from discord.ext import commands
import requests
from dotenv import load_dotenv

load_dotenv()

# โหลดตัวแปรสภาพแวดล้อม
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
FREEPIK_API_KEY = os.getenv("FREEPIK_API_KEY") # สมมติว่า FreePik มี API นี้

# กำหนด ID ช่องที่อนุญาต
ALLOWED_CHANNEL_ID = 1424193369646825482 # แทนที่ด้วย ID ช่องของคุณ

# ตั้งค่า intents
intents = discord.Intents.default()
intents.message_content = True # ต้องเปิดใช้งานใน Discord Developer Portal ด้วย!

bot = commands.Bot(command_prefix="!", intents=intents)

# URL สมมติสำหรับ FreePik API
# คุณจะต้องแทนที่ด้วย URL จริงของ FreePik Text-to-Image และ Image-to-Image API
FREEPIK_TEXT_TO_IMAGE_API_URL = "https://api.freepik.com/v1/image/generate"
FREEPIK_IMAGE_EDIT_API_URL = "https://api.freepik.com/v1/image/edit" # สมมติว่ามี

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')
    print(f'Bot ID: {bot.user.id}')
    print('Bot is ready!')

@bot.before_invoke
async def check_channel(ctx):
    # ตรวจสอบว่าคำสั่งถูกเรียกใช้ในช่องที่อนุญาตหรือไม่
    if ctx.channel.id != ALLOWED_CHANNEL_ID:
        await ctx.send(f"บอทนี้สามารถใช้งานได้เฉพาะในช่อง <#{ALLOWED_CHANNEL_ID}> เท่านั้นค่ะ")
        raise commands.CommandError("Command used in forbidden channel.")
    return True

@bot.command(name="genimage", help="สร้างรูปภาพจากข้อความ (เช่น !genimage amazing sunset over mountains)")
async def generate_image(ctx, *, prompt: str):
    await ctx.send(f"กำลังสร้างรูปภาพสำหรับ: '{prompt}' โปรดรอสักครู่...")
    
    headers = {
        "Authorization": f"Bearer {FREEPIK_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "prompt": prompt,
        "width": 1024, # ปรับขนาดได้ตามต้องการ
        "height": 1024,
        "quality": "standard" # หรือ "hd" ถ้ามี
    }

    try:
        response = requests.post(FREEPIK_TEXT_TO_IMAGE_API_URL, headers=headers, json=payload)
        response.raise_for_status() # ตรวจสอบข้อผิดพลาด HTTP

        data = response.json()
        
        # สมมติว่า FreePik API ส่งคืน URL ของรูปภาพ
        # คุณอาจจะต้องปรับเปลี่ยนตามโครงสร้างการตอบกลับจริงของ FreePik
        image_url = data.get("image_url") or data.get("url") 

        if image_url:
            await ctx.send(f"นี่คือรูปภาพของคุณ: http://googleusercontent.com/image_generation_content/0
