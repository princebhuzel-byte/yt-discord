import discord
from discord.ext import commands
import yt_dlp
import asyncio
import os
import subprocess
import sys
from dotenv import load_dotenv
from flask import Flask
from threading import Thread

# --- WEB SERVER FOR RENDER ---
app = Flask('')

@app.route('/')
def home():
    return "Bot is active in Guest Mode!"

def run_web_server():
    app.run(host='0.0.0.0', port=10000)

def keep_alive():
    t = Thread(target=run_web_server)
    t.daemon = True
    t.start()
# -----------------------------

load_dotenv()

def check_for_updates():
    print("Checking for yt-dlp updates...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-U", "yt-dlp"])
    except Exception as e:
        print(f"Update failed: {e}")

check_for_updates()

YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'no_warnings': True,
    'nocheckcertificate': True,
    # Guest Mode Strategy:
    'extractor_args': {
        'youtube': {
            'player_client': ['android', 'web'],
            'player_skip': ['webpage', 'configs']
        }
    },
    'http_headers': {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
}

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn -b:a 128k'
}

class MusicBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix="!", intents=intents)
        self.queue = []

    async def on_ready(self):
        print(f'Logged in as {self.user}')

bot = MusicBot()

async def play_song(ctx, url):
    try:
        ffmpeg_path = "ffmpeg" 
        async with ctx.typing():
            with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
                info = ydl.extract_info(url, download=False)
                audio_url = info['url']
                title = info.get('title', 'Unknown Title')

            await asyncio.sleep(1)
            source = await discord.FFmpegOpusAudio.from_probe(
                audio_url, 
                executable=ffmpeg_path, 
                **FFMPEG_OPTIONS
            )
            
            ctx.voice_client.play(source, after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop))
            await ctx.send(f"🔊 Now Broadcasting: **{title}**")
            
    except Exception as e:
        print(f"Detailed Error: {e}")
        await ctx.send(f"❌ Audio Error: {str(e)}")

async def play_next(ctx):
    if len(bot.queue) > 0:
        url = bot.queue.pop(0)
        await play_song(ctx, url)

@bot.command()
async def play(ctx, url):
    if not ctx.author.voice:
        return await ctx.send("Join a voice channel first!")
    
    vc = ctx.voice_client
    if not vc:
        vc = await ctx.author.voice.channel.connect(timeout=60.0, self_deaf=True)

    if vc.is_playing():
        bot.queue.append(url)
        await ctx.send("📝 Added to queue!")
    else:
        await play_song(ctx, url)

@bot.command()
async def stop(ctx):
    if ctx.voice_client:
        bot.queue.clear()
        await ctx.voice_client.disconnect(force=True)
        await ctx.send("🛑 Stopped.")

keep_alive()
bot.run(os.getenv('DISCORD_TOKEN'))
