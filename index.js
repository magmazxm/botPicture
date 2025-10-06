import 'dotenv/config';
import { Client, GatewayIntentBits, REST, Routes, SlashCommandBuilder } from 'discord.js';
import fetch from 'node-fetch';

const DISCORD_TOKEN = process.env.DISCORD_TOKEN;
const CLIENT_ID = process.env.CLIENT_ID; // Bot Application ID
const GUILD_ID = process.env.GUILD_ID;   // Server ID
const CHANNEL_ONLY = process.env.DISCORD_CHANNEL_ID || '1424193369646825482';
const FREEPIK_API_KEY = process.env.FREEPIK_API_KEY;

if (!DISCORD_TOKEN || !CLIENT_ID || !GUILD_ID || !FREEPIK_API_KEY) {
  console.error('กรุณาตั้งค่า DISCORD_TOKEN, CLIENT_ID, GUILD_ID, FREEPIK_API_KEY');
  process.exit(1);
}

const client = new Client({ intents: [GatewayIntentBits.Guilds] });

// กำหนด Slash Command
const commands = [
  new SlashCommandBuilder()
    .setName('search')
    .setDescription('ค้นหาภาพจาก Freepik')
    .addStringOption(opt =>
      opt.setName('keyword')
        .setDescription('คำค้นหาภาพ')
        .setRequired(true)),
].map(cmd => cmd.toJSON());

const rest = new REST({ version: '10' }).setToken(DISCORD_TOKEN);

async function registerCommands() {
  await rest.put(
    Routes.applicationGuildCommands(CLIENT_ID, GUILD_ID),
    { body: commands }
  );
  console.log('✅ Slash commands ลงทะเบียนแล้ว');
}

async function searchFreepik(query) {
  const url = `https://api.freepik.com/v1/resources?term=${encodeURIComponent(query)}&page=1&limit=3`;

  const res = await fetch(url, {
    headers: {
      'Authorization': `Bearer ${FREEPIK_API_KEY}`
    }
  });

  if (!res.ok) {
    throw new Error(await res.text());
  }

  return res.json();
}

client.on('ready', () => {
  console.log(`✅ Logged in as ${client.user.tag}`);
  registerCommands();
});

client.on('interactionCreate', async (interaction) => {
  if (!interaction.isChatInputCommand()) return;
  if (interaction.channelId !== CHANNEL_ONLY) {
    return interaction.reply({ content: '❌ ใช้บอทได้เฉพาะในช่องที่กำหนด', ephemeral: true });
  }

  if (interaction.commandName === 'search') {
    const keyword = interaction.options.getString('keyword');
    await interaction.deferReply();

    try {
      const data = await searchFreepik(keyword);

      if (!data.data || data.data.length === 0) {
        return interaction.editReply(`ไม่พบผลลัพธ์สำหรับ: **${keyword}**`);
      }

      const results = data.data.map(item =>
        `[${item.title}](${item.url})\nPreview: ${item.image}`
      ).join('\n\n');

      return interaction.editReply(`🔎 ผลลัพธ์การค้นหา: **${keyword}**\n\n${results}`);
    } catch (e) {
      return interaction.editReply(`❌ เกิดข้อผิดพลาด: ${e.message}`);
    }
  }
});

client.login(DISCORD_TOKEN);
