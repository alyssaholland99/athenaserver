# bot.py
import os

import discord
from dotenv import load_dotenv
from mcstatus import JavaServer

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.all()
client = discord.Client(intents=intents)

palworldCommands = ["info", "players", "start", "restart", "stop\*"]
minecraftCommands = ["info", "players", "start", "restart\*", "stop\*"]
valheimCommands = ["info", "start", "stop\*"]
serverCommands = ["uptime", "load", "memory"]
botCommands = ["add", "info"]
trustCommands = ["add\*", "remove\*", "list"]
helpCommands = [{
    "minecraft" : minecraftCommands,
    "palworld" : palworldCommands,
    "valheim" : valheimCommands,
},
{
    "server" : serverCommands,
    "bot" : botCommands,
    "trust" : trustCommands
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

        # don't respond to ourselves
        if message.author == client.user:
            return

        if not message.content.startswith('.'):
            return
        if message.content.startswith('..'):
            return
        
        msg = message.content[1:].lower()

        if len(msg.split(" ")) == 1 and msg.split(" ")[0] != "help":
            await message.channel.send(commandError(msg.split(" ")[0]))
            return

        match (msg.split(" ")[0]):

            case 'help':
                if len(msg.split(" ")) == 2:
                    match (msg.split(" ")[1]):
                        case '1' | '2':
                            await message.channel.send(makeHelpMessage(int(msg.split(" ")[1])))
                        case _:
                            await message.channel.send(getHelpForService(msg.split(" ")[1]))
                            return
                else:
                    await message.channel.send(makeHelpMessage("1") + "\nUse `.help 2` to see other commands available")
                

            case "server":
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

            case "palworld":
                match (msg.split(" ")[1]):
                    case "info":
                        await message.channel.send("Server address: server.alyssaserver.co.uk:8211\nPlease ask Aly for the password")
                    case "players":
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
                        restartStatus = os.popen("/srv/dev-disk-by-uuid-8479d8ee-6385-4a78-bdaf-0a485ac3d4c7/palworld/update_restart.sh").read()
                        await message.channel.send(restartStatus)
                    case "stop":
                        if isTrusted(message.author):
                            restartStatus = os.popen("/srv/dev-disk-by-uuid-8479d8ee-6385-4a78-bdaf-0a485ac3d4c7/palworld/stop.sh").read()
                            await message.channel.send(restartStatus)
                        else:
                            await message.channel.send(getInsufficentPermissionMessage())
                    case "start":
                        restartStatus = os.system(" /bin/docker-compose -f /srv/dev-disk-by-uuid-8479d8ee-6385-4a78-bdaf-0a485ac3d4c7/palworld/docker-compose.yml up -d >> /dev/null 2>&1")
                        await message.channel.send("Palworld server starting")
                    case _:
                        await message.channel.send(commandError(msg.split(" ")[0]))
                return

            case "minecraft":
                minecraft = JavaServer.lookup("192.168.0.120:25565")
                match (msg.split(" ")[1]):
                    case "info":
                        await message.channel.send("Server address: server.alyssaserver.co.uk:25565")
                    case "players":
                        query = minecraft.query()
                        status = minecraft.status()
                        if status.players.online > 0:
                            await message.channel.send("Players currently online: \n{}".format("\n- ".join(query.players.names)))
                        else:
                            await message.channel.send("There are currently no players online")
                    case "start":
                        os.system("/bin/systemctl start minecraft")
                        await message.channel.send("Starting Minecraft server")
                    case "stop":
                        if isTrusted(message.author):
                            status = minecraft.status()
                            if status.players.online == 0:
                                restartStatus = os.system("/bin/systemctl stop minecraft")
                                await message.channel.send("Stopping the minecraft server")
                            else: 
                                await message.channel.send("There are players currently on the world, not stopped")
                        else:
                            await message.channel.send(getInsufficentPermissionMessage())
                    case "restart":
                        if isTrusted(message.author):
                            status = minecraft.status()
                            if status.players.online == 0:
                                restartStatus = os.system("/bin/systemctl restart minecraft")
                                await message.channel.send("Restarting the minecraft server")
                            else: 
                                await message.channel.send("There are players currently on the world, not restarted")
                        else:
                            await message.channel.send(getInsufficentPermissionMessage())
                    case _:
                        await message.channel.send(commandError(msg.split(" ")[0]))
                return

            case "valheim":
                match (msg.split(" ")[1]):
                    case "info":
                        await message.channel.send("Server address: server.alyssaserver.co.uk:2456")
                    case "players":
                        #TODO
                        await message.channel.send("This command is currently WIP")
                    case "start":
                        os.system("/bin/docker-compose -f /srv/dev-disk-by-uuid-8479d8ee-6385-4a78-bdaf-0a485ac3d4c7/valheim/docker-compose.yml up -d >> /dev/null 2>&1")
                        await message.channel.send("Starting the Valheim server")
                    case "stop":
                        if isTrusted(message.author):
                            restartStatus = os.system("/bin/docker-compose -f /srv/dev-disk-by-uuid-8479d8ee-6385-4a78-bdaf-0a485ac3d4c7/valheim/docker-compose.yml down >> /dev/null 2>&1")
                            await message.channel.send("Stopping the Valheim server")
                        else:
                            await message.channel.send(getInsufficentPermissionMessage())
                    case _:
                        await message.channel.send(commandError(msg.split(" ")[0]))
                return
            
            case "trust":
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
                match (msg.split(" ")[1]):
                    case "add":
                        await message.channel.send("Use the following link to add this bot yo your server:\nhttps://discord.com/api/oauth2/authorize?client_id=1207456482170249287&permissions=3072&scope=bot")
                    case "info":
                        await message.channel.send("This bot is being used in {} servers".format(str(len(client.guilds))))
                    case "_":
                        await message.channel.send(commandError(msg.split(" ")[0]))

            case _:
                await message.channel.send(getInvalidServiceMessage())

def makeHelpMessage(index):
    global helpCommands

    commands = helpCommands[int(index)-1]

    sendMessage = "\nSyntax: `.[service] [command]`"
    for key, value in commands.items():
        sendMessage += "\n- {}".format(key)
        joinedCommands = ", ".join(value)
        sendMessage += "\n  - {}".format(joinedCommands)
    sendMessage += "\n*Trusted users only\nExample: `.palworld players`"
    return sendMessage

def getInsufficentPermissionMessage():
    return "You do not have permission to run this command"

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

client.run(TOKEN)
