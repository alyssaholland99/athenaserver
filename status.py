# bot.py
import os

import discord
from dotenv import load_dotenv
from discord.ext import commands, tasks
from requests import get
import datetime

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

time = datetime.datetime.now

class MyClient(commands.Bot):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.msg_sent = False

    async def on_ready(self):
        channel = bot.get_channel(1212969964634374186)  # replace with channel ID that you want to send to
        await self.timer.start(channel)

    @tasks.loop(seconds=1)
    async def timer(self, channel):
        if time().hour == 7 and time().minute == 0:
            if not self.msg_sent:
                await channel.send('Its 7 am')
                self.msg_sent = True
        else:
            await channel.send('Test')
            self.msg_sent = False


bot = MyClient(command_prefix='.', intents=discord.Intents().all())


def getCurrentTime():
    return [time().hour, time().minute]

bot.run(TOKEN)
