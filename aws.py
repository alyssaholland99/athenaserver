# bot.py
import os

import discord
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.all()
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    await client.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="for .help"))
    print(f'{client.user} has connected to Discord!')

@client.event
async def on_message(message):

        # don't respond to ourselves
        if message.author == client.user:
            return

        if not message.content.startswith('.'):
            return
        if message.content.startswith('..'):
            return
        
        if not "302" in os.popen("curl -Is https://cloud.alyssaserver.co.uk | head -n 1").read():
             await message.channel.send("AthenaServer may be offline, please checkout the status page here: <http://uptime.alyssaserver.co.uk/status/main>")
        
client.run(TOKEN)
