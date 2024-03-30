# bot.py
import os

import discord
from dotenv import load_dotenv
from mcstatus import JavaServer
from requests import get
import time
from datetime import datetime

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.all()
client = discord.Client(intents=intents)

servicePorts = {
    "Palworld" : "8211",
    "Minecraft" : "25565",
    "Valheim" : "2456",
    "Sons of the Forest" : "8766"
}

palworldCommands = ["info", "status", "players", "backup", "start", "restart", "stop\*"]
minecraftCommands = ["info", "status", "players", "start", "stop\*"]
valheimCommands = ["info", "status", "start", "stop\*"]
sotfCommands = ["info", "status", "backup", "start\* [force]", "restart\*", "stop\*"]
serverCommands = ["uptime", "load", "memory"]
botCommands = ["add", "info", "code", "delete [channel_id] [message_id]*"]
trustCommands = ["add\*", "remove\*", "list"]
serviceCommands = ["status"]
photoprismCommands = ["start\*", "stop\*"]
helpCommands = [{
    "minecraft" : minecraftCommands,
    "palworld" : palworldCommands,
    "valheim" : valheimCommands,
    "forest/sotf" : sotfCommands
},
{
    "photoprism" : photoprismCommands,
    "server" : serverCommands,
    "bot" : botCommands,
    "trust" : trustCommands,
    "service" : serviceCommands
}]

trustedPath = "/root/athenaserver/trustedUsers.txt"

@client.event
async def on_ready():
    await client.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="for .help"))
    print(f'{client.user} has connected to Discord!')

