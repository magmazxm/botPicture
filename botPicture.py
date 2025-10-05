import os
import requests
import io
import discord
from discord.ext import commands
from discord import app_commands # Import ส่วนที่จำเป็นสำหรับ Slash Commands
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
intents = discord.Intents.default()
# MESSAGE CONTENT INTENT ยังจำเป็นสำหรับบอทที่อ่านข้อความ (ถึงแม้จะเปลี่ยนเป็น Slash Command แล้ว) 
# แต่ในอนาคต หากคุณใช้แต่ Slash Command อย่างเดียว อาจไม่จำเป็นต้องเปิดถ้าไม่ใช้ข้อมูลในข้อความ
# อย่างไรก็ตาม เพื่อความชัวร์ ให้เปิดไว้ตามที่แก้ไขปัญหา Privileged Intents ไปแล้ว
intents.message_content = True 
# ในการใช้ Slash Command ให้สร้าง Bot โดยไม่ต้องมี command_prefix
bot = commands.Bot(command_prefix=commands.when_mentioned_or(""), intents=intents) 


# *********** ฟังก์ชันสำหรับเรียกใช้ Freepik API ***********
def generate_freepik_image(prompt: str):
    """เรียก Freepik API เพื่อเจนรูปภาพ"""
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
    """แสดงข้อความเมื่อบอทเชื่อมต่อสำเร็จ และทำการ Sync Slash Commands"""
    print(f'🤖 บอทเชื่อมต่อแล้ว: {bot.user}')
    print(f'🔒 บอทถูกจำกัดการใช้งานใน Channel ID: {ALLOWED_CHANNEL_ID}')
    
    # 🌟 ทำการ Sync Slash Commands
    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} slash commands.")
    except Exception as e:
        print(f"❌ Failed to sync slash commands: {e}")

# *********** Slash Command สำหรับเจนรูปภาพ ***********
@bot.tree.command(name="generate", description="สร้างรูปภาพจากข้อความ Prompt โดยใช้ Freepik API")
@app_commands.describe(
    prompt="คำอธิบายของรูปภาพที่คุณต้องการสร้าง (ภาษาอังกฤษ)"
)
async def generate_slash(interaction: discord.Interaction, prompt: str):
    """จัดการคำสั่ง /generate [prompt] และตรวจสอบ Channel ID"""
    
    # 1. ตรวจสอบ Channel ID 
    if interaction.channel_id != ALLOWED_CHANNEL_ID:
        # ใช้ interaction.response.send_message สำหรับ Slash Commands
        await interaction.response.send_message(
            f"❌ คำสั่ง **/generate** ใช้ได้เฉพาะในช่องทางที่มี ID **{ALLOWED_CHANNEL_ID}** เท่านั้น!",
            ephemeral=True # ตั้งค่าให้ข้อความนี้มีแค่ผู้ใช้ที่เห็นเท่านั้น
        )
        return
    
    # 2. แจ้งผู้ใช้ว่ากำลังดำเนินการ
    # ใช้ interaction.response.defer() เพื่อบอก Discord ว่ากำลังประมวลผลอยู่
    await interaction.response.defer() 

    # 3. เรียกใช้ Freepik API
    image_bytes = await bot.loop.run_in_executor(
        None, generate_freepik_image, prompt
    )
    
    # 4. ตรวจสอบและส่งรูปภาพกลับไปที่ Discord
    if image_bytes:
        image_file = discord.File(io.BytesIO(image_bytes), filename="freepik_image.jpg")
        
        # ใช้ interaction.followup.send เพื่อส่งผลลัพธ์หลังจาก defer
        await interaction.followup.send(
            f"✅ รูปภาพที่สร้างโดย Freepik จาก prompt: **{prompt}**",
            file=image_file
        )
    else:
        await interaction.followup.send(
            f"❌ ไม่สามารถเจนรูปภาพได้ โปรดตรวจสอบ Prompt หรือ Freepik API Key.",
            ephemeral=True # ตั้งค่าให้ข้อความข้อผิดพลาดมีแค่ผู้ใช้ที่เห็นเท่านั้น
        )

# *********** รันบอท ***********
if __name__ == "__main__":
    if not DISCORD_TOKEN or not FREEPIK_API_KEY:
        print("🚨 ERROR: กรุณาตั้งค่า DISCORD_TOKEN และ FREEPIK_API_KEY ใน Environment Variables")
    else:
        bot.run(DISCORD_TOKEN)
