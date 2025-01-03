import discord
import discord.ext.commands as commands
import os
import asyncio
import yt_dlp
from dotenv import load_dotenv
import urllib.parse, urllib.request, re
from discord import Embed

def keywords_url(link, youtube_results_url, youtube_watch_url):
    query_string = urllib.parse.urlencode({'search_query': link})
    content = urllib.request.urlopen(youtube_results_url + query_string)
    search_results = re.findall(r'/watch\?v=(.{11})', content.read().decode())
    link = youtube_watch_url + search_results[0]

    return link

def run_bot():
    load_dotenv()
    TOKEN = os.getenv('DISCORD_TOKEN')
    intents = discord.Intents.default()
    intents.message_content = True
    client = commands.Bot(command_prefix="c.", intents = intents)

    queues = {}
    voice_clients = {}
    youtube_base_url = 'https://www.youtube.com/'
    youtube_results_url = youtube_base_url + 'results?'
    youtube_watch_url = youtube_base_url + 'watch?v='
    yt_dl_options = {"format": "bestaudio/best"}
    ytdl = yt_dlp.YoutubeDL(yt_dl_options)

    ffmpeg_options = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5','options': '-vn -filter:a "volume=0.25"'}

    @client.event
    async def on_ready():
        print(f'{client.user} is now online!')
    
    async def play_next(ctx):
        if ctx.guild.id in queues and queues[ctx.guild.id]:
            next_url = queues[ctx.guild.id].pop[0]
            try:
                loop = asyncio.get_event_loop()
                data = await loop.run_in_executor(None, lambda: ytdl.extract_info(next_url, download=False))
                song = data['url']
                player = discord.FFmpegOpusAudio(song, **ffmpeg_options)

                voice_clients[ctx.guild.id].play(
                    player,
                    after = lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), client.loop)
                )
                await ctx.send(f"Now playing: {data.get('title', 'Unknown Title')}")
            except Exception as e:
                await ctx.send("An error occured while trying to play the next song.")
                print(e)


    @client.command(name="play")
    async def play(ctx, *, link):
        try: 
            voice_client = voice_clients.get(ctx.guild.id)
            if not voice_client or not voice_client.is_connected():
                voice_client = await ctx.author.voice.channel.connect()
                voice_clients[voice_client.guild.id] = voice_client
        except Exception as e:
            print(e)

        try:
            if youtube_base_url not in link:
                link = keywords_url(link, youtube_results_url, youtube_watch_url)

            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(link, download=False))

            if 'entries' in data:
                for entry in data['entries']:
                    video_url = entry['webpage_url']  # Get each video's URL
                    queues.setdefault(ctx.guild.id, []).append(video_url)  # Add to queue

                await ctx.reply(f"Added {len(data['entries'])} songs from the playlist to the queue!")

                # Start playback if not already playing
                if not voice_clients[ctx.guild.id].is_playing():
                    await play_next(ctx)
            else:
                # Handle single video
                queues.setdefault(ctx.guild.id, []).append(data['webpage_url'])

                if not voice_clients[ctx.guild.id].is_playing():
                    await play_next(ctx)
        except Exception as e:
            print(e)

    @client.command(name="clear")
    async def clear_queue(ctx):
        if ctx.guild.id in queues:
            queues[ctx.guild.id].clear()
            await ctx.send("Queue is cleared")
        else:
            await ctx.send("There is no queue to clear")


    @client.command(name="pause")
    async def pause(ctx):
        try:
            voice_clients[ctx.guild.id].pause()
        except Exception as e:
            print(e)

    @client.command(name="resume")
    async def resume(ctx):
        try:
            voice_clients[ctx.guild.id].resume()
        except Exception as e:
            print(e)

    @client.command(name="add")
    async def queue(ctx, *, url):
        if ctx.guild.id not in queues:
            queues[ctx.guild.id] = []
        
        queues[ctx.guild.id].append(url)

        try:     
            if youtube_base_url not in url:
                url = keywords_url(url, youtube_results_url, youtube_watch_url)

            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=False))

            song_title = data.get('title', 'Unknown Title')
            video_length = data.get('duration', 0)
            video_length_formatted = f"{video_length // 60}:{video_length % 60:02}"
            user_name = ctx.author.name
            queue_number = len(queues[ctx.guild.id]) + 1

            embed = Embed(
                title = f"Added to queue - {queue_number}",
                description=f"[{song_title}]({url}) \nRequested by: **{user_name}**.",
                color = 0x3498db
            )
            embed.add_field(name="Total Queue Time", value=f"{video_length_formatted}", inline=False)

            await ctx.reply(embed = embed)
        except Exception as e:
            await ctx.send("An error occurred while adding the song to the queue.")
            print(e)

    
    @client.command(name="leave")
    async def leave(ctx):
        try:
            voice_clients[ctx.guild.id].stop()
            await voice_clients[ctx.guild.id].disconnect()
            del voice_clients[ctx.guild.id]
        except Exception as e:
            print(e)

    @client.command(name="join")
    async def join(ctx):
        try:
            voice_client = await ctx.author.voice.channel.connect()
            voice_clients[ctx.guild.id] = voice_client
            await ctx.reply("Chandelier has joined the channel!")
        except Exception as e:
            print(e)

    @client.command(name="skip")
    async def skip(ctx):
        try:
            if ctx.guild.id in voice_clients and voice_clients[ctx.guild.id].is_playing():
                voice_clients[ctx.guild.id].stop()
                await play_next(ctx)
                await ctx.send("Skipped to the next song.")
            else:
                await ctx.send("No song is currently playing to skip.")
        except Exception as e:
            print(e)
    
    client.run(TOKEN)