@client.event
async def on_message(message):

        global helpCommands
        global trustedPath
        global servicePorts

        # don't respond to ourselves
        if message.author == client.user:
            return

        if not message.content.startswith('.'):
            return
        if message.content.startswith('..'):
            return
        
        msg = message.content[1:].lower()

        await logCommand(message)

        match (msg.split(" ")[0]):

            case 'help' | "h":
                if len(msg.split(" ")) == 2:
                    match (msg.split(" ")[1]):
                        case '1' | '2':
                            await message.channel.send(makeHelpMessage(int(msg.split(" ")[1])))
                        case '*':
                            await message.channel.send(makeHelpMessage('all'))
                        case _:
                            await message.channel.send(getHelpForService(msg.split(" ")[1]))
                            return
                else:
                    await message.channel.send(makeHelpMessage("1") + "\nUse `.help 2` to see other commands available")
                
            case "server":
                if len(msg.split(" ")) == 1:
                    await message.channel.send(commandError("server"))
                    return
                match (msg.split(" ")[1]):
                    case "uptime":
                        await message.channel.send((os.popen("uptime").read()).split(",")[0].split("up")[1])
                    case "load":
                        load = (os.popen("/bin/cat /proc/loadavg").read()).split(" ")[0]
                        load = (float(load)/12)*100
                        load = str(round(load, 2)) +"%"
                        await message.channel.send("CPU usage: " + load)
                    case "memory":
                        memoryPercent = os.popen("free | grep Mem | awk '{print $3/$2 * 100}'").read()
                        await message.channel.send("Memory usage: {}%".format(round(float(memoryPercent), 1)))
                    case _:
                        await message.channel.send(commandError(msg.split(" ")[0]))

            case "palworld" | "pal":
                if len(msg.split(" ")) == 1:
                    await message.channel.send(commandError("palworld"))
                    return
                match (msg.split(" ")[1]):
                    case "info":
                        await message.channel.send("Server address for Palworld: `server.alyssaserver.co.uk:{}`\nPassword: `{}`".format(servicePorts["Palworld"], os.getenv('PAL_PASS')))
                    case "status":
                        if isRunning(servicePorts["Palworld"]): 
                            await message.channel.send("The Palworld server is running")
                        else:
                            await message.channel.send("The Palworld server is not running")
                    case "players":
                        if not isRunning(servicePorts["Palworld"]):
                            await message.channel.send("The Palworld server is not running - Use `.palworld start` to start it")
                            return
                        players = os.popen("/bin/docker exec palworld-dedicated-server rcon showPlayers").read()
                        players = players.splitlines()
                        playerSend = "Players currently online:"
                        for i in players:
                            if i.split(",")[0] != "name":
                                playerSend += "\n- " + i.split(",")[0]
                        if playerSend == "Players currently online:":
                            playerSend = "There are currently no players online"
                        await message.channel.send(playerSend)
                    case "restart":
                        if not isRunning(servicePorts["Palworld"]):
                            await message.channel.send("The Palworld server is not running - Use `.palworld start` to start it")
                            return
                        await message.channel.send("Backing up palworld", delete_after=5)
                        os.system("/bin/docker exec palworld-dedicated-server backup create")
                        await message.channel.send("Palworld backup created")
                        time.sleep(2)
                        restartStatus = os.popen("/srv/dev-disk-by-uuid-8479d8ee-6385-4a78-bdaf-0a485ac3d4c7/palworld/update_restart.sh").read()
                        await message.channel.send(restartStatus)
                    case "stop":
                        if isTrusted(message.author):
                            if not isRunning(servicePorts["Palworld"]):
                                await message.channel.send("The Palworld server is already stopped")
                                return
                            await message.channel.send("Backing up palworld", delete_after=5)
                            os.system("/bin/docker exec palworld-dedicated-server backup create")
                            await message.channel.send("Palworld backup created")
                            time.sleep(2)
                            restartStatus = os.popen("/srv/dev-disk-by-uuid-8479d8ee-6385-4a78-bdaf-0a485ac3d4c7/palworld/stop.sh").read()
                            await message.channel.send(restartStatus)
                        else:
                            await message.channel.send(getInsufficentPermissionMessage())
                    case "start":
                        if isRunning(servicePorts["Palworld"]):
                            await message.channel.send("The Palworld server is already running")
                            return
                        restartStatus = os.system(" /bin/docker-compose -f /srv/dev-disk-by-uuid-8479d8ee-6385-4a78-bdaf-0a485ac3d4c7/palworld/docker-compose.yml up -d >> /dev/null 2>&1")
                        await message.channel.send("Palworld server starting")
                    case "backup":
                        if not isRunning(servicePorts["Palworld"]):
                            await message.channel.send("The Palworld server is not running - Use `.palworld start` to start it")
                            return
                        await message.channel.send("Backing up palworld", delete_after=5)
                        os.system("/bin/docker exec palworld-dedicated-server backup create")
                        await message.channel.send("Palworld backup created")
                    case _:
                        await message.channel.send(commandError("palworld"))
                return

            case "minecraft" | "mine":
                minecraft = JavaServer.lookup("192.168.0.120:{}".format(servicePorts["Minecraft"]))
                if len(msg.split(" ")) == 1:
                    await message.channel.send(commandError("minecraft"))
                    return
                match (msg.split(" ")[1]):
                    case "info":
                        await message.channel.send("Server address for Minecraft: `server.alyssaserver.co.uk:{}`\nOnline Map: <http://server.alyssaserver.co.uk:8000>".format(servicePorts["Minecraft"]))
                    case "status":
                        if isRunning(servicePorts["Minecraft"]): 
                            await message.channel.send("The Minecraft server is running")
                        else:
                            await message.channel.send("The Minecraft server is not running")
                    case "players":
                        if not isRunning(servicePorts["Minecraft"]):
                            await message.channel.send("The Minecraft server is not running, use `.minecraft start` to start it")
                            return
                        query = minecraft.query()
                        status = minecraft.status()
                        if status.players.online > 0:
                            await message.channel.send("Players currently online: \n- {}".format("\n- ".join(query.players.names)))
                        else:
                            await message.channel.send("There are currently no players online")
                    case "start":
                        if isRunning(servicePorts["Minecraft"]):
                            await message.channel.send("The Minecraft server is already running")
                            return
                        os.system("/bin/systemctl start minecraft")
                        await message.channel.send("Starting Minecraft server")
                    case "stop":
                        if isTrusted(message.author):
                            if not isRunning(servicePorts["Minecraft"]):
                                await message.channel.send("The Minecraft server is already stopped")
                                return
                            status = minecraft.status()
                            if status.players.online == 0:
                                restartStatus = os.system("/bin/systemctl stop minecraft")
                                await message.channel.send("Stopping the minecraft server")
                            else: 
                                await message.channel.send("There are players currently on the world, not stopped")
                        else:
                            await message.channel.send(getInsufficentPermissionMessage())
                    case "restart":
                        await message.channel.send("This is disabled because it breaks the bot for some reason")
                        return
                        if isTrusted(message.author):
                            if not isRunning(servicePorts["Minecraft"]):
                                await message.channel.send("The Minecraft server is not running, use `.minecraft start` to start it")
                                return
                            status = minecraft.status()
                            if status.players.online == 0:
                                restartStatus = os.system("/bin/systemctl restart minecraft")
                                await message.channel.send("Restarting the minecraft server")
                            else: 
                                await message.channel.send("There are players currently on the world, not restarted")
                        else:
                            await message.channel.send(getInsufficentPermissionMessage())
                    case _:
                        await message.channel.send(commandError("minecraft"))
                return

            case "valheim" | "val":
                if len(msg.split(" ")) == 1:
                    await message.channel.send(commandError("valheim"))
                    return
                match (msg.split(" ")[1]):
                    case "info":
                        await message.channel.send("Server address for Valheim: `server.alyssaserver.co.uk:{}`\nPassword: `{}`".format(servicePorts["Valheim"], os.getenv('VAL_PASS')))
                    case "status":
                        if isRunning(servicePorts["Valheim"]): 
                            await message.channel.send("The Valheim server is running")
                        else:
                            await message.channel.send("The Valheim server is not running")
                    case "players":
                        #TODO
                        await message.channel.send("This command is currently WIP")
                    case "start":
                        if isRunning(servicePorts["Valheim"]):
                            await message.channel.send("The Valheim server is already running")
                            return
                        os.system("/bin/docker-compose -f /srv/dev-disk-by-uuid-8479d8ee-6385-4a78-bdaf-0a485ac3d4c7/valheim/docker-compose.yml up -d >> /dev/null 2>&1")
                        await message.channel.send("Starting the Valheim server")
                    case "stop":
                        if isTrusted(message.author):
                            if not isRunning(servicePorts["Valheim"]):
                                await message.channel.send("The Valheim server is already stopped")
                                return
                            restartStatus = os.system("/bin/docker-compose -f /srv/dev-disk-by-uuid-8479d8ee-6385-4a78-bdaf-0a485ac3d4c7/valheim/docker-compose.yml down >> /dev/null 2>&1")
                            await message.channel.send("Stopping the Valheim server")
                        else:
                            await message.channel.send(getInsufficentPermissionMessage())
                    case "restart":
                        if isTrusted(message.author):
                            if not isRunning(servicePorts["Valheim"]):
                                await message.channel.send("The Valheim server is not running, use `.valheim start` to start it")
                                return
                            restartStatus = os.system("/bin/docker-compose -f /srv/dev-disk-by-uuid-8479d8ee-6385-4a78-bdaf-0a485ac3d4c7/valheim/docker-compose.yml down >> /dev/null 2>&1 && /bin/docker-compose -f /srv/dev-disk-by-uuid-8479d8ee-6385-4a78-bdaf-0a485ac3d4c7/valheim/docker-compose.yml up -d >> /dev/null 2>&1")
                            await message.channel.send("Restarting the Valheim server")
                        else:
                            await message.channel.send(getInsufficentPermissionMessage())
                    case _:
                        await message.channel.send(commandError("valheim"))
                return

            case "forest" | "sotf":
                if len(msg.split(" ")) == 1:
                    await message.channel.send(commandError("forest"))
                    return
                match (msg.split(" ")[1]):
                    case "info":
                        ip = get('https://api.ipify.org').content.decode('utf8')
                        await message.channel.send("Server name: Aly's SotF server\nServer address: `{}:{}`\nPassword: `{}`".format(ip, servicePorts["Sons of the Forest"], os.getenv('SOTF_PASS'))) ## GET IP
                    case "status":
                        if isRunning(servicePorts["Sons of the Forest"]): 
                            await message.channel.send("The Sons of the Forest server is running")
                        else:
                            await message.channel.send("The Sons of the Forest server is not running")
                    case "start":
                        if isTrusted(message.author):
                            if isRunning(servicePorts["Sons of the Forest"]): 
                                await message.channel.send("The Sons of the Forest server is already running")
                                return
                            if isRunning(servicePorts["Palworld"]):
                                if len(msg.split(" ")) == 3 and msg.split(" ")[2] == "force":
                                    await message.channel.send("The palworld server is currently running, forcing start anyway - Making backup of palworld as a precaution")
                                    await message.channel.send("Backing up palworld", delete_after=5)
                                    os.system("/bin/docker exec palworld-dedicated-server backup create")
                                    await message.channel.send("Palworld backup created")
                                else:
                                    await message.channel.send("Please stop the Palworld server before starting this server, once Sons of the Forest is running you can start Palworld again\nThis is to prevent world corruption in the case of a server crash\nYou can use `.sotf start force` to skip this check")
                                    return
                            os.system("/bin/docker-compose -f /srv/dev-disk-by-uuid-8479d8ee-6385-4a78-bdaf-0a485ac3d4c7/sons_of_the_forest/docker-compose.yml up -d >> /dev/null 2>&1")
                            await message.channel.send("Starting the Sons of the Forest server\nPlease note: It may take a while (3-6 minutes) for the server to start correctly, another message will confirm when the server is running")
                            await message.channel.send(ensureSotFServerStarts())
                        else:
                            await message.channel.send("Due to server crashing issues with SotF only admins can turn on the server\n" + getInsufficentPermissionMessage())
                    case "stop":
                        if isTrusted(message.author):
                            if not isRunning(servicePorts["Sons of the Forest"]): 
                                await message.channel.send("The Sons of the Forest server is already stopped")
                                return
                            await message.channel.send(backupSotF())
                            restartStatus = os.system("/bin/docker-compose -f /srv/dev-disk-by-uuid-8479d8ee-6385-4a78-bdaf-0a485ac3d4c7/sons_of_the_forest/docker-compose.yml down >> /dev/null 2>&1")
                            await message.channel.send("Stopping the Sons of the Forest server")
                        else:
                            await message.channel.send(getInsufficentPermissionMessage())
                    case "restart":
                        if isTrusted(message.author):
                            if not isRunning(servicePorts["Sons of the Forest"]): 
                                await message.channel.send("The Sons of the Forest server is not running, use `.sotf start` to start the server")
                                return
                            if isRunning(servicePorts["Palworld"]): 
                                await message.channel.send("Please stop the Palworld server before restarting this server, once SofF is running you can start Palworld")
                                return
                            await message.channel.send(backupSotF())
                            restartStatus = os.system("/bin/docker-compose -f /srv/dev-disk-by-uuid-8479d8ee-6385-4a78-bdaf-0a485ac3d4c7/sons_of_the_forest/docker-compose.yml down >> /dev/null 2>&1 && /bin/docker-compose -f /srv/dev-disk-by-uuid-8479d8ee-6385-4a78-bdaf-0a485ac3d4c7/sons_of_the_forest/docker-compose.yml up -d >> /dev/null 2>&1")
                            await message.channel.send("Restarting the Sons of the Forest server")
                        else:
                            await message.channel.send(getInsufficentPermissionMessage())
                    case "backup":
                        await message.channel.send(backupSotF())
                    case _:
                        await message.channel.send(commandError("forest/sotf"))

            case "photo" | "photos" | "photoprism":
                if len(msg.split(" ")) == 1:
                    await message.channel.send(commandError("photoprism"))
                    return
                if not isTrusted(message.author):
                    await message.channel.send(getInsufficentPermissionMessage())
                    return
                match (msg.split(" ")[1]):
                    case "start":
                        os.system("/bin/docker-compose -f /root/Photoprism/docker-compose.yml up -d >> /dev/null 2>&1")
                        await message.channel.send("Starting Photoprism")
                    case "stop":
                        os.system("/bin/docker-compose -f /root/Photoprism/docker-compose.yml down >> /dev/null 2>&1")
                        await message.channel.send("Stopping Photoprism")
                    case _:
                        await message.channel.send(commandError("photoprism"))
            
            case "trust":
                if len(msg.split(" ")) == 1:
                    await message.channel.send(commandError("trust"))
                    return
                match (msg.split(" ")[1]):
                    case "add":
                        if isTrusted(message.author):
                            if isTrusted(msg.split(" ")[2]):
                                await message.channel.send("{} is already a trusted user of this bot".format(msg.split(" ")[2]))
                                return
                            trustedFile = open(trustedPath, "a")
                            trustedFile.write("{}\n".format(msg.split(" ")[2]))
                            trustedFile.close()
                            await message.channel.send("Added {} to trusted users".format(msg.split(" ")[2]))
                        else:
                            await message.channel.send(getInsufficentPermissionMessage())
                    case "remove":
                        if isTrusted(message.author):
                            if isTrusted(msg.split(" ")[2]):
                                trustedFile = open(trustedPath, "r")
                                trustedUsers = trustedFile.read()
                                trustedFile.close()
                                newTrustedUsers = ""
                                for line in trustedUsers.splitlines():
                                    if line.replace("\n", "") != msg.split(" ")[2]:
                                        newTrustedUsers += line + "\n"
                                trustedFile = open(trustedPath, "w")
                                trustedFile.write(newTrustedUsers)
                                trustedFile.close()
                                await message.channel.send("Removed {} from trusted users".format(msg.split(" ")[2]))
                            else:
                                await message.channel.send("{} is not a trusted user".format(msg.split(" ")[2]))
                        else:
                            await message.channel.send(getInsufficentPermissionMessage())
                    case "list":
                        trustedFile = open(trustedPath, "r")
                        trustedUsers = "Trusted users:\n"
                        for u in trustedFile:
                            trustedUsers += "- {}".format(u)
                        trustedFile.close()
                        await message.channel.send(trustedUsers)
                    case _:
                        await message.channel.send(commandError(msg.split(" ")[0]))
                return

            case "bot":
                if len(msg.split(" ")) == 1:
                    await message.channel.send(commandError("bot"))
                    return
                match (msg.split(" ")[1]):
                    case "add":
                        await message.channel.send("Use the following link to add this bot yo your server:\nhttps://discord.com/api/oauth2/authorize?client_id=1207456482170249287&permissions=3072&scope=bot")
                    case "info":
                        await message.channel.send("This bot is being used in {} servers".format(str(len(client.guilds))))
                    case "code" | "git":
                        await message.channel.send("Source code: https://github.com/alyssaholland99/athenaserver")
                    case "delete": 
                        if isTrusted(message.author):
                            if len(msg.split(" ")) == 4:
                                try:
                                    ch = client.get_channel(int(msg.split(" ")[2]))
                                    messageToDelete = await ch.fetch_message(int(msg.split(" ")[3]))
                                    await messageToDelete.delete()
                                except Exception as e:
                                    await message.channel.send("Incorrect syntax - Usage `bot delete [channel_id] [message_id]")
                            else:
                                await message.channel.send("Incorrect syntax - Usage `bot delete [channel_id] [message_id]")
                        else:
                            await message.channel.send(getInsufficentPermissionMessage())
                    case _:
                        await message.channel.send(commandError(msg.split(" ")[0]))

            case "service":
                if len(msg.split(" ")) == 1:
                    await message.channel.send(commandError("service"))
                    return
                match (msg.split(" ")[1]):
                    case "status":
                        runningServices = []
                        stoppedServices = []
                        for service, port in servicePorts.items():
                            if isRunning(port):
                                runningServices.append(service)
                            else:
                                stoppedServices.append(service)
                        messageConst = ""
                        if len(runningServices) > 0:
                            messageConst += "Running Services:\n"
                            for s in runningServices:
                                messageConst += "- {}\n".format(s)
                        if len(stoppedServices) > 0:
                            messageConst += "Stopped Services:\n"
                            for s in stoppedServices:
                                messageConst += "- {}\n".format(s)
                            messageConst += "You can use `.[service] start` to start the service"
                        await message.channel.send(messageConst)
                    case _:
                        await message.channel.send(commandError(msg.split(" ")[0]))

            case _:
                await message.channel.send(getInvalidServiceMessage())

