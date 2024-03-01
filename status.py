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
        match getCurrentTime():
            case [12, 0] | [4, 44]:
                if self.msg_sent:
                    return
                checkBackup = os.popen('/bin/ssh root@offsitebackup "stat /srv/dev-disk-by-uuid-e6501278-3541-4943-b633-30d3a773bd97/OffsiteBackup"').read()
                checkBackup = checkBackup.splitlines()
                if len(checkBackup) > 1:
                    lastBackup = checkBackup[5].split(" ")[1]
                    await channel.send(lastBackup)
                else:
                    await channel.send("FAILURE: Unable to get status for offsite backup")
                self.msg_sent = True
            case _:
                self.msg_sent = False


bot = MyClient(command_prefix='.', intents=discord.Intents().all())

def getCurrentTime():
    return [time().hour, time().minute]

bot.run(TOKEN)
