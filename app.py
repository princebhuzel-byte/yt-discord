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

# --- WEB SERVER (For Render Keep-Alive) ---
app = Flask('')
@app.route('/')
def home(): return "Bot is live with Burner Cookies!"
def run_web_server(): app.run(host='0.0.0.0', port=10000)
def keep_alive():
    t = Thread(target=run_web_server)
    t.daemon = True
    t.start()

load_dotenv()

# Force update yt-dlp to the latest 2026 nightly fixes on startup
def check_for_updates():
    try: subprocess.check_call([sys.executable, "-m", "pip", "install", "-U", "--pre", "yt-dlp[default]"])
    except: pass
check_for_updates()

# --- OPTIMIZED YT-DLP CONFIG ---
YDL_OPTIONS = {
    'format': 'bestaudio/best',  # Fixes "Requested format not available"
    'noplaylist': True,
    'quiet': False,
    'no_warnings': False,
    'nocheckcertificate': True,
    'cookiefile': 'youtube_cookies.txt', # MUST upload this to GitHub!
    'extractor_args': {
        'youtube': {
            'player_client': ['tv', 'web', 'mweb'], # 'tv' is currently more stable
            'po_token': 'web+ios' 
        }
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
        print(f'✅ Logged in as: {self.user}')

bot = MusicBot()

async def play_song(ctx, url):
    try:
        async with ctx.typing():
            # Check for the cookie file
            if not os.path.exists('youtube_cookies.txt'):
                return await ctx.send("⚠️ `youtube_cookies.txt` not found on GitHub! Upload it to fix this.")

            with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
                info = ydl.extract_info(url, download=False)
                audio_url = info['url']
                title = info.get('title', 'Unknown')
            
            # Using Discord's FFmpeg audio source
            source = await discord.FFmpegOpusAudio.from_probe(audio_url, **FFMPEG_OPTIONS)
            
            # Connection management to avoid 4006 error
            if ctx.voice_client:
                ctx.voice_client.play(source, after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop))
                await ctx.send(f"🎶 Now Playing: **{title}**")
            else:
                await ctx.send("❌ Bot was disconnected. Re-joining...")

    except Exception as e:
        print(f"🔥 Extraction Error: {e}")
        await ctx.send(f"❌ Error: {str(e)}")

async def play_next(ctx):
    if len(bot.queue) > 0: await play_song(ctx, bot.queue.pop(0))

@bot.command()
async def play(ctx, url):
    if not ctx.author.voice: 
        return await ctx.send("You need to be in a voice channel!")
    
    # Connect or use existing connection
    vc = ctx.voice_client
    if not vc:
        try:
            vc = await ctx.author.voice.channel.connect(timeout=20, self_deaf=True)
        except Exception as e:
            return await ctx.send(f"❌ Failed to join VC: {e}")

    if vc.is_playing():
        bot.queue.append(url)
        await ctx.send("✅ Added to queue.")
    else: 
        await play_song(ctx, url)

@bot.command()
async def stop(ctx):
    if ctx.voice_client:
        bot.queue.clear()
        await ctx.voice_client.disconnect()

keep_alive()
bot.run(os.getenv('DISCORD_TOKEN'))
