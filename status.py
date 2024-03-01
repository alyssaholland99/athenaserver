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
date = datetime.datetime.today()

class MyClient(commands.Bot):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.msg_sent = False

    async def on_ready(self):
        channel = bot.get_channel(1212969964634374186)
        urgent = bot.get_channel(1212985612877955122)
        await self.timer.start(channel, urgent)

    @tasks.loop(seconds=30)
    async def timer(self, channel, urgent):
        match getCurrentTime():
            case [12, 0]: #Midday
                if self.msg_sent:
                    return
                checkBackup = os.popen('/bin/ssh root@offsitebackup "stat /srv/dev-disk-by-uuid-e6501278-3541-4943-b633-30d3a773bd97/OffsiteBackup"').read()
                checkBackup = checkBackup.splitlines()
                if len(checkBackup) > 1:
                    lastBackup = checkBackup[5].split(" ")[1]
                    currentDate = str(date).split(" ")[0]
                    if lastBackup == currentDate:
                        await channel.send("SUCCESS: Offsite server was backed up to successfully overnight")
                    else:
                        await urgent.send("FAILURE: Backup date and current date do not match; server may not have backed up last night")
                else:
                    await urgent.send("FAILURE: Unable to get status for offsite backup")
                self.msg_sent = True
            case [10, 0]: #10am
                if self.msg_sent:
                    return
                driveList = []
                getDriveList = os.popen('smartctl --scan').read()
                for drive in getDriveList.splitlines():
                    driveList.append(drive.split(" ")[0])
                for drive in driveList:
                    checkDrive = os.popen('smartctl -a {} | grep "SMART overall-health self-assessment test result:"'.format(drive)).read()
                    if not "PASSED" in checkDrive:
                        await urgent.send("FAILURE: {} - {}".format(drive, checkDrive))
                    else:
                        await channel.send("SUCCESS: {} - {}".format(drive, checkDrive))
                self.msg_sent = True
            case _:
                self.msg_sent = False


bot = MyClient(command_prefix='.!.!.!', intents=discord.Intents().all())

def getCurrentTime():
    return [time().hour, time().minute]

bot.run(TOKEN)
