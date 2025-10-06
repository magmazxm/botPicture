import { Client, GatewayIntentBits, REST, Routes, SlashCommandBuilder } from 'discord.js';
import fetch from 'node-fetch';
import dotenv from 'dotenv';

dotenv.config();

const client = new Client({
  intents: [GatewayIntentBits.Guilds, GatewayIntentBits.GuildMessages]
});

// คำสั่ง /gen และ /edit
const commands = [
  new SlashCommandBuilder()
    .setName('gen')
    .setDescription('Generate an image from Freepik API')
    .addStringOption(option =>
      option.setName('prompt')
        .setDescription('คำอธิบายภาพ')
        .setRequired(true)
    ),
  new SlashCommandBuilder()
    .setName('edit')
    .setDescription('Edit an existing image (ถ้า Freepik API รองรับ)')
    .addStringOption(option =>
      option.setName('prompt')
        .setDescription('สิ่งที่จะให้แก้')
        .setRequired(true)
    )
].map(cmd => cmd.toJSON());

// สมัคร slash commands ตอน start
client.once('ready', async () => {
  console.log(`✅ Logged in as ${client.user.tag}`);

  const rest = new REST({ version: '10' }).setToken(process.env.DISCORD_TOKEN);

  try {
    await rest.put(
      Routes.applicationGuildCommands(process.env.CLIENT_ID, process.env.GUILD_ID),
      { body: commands }
    );
    console.log('✅ Slash commands registered.');
  } catch (err) {
    console.error('❌ Failed to register commands:', err);
  }
});

// ฟังคำสั่ง
client.on('interactionCreate', async interaction => {
  if (!interaction.isChatInputCommand()) return;
  if (interaction.channelId !== process.env.DISCORD_CHANNEL_ID) {
    return interaction.reply({ content: '❌ คุณใช้บอทในช่องนี้ไม่ได้', ephemeral: true });
  }

  if (interaction.commandName === 'gen') {
    const prompt = interaction.options.getString('prompt');
    await interaction.reply(`⏳ กำลังสร้างรูปภาพจาก: "${prompt}"`);

    try {
      const res = await fetch(`https://api.freepik.com/v1/resources?search=${encodeURIComponent(prompt)}`, {
        headers: {
          'Authorization': `Bearer ${process.env.FREEPIK_API_KEY}`
        }
      });
      const data = await res.json();

      if (data && data.data && data.data.length > 0) {
        await interaction.followUp(`✅ เจอภาพ: ${data.data[0].preview.url}`);
      } else {
        await interaction.followUp('❌ ไม่พบภาพที่ตรงกับ prompt');
      }
    } catch (err) {
      console.error(err);
      await interaction.followUp('❌ เกิดข้อผิดพลาดในการติดต่อ Freepik API');
    }
  }

  if (interaction.commandName === 'edit') {
    const prompt = interaction.options.getString('prompt');
    await interaction.reply(`ℹ️ Freepik API ไม่มี endpoint สำหรับแก้ภาพโดยตรง (ต้องเช็ค doc ของ Freepik เพิ่มเติม)\nคุณพิมพ์ว่า: "${prompt}"`);
  }
});

client.login(process.env.DISCORD_TOKEN);
