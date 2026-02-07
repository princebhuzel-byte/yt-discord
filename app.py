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

# --- WEB SERVER FOR RENDER (Option A) ---
app = Flask('')

@app.route('/')
def home():
    return "Bot is alive and broadcasting!"

def run_web_server():
    # Render uses port 10000 by default for Web Services
    app.run(host='0.0.0.0', port=10000)

def keep_alive():
    t = Thread(target=run_web_server)
    t.daemon = True
    t.start()
# -----------------------------------------

load_dotenv()

def check_for_updates():
    """Ensures yt-dlp is always current to bypass YouTube detection."""
    print("Checking for yt-dlp updates...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-U", "yt-dlp"])
        print("yt-dlp update check complete.")
    except Exception as e:
        print(f"Update failed: {e}")

# Run update on startup
check_for_updates()

YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'nocheckcertificate': True,
    'impersonate': 'chrome', # Requires curl-cffi in requirements.txt
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

    async def on_ready(self):
        print(f'Logged in as {self.user}')
        print("System status: Connected and ready for broadcast.")

bot = MusicBot()

async def play_song(ctx, url):
    try:
        ffmpeg_path = "ffmpeg" # System path for Linux/Docker

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
        print(f"Error: {e}")
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
        vc = await ctx.author.voice.channel.connect(timeout=45.0, self_deaf=True)

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

# Start the web server and the bot
keep_alive()
bot.run(os.getenv('DISCORD_TOKEN'))
