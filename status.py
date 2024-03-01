# bot.py
import os

import discord
from dotenv import load_dotenv
from discord.ext import commands, tasks
from requests import get
import datetime

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.all()
client = discord.Client(intents=intents)

time = datetime.datetime.now

@client.event
async def on_ready():
    print(f'{client.user} has connected to Discord!')

@tasks.loop(minutes=1)
async def timer(channel):

    channel = client.get_channel(1212969964634374186)
    currentTime = getCurrentTime()

    match currentTime:
        case [12, 0]:
            await channel.send('Test12')
        case _:
            await channel.send('Test')


def getCurrentTime():
    return [time().hour, time().minute]

client.run(TOKEN)
