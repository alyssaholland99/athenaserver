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
    print(f'{client.user} has connected to Discord!')

@client.event
async def on_message(message):
        # don't respond to ourselves
        if message.author == client.user:
            return

        if not message.content.startswith('.'):
            return
        msg = message.content[1:]

        if msg == 'ping':
            await message.channel.send('pong')

        if msg.split(" ")[0] == "palworld":
            if msg.split(" ")[1] == "players":
                players = os.popen("/bin/docker exec palworld-dedicated-server rcon showPlayers").read()
                players = players.splitlines()
                playerSend = ""
                for i in players:
                    playerSend += i.split()[0]
                await message.channel.send(playerSend)

client.run(TOKEN)