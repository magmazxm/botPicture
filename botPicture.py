import os
import requests
from io import BytesIO
from discord import File, Intents
from discord.ext import commands
from dotenv import load_dotenv # ใช้สำหรับรัน local, แต่บน Render จะใช้ Environment Variables โดยตรง

# โหลดตัวแปรสภาพแวดล้อม (สำหรับรัน local)
# บน Render คุณต้องตั้งค่า DISCORD_TOKEN และ FREEPIK_API_KEY ในส่วน Environment Variables
load_dotenv()

# *********** ตั้งค่า Environment Variables ***********
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
FREEPIK_API_KEY = os.getenv("FREEPIK_API_KEY")

# *********** ตั้งค่า Discord Bot ***********
# เปิดใช้งาน Intent ที่จำเป็น (message_content จำเป็นสำหรับการอ่านข้อความคำสั่ง)
intents = Intents.default()
intents.message_content = True

# สร้าง Bot instance และกำหนด prefix (เช่น !generate)
bot = commands.Bot(command_prefix='!', intents=intents)

# *********** ฟังก์ชันสำหรับเรียกใช้ Freepik API ***********
def generate_freepik_image(prompt: str):
    """เรียก Freepik API เพื่อเจนรูปภาพ และคืนค่าเป็นไบนารีข้อมูลรูปภาพ"""
    
    # URL และ Headers สำหรับ Freepik Image Generation API
    url = "https://api.freepik.com/v1/image/generate" 
    headers = {
        "accept": "image/jpeg",  # รูปแบบที่ต้องการรับคืนเป็นไบนารี
        "content-type": "application/json",
        "Authorization": f"Bearer {FREEPIK_API_KEY}"
    }

    # Payload (ข้อมูลที่จะส่งไปยัง API)
    # ปรับค่า 'aspect_ratio' และ 'style' ตามที่คุณต้องการ
    payload = {
        "prompt": prompt,
        "aspect_ratio": "1:1",  # ตัวอย่าง: 1:1, 16:9, 4:3
        "style": "photorealistic", # ตัวอย่าง: photorealistic, 3d-render, cartoon
    }
    
    try:
        # ส่ง request ไปยัง Freepik API
        response = requests.post(url, headers=headers, json=payload)
        
        # ตรวจสอบว่า API ตอบกลับมาสำเร็จ (status code 200)
        if response.status_code == 200 and response.content:
            # คืนค่าไบนารีของรูปภาพ
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

# *********** คำสั่งสำหรับเจนรูปภาพ ***********
@bot.command(name='generate', help='เจนรูปภาพจากข้อความ. ใช้: !generate [prompt]')
async def generate(ctx, *, prompt: str):
    """จัดการคำสั่ง !generate [prompt]"""
    
    # 1. แจ้งผู้ใช้ว่ากำลังดำเนินการ
    await ctx.send(f"⏳ กำลังเจนรูปภาพจาก prompt: **{prompt}**...")

    # 2. เรียกใช้ Freepik API
    image_bytes = await bot.loop.run_in_executor(
        None, generate_freepik_image, prompt
    )
    
    # 3. ตรวจสอบและส่งรูปภาพกลับไปที่ Discord
    if image_bytes:
        # สร้างไฟล์ Discord จากไบนารีข้อมูลรูปภาพ
        image_file = File(BytesIO(image_bytes), filename="freepik_image.jpg")
        
        # ส่งรูปภาพกลับไปยัง Channel
        await ctx.send(
            f"✅ รูปภาพที่สร้างโดย Freepik จาก prompt: **{prompt}**",
            file=image_file
        )
    else:
        # แจ้งข้อผิดพลาด
        await ctx.send(f"❌ ไม่สามารถเจนรูปภาพได้ โปรดตรวจสอบ prompt หรือ Freepik API Key.")

# *********** รันบอท ***********
if __name__ == "__main__":
    if not DISCORD_TOKEN or not FREEPIK_API_KEY:
        print("🚨 ERROR: กรุณาตั้งค่า DISCORD_TOKEN และ FREEPIK_API_KEY ใน Environment Variables")
    else:
        # รันบอท
        bot.run(DISCORD_TOKEN)
