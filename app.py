import discord
from discord.ext import commands
import yt_dlp
import asyncio
import os
from dotenv import load_dotenv
from flask import Flask
from threading import Thread

# --- WEB SERVER (For Render Keep-Alive) ---
app = Flask('')
@app.route('/')
def home(): return "Bot is live with PO Token and Cookies!"
def run_web_server(): app.run(host='0.0.0.0', port=10000)
def keep_alive():
    t = Thread(target=run_web_server)
    t.daemon = True
    t.start()

load_dotenv()

# --- THE CONFIGURATION ---
# REPLACE 'YOUR_EXTRACTED_PO_TOKEN' with the string you found in your browser
MY_PO_TOKEN = os.getenv('PO_TOKEN', 'YOUR_EXTRACTED_PO_TOKEN')

YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': False,
    'no_warnings': False,
    'nocheckcertificate': True,
    'cookiefile': 'youtube_cookies.txt', # Ensure this is in your GitHub
    'extractor_args': {
        'youtube': {
            'player_client': ['web', 'mweb'],
            'po_token': f'web+{MY_PO_TOKEN}' # The 'web+' prefix is required
        }
    }
}

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

class MusicBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix="!", intents=intents)
        self.queue = []
    async def on_ready(self): print(f'✅ Bot Ready: {self.user}')

bot = MusicBot()

async def play_song(ctx, url):
    try:
        async with ctx.typing():
            with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
                info = ydl.extract_info(url, download=False)
                audio_url = info['url']
                title = info.get('title', 'Unknown')
            
            source = await discord.FFmpegOpusAudio.from_probe(audio_url, **FFMPEG_OPTIONS)
            ctx.voice_client.play(source, after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop))
            await ctx.send(f"🔊 Playing: **{title}**")
    except Exception as e:
        print(f"ERROR: {e}")
        await ctx.send(f"❌ Error: {str(e)}")

async def play_next(ctx):
    if len(bot.queue) > 0: await play_song(ctx, bot.queue.pop(0))

@bot.command()
async def play(ctx, url):
    if not ctx.author.voice: return await ctx.send("Join a VC!")
    vc = ctx.voice_client or await ctx.author.voice.channel.connect(self_deaf=True)
    if vc.is_playing():
        bot.queue.append(url)
        await ctx.send("Added to queue!")
    else: await play_song(ctx, url)

@bot.command()
async def stop(ctx):
    if ctx.voice_client:
        bot.queue.clear()
        await ctx.voice_client.disconnect()

keep_alive()
bot.run(os.getenv('DISCORD_TOKEN'))
