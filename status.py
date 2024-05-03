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
        self.isMdadmChecking = False
        self.isTempAlerting = False
        self.isHighTempAlerting = False

    async def on_ready(self):
        channel = bot.get_channel(1212969964634374186)
        urgent = bot.get_channel(1212985612877955122)
        alerts = bot.get_channel(1234274146997899394)
        await self.timer.start(channel, urgent, alerts)

    @tasks.loop(seconds=60)
    async def timer(self, channel, urgent, alerts):

        ### vars ###
        allowed_lsi_temp = 65

        ### Constant checks ###

        # RAID checking
        if ("checking" in os.popen("/sbin/mdadm -D /dev/md1").read()): # Check to see if the RAID is being verified
            if (not self.isMdadmChecking):
                await alerts.send("WARNING: The main drives are being verified for data integrity, modifictions to files within Nextcloud may be slow or not working. \nTo check the progress of this check please use `.server mdadm`")
                self.isMdadmChecking = True
        elif (self.isMdadmChecking):
            await alerts.send("The drives have now finished their data integrity check")
            self.isMdadmChecking = False

        # LSI temperature
        await self.lsi_temp(channel, urgent, alerts, allowed_lsi_temp)


        ### Checks at specific times ###
        match getCurrentTime():
            case [4, 15]:
                
                # AmeliaServer status
                if self.msg_sent:
                    return
                self.msg_sent = True
                day = datetime.datetime.today().weekday()
                if day == 0: # If Monday
                    ping = os.popen("ping -c 1 192.168.0.100").read()
                    if "0% packet loss" in ping:
                        await channel.send("SUCCESS: Cold storage is active")
                    else:
                        await urgent.send("FAILURE: Cold storage was not able to be pinged")
                if day == 1: # If Tuesday
                    ping = os.popen("ping -c 1 192.168.0.100").read()
                    if not "100% packet loss" in ping:
                        await urgent.send("FAILURE: Cold storage is still active when it shouldn't be; could be a long backup or the backup may have failed")


            case [10, 0]: #10am
                
                # SMART status
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

            case [11, 0]: #11am

                # RAID status
                if self.msg_sent:
                    return
                day = datetime.datetime.today().weekday()
                self.msg_sent = True
                checkRAID = os.popen("/sbin/mdadm -D /dev/md1").read()
                if "State : clean" in checkRAID:
                    if day != 0:
                        return
                    await channel.send("RAID Status: \n{}".format(checkRAID))
                else:
                    await urgent.send("RAID Status: \n{}".format(checkRAID))

            case [12, 0]: #Midday

                # Offsite backup status
                if self.msg_sent:
                    return
                date = datetime.datetime.today()
                checkBackup = os.popen('/bin/ssh root@offsitebackup "stat /srv/dev-disk-by-uuid-e6501278-3541-4943-b633-30d3a773bd97/OffsiteBackup"').read()
                checkBackupUptime = os.popen('/bin/ssh root@offsitebackup "uptime"').read()
                checkBackup = checkBackup.splitlines()
                if len(checkBackup) > 1:
                    lastBackup = checkBackup[5].split(" ")[1]
                    currentDate = str(date).split(" ")[0]
                    if lastBackup == currentDate:
                        await channel.send("SUCCESS: Offsite server was backed up to successfully overnight and has been up for{}".format(checkBackupUptime.split(",")[0].split("up")[1]))
                    else:
                        await urgent.send("FAILURE: Backup date and current date do not match; server may not have backed up last night")
                else:
                    await urgent.send("FAILURE: Unable to get status for offsite backup")
                self.msg_sent = True


            case _:
                self.msg_sent = False
    
    async def lsi_temp(self, channel, urgent, alerts, allowed_lsi_temp):
        lsi_temp = int(os.popen("/opt/MegaRAID/storcli/storcli64 /c0 show temperature | grep temperature").read().split(" temperature(Degree Celsius) ")[1]) # Check temperature of LSI HBA
        if (allowed_lsi_temp < lsi_temp): # Check to see if the LSI HBA is too hot
            if not self.isTempAlerting: # Check to see if an alert has already been sent
                await alerts.send("ALERT: The LSI HBA is over {}°C! Currently at {}°C\nThe fan may be unplugged or may have failed".format(allowed_lsi_temp, lsi_temp))
                self.isTempAlerting = True
            if (allowed_lsi_temp + 20 < lsi_temp): # Check to see if the LSI HBA is far too hot
                if not self.isHighTempAlerting: # Check to see if an alert has already been sent
                    await urgent.send("URGENT: The LSI HBA is over {}°C! Currently at {}°C".format(allowed_lsi_temp + 20, lsi_temp))
                    self.isHighTempAlerting = True
        elif (self.isTempAlerting): # Reset temperature booleans and send message
            await alerts.send("The LSI HBA is now an acceptable temperature ({}°C) ".format(lsi_temp))
            self.isTempAlerting = False
            self.isHighTempAlerting = False


bot = MyClient(command_prefix='.!.!.!', intents=discord.Intents().all())

def getCurrentTime():
    return [time().hour, time().minute]

bot.run(TOKEN)