def backupSotF():
    os.system("tar -zcvf /srv/dev-disk-by-uuid-8479d8ee-6385-4a78-bdaf-0a485ac3d4c7/sons_of_the_forest/backups/\"$(date '+%Y-%m-%d_%H:%M:%S')_sotf.tar.gz\" /srv/dev-disk-by-uuid-8479d8ee-6385-4a78-bdaf-0a485ac3d4c7/sons_of_the_forest/game/userdata/Saves >> /dev/null 2>&1")
    return "Backing up the Sons of the Forest server"

def ensureSotFServerStarts():
    running = False
    retryCount = 0
    time.sleep(200)
    while running == False:
        sotfStatus = os.popen("docker logs sons-of-the-forest-dedicated-server 2>&1 | grep 'server/fd.c:1644'").read()
        if len(sotfStatus.splitlines()) > 0:
            os.system("/bin/docker-compose -f /srv/dev-disk-by-uuid-8479d8ee-6385-4a78-bdaf-0a485ac3d4c7/sons_of_the_forest/docker-compose.yml down >> /dev/null 2>&1 && /bin/docker-compose -f /srv/dev-disk-by-uuid-8479d8ee-6385-4a78-bdaf-0a485ac3d4c7/sons_of_the_forest/docker-compose.yml up -d >> /dev/null 2>&1")
            time.sleep(120)
            retryCount += 1
            if retryCount >= 10:
                return "The Sons of the Forest failed to start correctly"
        else:
            running = True
    return "The Sons of the Forest server is running"

