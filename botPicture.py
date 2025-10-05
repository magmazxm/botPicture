import os
import requests
from io import BytesIO
from discord import File, Intents
from discord.ext import commands
from dotenv import load_dotenv

# โหลดตัวแปรสภาพแวดล้อม
load_dotenv()

# *********** ตั้งค่า Environment Variables ***********
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
FREEPIK_API_KEY = os.getenv("FREEPIK_API_KEY")

# *********** ตั้งค่า Channel ID ที่อนุญาต ***********
# Channel ID ที่บอทจะตอบสนองเท่านั้น (จากที่คุณกำหนด: 1424193369646825482)
ALLOWED_CHANNEL_ID = 1424193369646825482 

# *********** ตั้งค่า Discord Bot ***********
intents = Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# *********** ฟังก์ชันสำหรับเรียกใช้ Freepik API ***********
def generate_freepik_image(prompt: str):
    """เรียก Freepik API เพื่อเจนรูปภาพ"""
    # ... (โค้ดส่วนนี้ยังคงเดิม) ...
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


# *********** Event เมื่อ Bot พร้อมใช้งาน ***********
@bot.event
async def on_ready():
    """แสดงข้อความเมื่อบอทเชื่อมต่อสำเร็จ"""
    print(f'🤖 บอทเชื่อมต่อแล้ว: {bot.user}')
    print(f'🔒 บอทถูกจำกัดการใช้งานใน Channel ID: {ALLOWED_CHANNEL_ID}')


# *********** คำสั่งสำหรับเจนรูปภาพ พร้อมการตรวจสอบ Channel ID ***********
@bot.command(name='generate', help='เจนรูปภาพจากข้อความ. ใช้: !generate [prompt]')
async def generate(ctx, *, prompt: str):
    """จัดการคำสั่ง !generate [prompt] และตรวจสอบ Channel ID"""

    # ตรวจสอบ Channel ID ก่อนดำเนินการ
    if ctx.channel.id != ALLOWED_CHANNEL_ID:
        # บอทจะไม่ตอบสนองในช่องทางอื่น หรือคุณจะส่งข้อความแจ้งเตือนก็ได้
        # await ctx.send(f"❌ คำสั่งนี้ใช้ได้เฉพาะในช่องทางที่มี ID {ALLOWED_CHANNEL_ID} เท่านั้น!", delete_after=5) 
        return # ออกจากฟังก์ชันทันที
    
    # 1. แจ้งผู้ใช้ว่ากำลังดำเนินการ
    await ctx.send(f"⏳ กำลังเจนรูปภาพจาก prompt: **{prompt}**...")

    # 2. เรียกใช้ Freepik API
    image_bytes = await bot.loop.run_in_executor(
        None, generate_freepik_image, prompt
    )
    
    # 3. ตรวจสอบและส่งรูปภาพกลับไปที่ Discord
    if image_bytes:
        image_file = File(BytesIO(image_bytes), filename="freepik_image.jpg")
        await ctx.send(
            f"✅ รูปภาพที่สร้างโดย Freepik จาก prompt: **{prompt}**",
            file=image_file
        )
    else:
        await ctx.send(f"❌ ไม่สามารถเจนรูปภาพได้ โปรดตรวจสอบ prompt หรือ Freepik API Key.")

# *********** รันบอท ***********
if __name__ == "__main__":
    if not DISCORD_TOKEN or not FREEPIK_API_KEY:
        print("🚨 ERROR: กรุณาตั้งค่า DISCORD_TOKEN และ FREEPIK_API_KEY ใน Environment Variables")
    else:
        bot.run(DISCORD_TOKEN)
