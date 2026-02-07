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

# --- WEB SERVER ---
app = Flask('')
@app.route('/')
def home(): return "Bot is live with Burner Cookies!"
def run_web_server(): app.run(host='0.0.0.0', port=10000)
def keep_alive():
    t = Thread(target=run_web_server)
    t.daemon = True
    t.start()

load_dotenv()

# We keep this to ensure the latest bypasses are active
def check_for_updates():
    try: subprocess.check_call([sys.executable, "-m", "pip", "install", "-U", "yt-dlp"])
    except: pass
check_for_updates()

# --- THE COOKIE-BASED CONFIG ---
YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'no_warnings': True,
    'nocheckcertificate': True,
    'cookiefile': 'youtube_cookies.txt', # This points to your uploaded file
    'extractor_args': {
        'youtube': {
            'player_client': ['web', 'mweb'],
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
    async def on_ready(self): print(f'Bot Ready: {self.user}')

bot = MusicBot()

async def play_song(ctx, url):
    try:
        async with ctx.typing():
            # Check if the file actually exists on the server
            if not os.path.exists('youtube_cookies.txt'):
                return await ctx.send("❌ Cookie file missing from GitHub!")

            with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
                info = ydl.extract_info(url, download=False)
                audio_url = info['url']
                title = info.get('title', 'Unknown')
            
            source = await discord.FFmpegOpusAudio.from_probe(audio_url, executable="ffmpeg", **FFMPEG_OPTIONS)
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
    vc = ctx.voice_client or await ctx.author.voice.channel.connect(timeout=60.0, self_deaf=True)
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
