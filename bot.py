# bot.py
import os

import discord
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f'{client.user} has connected to Discord!')

async def on_message(self, message):
        # don't respond to ourselves
        if message.author == self.user:
            return

        print(message.content)

        if not message.content.startswith('.'):
            return
        msg = message.content[1:]

        if msg == 'ping':
            await message.channel.send('pong')

client.run(TOKEN)