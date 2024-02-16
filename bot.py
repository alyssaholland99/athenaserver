# bot.py
import os

import discord
from dotenv import load_dotenv
from mcstatus import JavaServer

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.all()
client = discord.Client(intents=intents)

palworldCommands = ["info", 'players', 'restart']
minecraftCommands = ["info", 'players', 'start']
serverCommands = ["info", 'players', 'restart']
helpCommands = {
    "minecraft" : minecraftCommands,
    "palworld" : palworldCommands,
    "server" : serverCommands
}

@client.event
async def on_ready():
    await client.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="for .help"))
    print(f'{client.user} has connected to Discord!')

@client.event
async def on_message(message):

        global helpCommands

        # don't respond to ourselves
        if message.author == client.user:
            return

        if not message.content.startswith('.'):
            return
        msg = message.content[1:].lower()

        if len(msg.split(" ")) == 1 and msg.split(" ")[0] != 'help':
            await message.channel.send("Invalid command, use '.help' to see options")
            return

        match (msg.split(" ")[0]):

            case 'help':
                sendMessage = "Help:"
                for key, value in helpCommands.items():
                    sendMessage += "- " + key
                    for command in value:
                        sendMessage += "  - " + command
                sendMessage += "\nExample: .palworld players"
                await message.channel.send(sendMessage)

            case "server":
                match (msg.split(" ")[1]):
                    case "uptime":
                        await message.channel.send((os.popen("uptime").read()).split(",")[0].split("up")[1])
                    case "load":
                        initload = (os.popen("uptime").read()).split(",")[3]
                        load = initload.split(":")[1]
                        load = (float(load)/12)*100
                        load = str(round(load, 2)) +"%"
                        await message.channel.send("CPU usage: " + load)

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
                                playerSend += "\n" + i.split(",")[0]
                        if playerSend == "Players currently online:":
                            playerSend = "There are currently no players online"
                        await message.channel.send(playerSend)
                    case "restart":
                        restartStatus = os.popen("/srv/dev-disk-by-uuid-8479d8ee-6385-4a78-bdaf-0a485ac3d4c7/palworld/update_restart.sh").read()
                        await message.channel.send(restartStatus)
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
                            await message.channel.send("The server has the following players online: \n{}".format("\n".join(query.players.names)))
                        else:
                            await message.channel.send("There are currently no players online")
                    case "start":
                        os.system("/bin/systemctl start minecraft")
                        await message.channel.send("Starting Minecraft server")
                return
            
            case _:
                await message.channel.send("Invalid command, use '.help' to see options")

            


client.run(TOKEN)