def isRunning(port):
    runningServices = os.popen("/bin/lsof -i:{}".format(port)).read()
    return len(runningServices.splitlines()) > 0

def makeHelpMessage(index):
    
    global helpCommands

    if index == "all":
        commands = getAllCommands()
    else:
        commands = helpCommands[int(index)-1]

    sendMessage = "\nSyntax: `.[service] [command]`"
    for key, value in commands.items():
        sendMessage += "\n- {}".format(key)
        joinedCommands = ", ".join(value)
        sendMessage += "\n  - {}".format(joinedCommands)
    sendMessage += "\n*Trusted users only\nExample: `.palworld players`"
    return sendMessage

def getInsufficentPermissionMessage():
    return "You do not have permission to run this command - use `.trust list` to see who has permission"

def isTrusted(user):
    global trustedPath
    trustedFile = open(trustedPath, "r")
    for u in trustedFile:
        if str(user) == u.replace("\n", ""):
            trustedFile.close()
            return True
    trustedFile.close()
    return False

def getAllCommands():

    global helpCommands

    return {**helpCommands[0], **helpCommands[1]}


def getHelpForService(service):

    allCommands = getAllCommands()

    if (service not in allCommands):
        return getInvalidServiceMessage()
    
    return "Syntax: `.{} [command]`\nAvailable commands for service {}:\n{}*Trusted users only".format(service, service, getCommands(service))

def commandError(service):

    allCommands = getAllCommands()

    if (service not in allCommands):
        return getInvalidServiceMessage()

    return "Syntax: `.{} [command]`\nThis is not a valid command for {}, please pick from the following:\n{}".format(service, service, getCommands(service))
            
def getCommands(service):

    allCommands = getAllCommands()

    if (service not in allCommands):
        return getInvalidServiceMessage()
    
    validCommands = allCommands[service]

    returnOptions = ""

    for commands in validCommands:
        returnOptions += "- " + commands + "\n"

    return returnOptions

def getInvalidServiceMessage():

    allCommands = getAllCommands()

    services = list(allCommands.keys())

    serviceList = ""

    for service in services:
        serviceList += "- {}\n".format(service)

    return "This is not a valid service, please use `.help [service]` to see valid commands for that service (you can also use `.help` to view all)\nServices:\n{}".format(serviceList)

async def logCommand(msg):
    now = datetime.now()
    ch = client.get_channel(1213120151361429594)
    await ch.send("{} | User: `{}` - Command: `{}`".format(now.strftime("%d/%m/%Y %H:%M:%S"), msg.author, msg.content))

client.run(TOKEN)
