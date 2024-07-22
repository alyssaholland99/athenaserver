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
        self.isHBATempAlerting = False
        self.isHBAHighTempAlerting = False
        self.isCPUTempAlerting = False
        self.isCPUHighTempAlerting = False

    async def on_ready(self):
        channel = bot.get_channel(1212969964634374186)
        urgent = bot.get_channel(1212985612877955122)
        alerts = bot.get_channel(1234274146997899394)
        await self.timer.start(channel, urgent, alerts)

    @tasks.loop(seconds=60)
    async def timer(self, channel, urgent, alerts):

        ### vars ###
        allowed_lsi_temp = 65
        allowed_cpu_temp = 45

        ### Constant checks ###
        await self.raid_integrity(channel, urgent, alerts)
        await self.lsi_temp(channel, urgent, alerts, allowed_lsi_temp)
        await self.cpu_temp(channel, urgent, alerts, allowed_cpu_temp)
        await self.transmissionCheck(alerts)

        ### Checks at specific times ###
        match getCurrentTime():

            case [4, 30]: #4:15
                if self.msg_sent:
                    return
                #await self.amelia_ping(channel, urgent, alerts)
                
            case [10, 0]: #10:00
                if self.msg_sent:
                    return
                await self.smart(channel, urgent, alerts)

            case [10, 30]: #10:30
                if self.msg_sent:
                    return
                await self.offsite_backup_check(channel, urgent, alerts)

            case [12, 0]: #12:00
                if self.msg_sent:
                    return
                day = datetime.datetime.today().weekday()
                if day == 0:
                    await self.raid_status(channel, urgent, alerts)

            case _:
                self.msg_sent = False

    async def offsite_backup_check(self, channel, urgent, alerts):
        # Offsite backup status
        
        date = datetime.datetime.today()
        checkBackup = os.popen('/bin/ssh root@offsitebackup "stat /srv/dev-disk-by-uuid-e6501278-3541-4943-b633-30d3a773bd97/OffsiteBackup"').read()
        checkBackup = checkBackup.splitlines()
        backupLogs = os.popen('cat /root/athenaserver/syslogs/duplicityBackup').read()
        if len(checkBackup) > 1:
            lastBackup = checkBackup[5].split(" ")[1]
            currentDate = str(date).split(" ")[0]
            if lastBackup == currentDate:
                await channel.send("SUCCESS: Offsite server was backed up to successfully overnight\n\nOutput Log:\n{}".format(backupLogs))
            else:
                await urgent.send("FAILURE: Backup date and current date do not match; server may not have backed up last night\n\nOutput Log:\n{}".format(backupLogs))
        else:
            await urgent.send("FAILURE: Unable to get status for offsite backup\n\nOutput Log:\n{}".format(backupLogs))
        self.msg_sent = True
            
    async def raid_status(self, channel, urgent, alerts):
        # RAID status
        self.msg_sent = True
        checkRAID = os.popen("/sbin/mdadm -D /dev/md1").read()
        if "State : clean" in checkRAID:
            await channel.send("RAID Status: \n{}".format(checkRAID))
        else:
            await urgent.send("RAID Status: \n{}".format(checkRAID))
    
    async def smart(self, channel, urgent, alerts):
        # SMART status
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

    async def amelia_ping(self, channel, urgent, alerts):
        # AmeliaServer status
        self.msg_sent = True
        day = datetime.datetime.today().weekday()
        if day == 0: # If Monday
            ping = os.popen("ping -c 1 192.168.0.100").read()
            if not "100% packet loss" in ping:
                await channel.send("SUCCESS: Cold storage is active")
            else:
                await urgent.send("FAILURE: Cold storage was not able to be pinged")
        if day == 1: # If Tuesday
            ping = os.popen("ping -c 1 192.168.0.100").read()
            if not "100% packet loss" in ping:
                await urgent.send("FAILURE: Cold storage is still active when it shouldn't be; could be a long backup or the backup may have failed")

    async def raid_integrity(self, channel, urgent, alerts):
        if ("checking" in os.popen("/sbin/mdadm -D /dev/md1").read()): # Check to see if the RAID is being verified
            if (not self.isMdadmChecking):
                await alerts.send("WARNING: The main drives are being verified for data integrity, modifictions to files within Nextcloud may be slow or not working. This may take around 12 hours to complete.\nTo check the progress of this check please use `.server mdadm`")
                self.isMdadmChecking = True
        elif (self.isMdadmChecking):
            await alerts.send("The drives have now finished their data integrity check")
            await alerts.send(os.popen("/sbin/mdadm -D /dev/md1 | grep State").read())
            self.isMdadmChecking = False

    async def lsi_temp(self, channel, urgent, alerts, allowed_lsi_temp):
        lsi_temp = int(os.popen("/opt/MegaRAID/storcli/storcli64 /c0 show temperature | grep temperature").read().split(" temperature(Degree Celsius) ")[1]) # Check temperature of LSI HBA
        if (allowed_lsi_temp < lsi_temp): # Check to see if the LSI HBA is too hot
            if not self.isHBATempAlerting: # Check to see if an alert has already been sent
                await alerts.send("ALERT: The LSI HBA is over {}°C! Currently at {}°C\nThe fan may be unplugged or may have failed".format(allowed_lsi_temp, lsi_temp))
                self.isHBATempAlerting = True
            if (allowed_lsi_temp + 20 < lsi_temp): # Check to see if the LSI HBA is far too hot
                if not self.isHBAHighTempAlerting: # Check to see if an alert has already been sent
                    await urgent.send("URGENT: The LSI HBA is over {}°C! Currently at {}°C".format(allowed_lsi_temp + 20, lsi_temp))
                    self.isHBAHighTempAlerting = True
        elif (self.isHBATempAlerting): # Reset temperature booleans and send message
            await alerts.send("The LSI HBA is now an acceptable temperature ({}°C) ".format(lsi_temp))
            self.isHBATempAlerting = False
            self.isHBAHighTempAlerting = False

    async def cpu_temp(self, channel, urgent, alerts, allowed_cpu_temp):
        cpu_temp = int(os.popen("/bin/sensors | grep Tccd1").read().split("+")[1].split(".")[0]) # Check temperature of CPU
        if (allowed_cpu_temp < cpu_temp): # Check to see if the CPU is too hot
            if not self.isCPUTempAlerting: # Check to see if an alert has already been sent
                await alerts.send("ALERT: The CPU is over {}°C! Currently at {}°C\nThe fan may be unplugged or may have failed".format(allowed_cpu_temp, cpu_temp))
                self.isCPUTempAlerting = True
            if (allowed_cpu_temp + 20 < allowed_cpu_temp): # Check to see if the CPU is far too hot
                if not self.isCPUHighTempAlerting: # Check to see if an alert has already been sent
                    await urgent.send("URGENT: The CPU is over {}°C! Currently at {}°C".format(allowed_cpu_temp + 20, cpu_temp))
                    self.isCPUHighTempAlerting = True
        elif (self.isCPUTempAlerting): # Reset temperature booleans and send message
            await alerts.send("The CPU is now an acceptable temperature ({}°C) ".format(cpu_temp))
            self.isCPUTempAlerting = False
            self.isCPUHighTempAlerting = False

    async def transmissionCheck(self, alerts):
        transmissionStatusCheck = os.popen("curl server.alyssaserver.co.uk:9091").read()
        if "401" not in transmissionStatusCheck:
            await alerts.send("Transmission is unreachable. Restarting...")
            os.system("/bin/docker stop transmission-openvpn-proxy && /bin/docker rm transmission-openvpn-proxy && /bin/docker compose -f /root/Transmission/vpn/docker-compose.yml down >> /dev/null 2>&1 && /bin/docker compose -f /root/Transmission/vpn/docker-compose.yml up -d >> /dev/null 2>&1 && /root/Transmission/vpn/proxy.sh")
            await alerts.send("Transmission restarted")

bot = MyClient(command_prefix='.!.!.!', intents=discord.Intents().all())

def getCurrentTime():
    return [time().hour, time().minute]

bot.run(TOKEN)
