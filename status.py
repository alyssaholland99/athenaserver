# bot.py
import os
import discord
from dotenv import load_dotenv
from discord.ext import commands, tasks
from requests import get
import datetime, time

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

currentTime = datetime.datetime.now

class MyClient(commands.Bot):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.msg_sent = False
        self.isMdadmChecking = False
        self.isHBATempAlerting = False
        self.isHBAHighTempAlerting = False
        self.isCPUTempAlerting = False
        self.isCPUHighTempAlerting = False
        self.isloadAverageAlerting = False
        self.isMemoryAlerting = False
        self.sshClients = []
        self.isStorageAlerting = False
        self.isUrgentStorageAlerting = False
        self.isTransmissionAlerting = False

    async def on_ready(self):
        channel = bot.get_channel(int(os.getenv('NOTIFICATIONS')))
        urgent = bot.get_channel(int(os.getenv('URGENT')))
        alerts = bot.get_channel(int(os.getenv('ALERTS')))
        await self.timer.start(channel, urgent, alerts)

    @tasks.loop(seconds=60)
    async def timer(self, channel, urgent, alerts):

        ### vars ###
        allowed_lsi_temp = 65
        allowed_cpu_temp = 75

        allowed_cpu_load = 12 # 12 Threads
        allowed_memory_percentage = 80

        ### Constant checks ###
        await self.raid_integrity(channel, urgent, alerts)
        await self.lsi_temp(channel, urgent, alerts, allowed_lsi_temp)
        await self.cpu_temp(channel, urgent, alerts, allowed_cpu_temp)
        await self.cpu_load_average(channel, urgent, alerts, allowed_cpu_load)
        await self.memory_usage(channel, urgent, alerts, allowed_memory_percentage)
        await self.transmissionCheck(alerts)
        await self.sshConnectionCheck(alerts)
        await self.bootDriveStorageCheck(alerts, urgent)

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

            #case [12, 20]: #12:20
            case [13, 20]: #12:20
                if self.msg_sent:
                    return
                await self.offsite_backup_check(channel, urgent, alerts)

            case [11, 00]: #17:30
                if self.msg_sent:
                    return
                #await self.offite_cleanup_check(channel)

            case [12, 0]: #12:00
                if self.msg_sent:
                    return
                day = datetime.datetime.today().weekday()
                if day == 0:
                    await self.raid_status(channel, urgent, alerts)

            case [12, 15]: #12:15
                await self.offsiteDriveStorageCheck(alerts, urgent, channel)

            case [16, 30]:
                await self.photoBackupCheck(alerts, channel)

            case _:
                self.msg_sent = False

    async def offsite_backup_check(self, channel, urgent, alerts):
        # Offsite backup status
        
        date = datetime.datetime.today()
        #checkBackup = os.popen('/bin/ssh root@offsitebackup "stat /srv/dev-disk-by-uuid-e6501278-3541-4943-b633-30d3a773bd97/OffsiteBackup"').read()
        #checkBackup = checkBackup.splitlines()
        checkBackup = os.popen('/root/restic/getSnapshots.sh | grep athenaserver').read()
        backupLogs = os.popen('cat /root/athenaserver/syslogs/duplicityBackup').read()
        if len(checkBackup) > 1:
            #lastBackup = checkBackup[5].split(" ")[1]
            currentDate = str(date).split(" ")[0]
            if currentDate in checkBackup:
                await channel.send("SUCCESS: Offsite server was backed up to successfully overnight\n\nOutput Log:\n{}".format(backupLogs))
            else:
                await urgent.send("FAILURE: Backup date and current date do not match; server may not have backed up last night\n\nOutput Log:\n{}".format(backupLogs))
        else:
            await urgent.send("FAILURE: Unable to get status for offsite backup\n\nOutput Log:\n{}".format(backupLogs))
        self.msg_sent = True

    async def offite_cleanup_check(self, channel):
        modifiedTime = os.path.getmtime('/root/athenaserver/syslogs/duplicityRemoval')
        age = time.time() - modifiedTime
        if (age // 3600) <= 24:
            cleanupLogs = os.popen('cat /root/athenaserver/syslogs/duplicityRemoval').read()
            await channel.send("Backup files appear to have been cleaned\n\nOutput Log:\n{}".format(cleanupLogs))
            
    async def raid_status(self, channel, urgent, alerts):
        # RAID status
        self.msg_sent = True
        checkRAID = os.popen("/sbin/mdadm -D /dev/md1").read()
        if ("State : clean" in checkRAID or "State : active, checking" in checkRAID):
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
            await alerts.send(os.popen("/sbin/mdadm -D /dev/md1 | grep State | head -n 1").read())
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
                await alerts.send("ALERT: The CPU is over {}°C! Currently at {}°C".format(allowed_cpu_temp, cpu_temp))
                self.isCPUTempAlerting = True
            if (allowed_cpu_temp + 10 < cpu_temp): # Check to see if the CPU is far too hot
                if not self.isCPUHighTempAlerting: # Check to see if an alert has already been sent
                    await urgent.send("URGENT: The CPU is over {}°C! Currently at {}°C".format(allowed_cpu_temp + 20, cpu_temp))
                    self.isCPUHighTempAlerting = True
        elif (self.isCPUTempAlerting and allowed_cpu_temp - 5 > cpu_temp): # Reset temperature booleans and send message
            await alerts.send("The CPU is now an acceptable temperature ({}°C) ".format(cpu_temp))
            self.isCPUTempAlerting = False
            self.isCPUHighTempAlerting = False

    async def cpu_load_average(self, channel, urgent, alerts, allowed_load_average):
        load = float((os.popen("/bin/cat /proc/loadavg").read()).split(" ")[0])
        if (allowed_load_average < load): # Check to see if the CPU has a high load average
            if not self.isloadAverageAlerting: # Check to see if an alert has already been sent
                await alerts.send("ALERT: The CPU has a high load average! Currently at {}".format(str(round(load, 2))))
                self.isloadAverageAlerting = True
        elif (self.isloadAverageAlerting): # Reset load boolean
            await alerts.send("The CPU is now at a load average of {}".format(str(round(load, 2))))
            self.isloadAverageAlerting = False

    async def memory_usage(self, channel, urgent, alerts, allowed_memory_usage):
        memoryPercent = float(os.popen("free | grep Mem | awk '{print $3/$2 * 100}'").read())
        if (allowed_memory_usage < memoryPercent): # Check to see if the memory usage is high
            if not self.isMemoryAlerting: # Check to see if an alert has already been sent
                await alerts.send("ALERT: The memory usage on the server is high! Currently at {}%".format(str(round(memoryPercent, 2))))
                self.isMemoryAlerting = True
        elif (self.isMemoryAlerting): # Reset memory boolean
            await alerts.send("The memory usage is now {}%".format(str(round(memoryPercent, 2))))
            self.isMemoryAlerting = False

    async def transmissionCheck(self, alerts):
        transmissionStatusCheck = os.popen("curl transmission.alyssaserver.co.uk").read()
        if "401" not in transmissionStatusCheck:
            if self.isTransmissionAlerting == True:
                await alerts.send("Transmission failed to restart successfully. Retrying restart...", delete_after=60)
            else:
                await alerts.send("Transmission is unreachable. Restarting...", delete_after=60)
            self.isTransmissionAlerting = True
            os.system("/bin/docker stop transmission-openvpn-proxy && /bin/docker rm transmission-openvpn-proxy && /bin/docker compose -f /root/Transmission/vpn/docker-compose.yml down >> /dev/null 2>&1 && /bin/docker compose -f /root/Transmission/vpn/docker-compose.yml up -d >> /dev/null 2>&1 && /root/Transmission/vpn/proxy.sh")
        elif self.isTransmissionAlerting == True:
            await alerts.send("Transmission restarted successfully")
            self.isTransmissionAlerting = False

    async def sshConnectionCheck(self, alerts):
        sshClientCheck = os.popen("w -ih | awk '{print $2}'").read()
        currentSshClients = sshClientCheck.splitlines()
        if '-' in currentSshClients:
            currentSshClients.remove('-')
        clientDifferenceConnected = list(set(currentSshClients) - set(self.sshClients))
        clientDifferenceDisconnected = list(set(self.sshClients) - set(currentSshClients))
        if len(clientDifferenceConnected) >= 1:
            for ip in clientDifferenceConnected:
                local = "REMOTE"
                if "192.168.0." in ip:
                    local = "LOCAL"
                await alerts.send("{} ({}) has just started an SSH session".format(ip, local))
        if len(clientDifferenceDisconnected) >= 1:
            for ip in clientDifferenceDisconnected:
                local = "REMOTE"
                if "192.168.0." in ip:
                    local = "LOCAL"
                await alerts.send("{} ({}) has just closed their SSH session".format(ip, local))
        self.sshClients = currentSshClients

    async def bootDriveStorageCheck(self, alerts, urgent):
        storageCheck = os.popen("df -h / | awk '{print $5}' | tail -n +2").read()
        storageCheck = int(storageCheck.replace("%", ""))
        if storageCheck >= 80:
            if not self.isStorageAlerting:
                await alerts.send("Boot drive is at {}% usage".format(storageCheck))
                self.isStorageAlerting = True
        if storageCheck >= 90:
            if not self.isUrgentStorageAlerting:
                await urgent.send("Boot drive is at {}% usage".format(storageCheck))
                self.isUrgentStorageAlerting = True
        if storageCheck >= 95:
            await urgent.send("Boot drive is at {}% usage".format(storageCheck))

    async def offsiteDriveStorageCheck(self, alerts, urgent, channel):
        storageCheck = os.popen('/bin/ssh root@offsitebackup -tt "/root/checkStorage.sh"').read()
        if "%" in storageCheck:
            storageCheck = storageCheck.splitlines()
            storageCheck = storageCheck[0].split(" ")
            tb = storageCheck[1]+"B"
            percentage = int(storageCheck[0].replace("%", ""))
            await channel.send("Offsite drive is at {}% usage ({})".format(percentage, tb))
            if percentage >= 90 and percentage < 95:
                await alerts.send("ALERT: Offsite drive is at {}% usage ({})".format(percentage, tb))
            if percentage >= 95:
                await urgent.send("URGENT: Offsite drive is at {}% usage ({})".format(percentage, tb))

    async def photoBackupCheck(self, alerts, channel):
        nextcloudBase = "/srv/dev-disk-by-uuid-0901e9da-0191-4a3f-b7ff-d8cc98c9c617/16TB/.Cloud/"
        photoPath = "/files/Photos/AutomaticBackup/"
        users = ["Alastair", "Kevin", "Gill"]
        for user in users:
            modifyCheck = os.popen("stat {}{}{} | grep Modify".format(nextcloudBase, user, photoPath)).read()
            user = user.replace("Alastair", "Alyssa")
            modifyDate = modifyCheck.split(" ")[1]
            modifyDelta = datetime.datetime.now() - datetime.datetime.strptime(modifyDate, "%Y-%m-%d")
            photoString = "{}'s photos folder was last modifed on {} ({} days ago)".format(user, modifyDate, modifyDelta.days)
            if modifyDelta.days % 7 == 0 and modifyDelta.days != 0:
                await alerts.send(photoString)
            await channel.send(photoString)

                

bot = MyClient(command_prefix='.!.!.!', intents=discord.Intents().all())

def getCurrentTime():
    return [currentTime().hour, currentTime().minute]

bot.run(TOKEN)
