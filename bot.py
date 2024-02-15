# bot.py
import os

import discord
from dotenv import load_dotenv
from mcstatus import JavaServer

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.all()
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    client.change_presence(status=discord.Status.Online, activity=discord.ActivityType.watching('for .help'))
    print(f'{client.user} has connected to Discord!')

@client.event
async def on_message(message):
        # don't respond to ourselves
        if message.author == client.user:
            return

        if not message.content.startswith('.'):
            return
        msg = message.content[1:].toLower()

        if msg == 'ping':
            await message.channel.send('pong')

        if msg.split(" ")[0] == 'help':
            sendMessage = "HELP:"
            sendMessage += "\n.[game] [game_command]"
            sendMessage += "\n- minecraft"
            sendMessage += "\n    - players"
            sendMessage += "\n  - start"
            sendMessage += "\n- palworld"
            sendMessage += "\n    - players"
            sendMessage += "\n  - restart"
            sendMessage += "\nExample: .palworld players"
            await message.channel.send(sendMessage)

        if msg.split(" ")[0] == "palworld":
            if msg.split(" ")[1] == "players":
                players = os.popen("/bin/docker exec palworld-dedicated-server rcon showPlayers").read()
                players = players.splitlines()
                playerSend = "Players currently online:"
                for i in players:
                    if i.split(",")[0] != "name":
                        playerSend += "\n" + i.split(",")[0]
                if playerSend == "Players currently online:":
                    playerSend = "There are currently no players online"
                await message.channel.send(playerSend)
            if msg.split(" ")[1] == "restart":
                restartStatus = os.popen("/srv/dev-disk-by-uuid-8479d8ee-6385-4a78-bdaf-0a485ac3d4c7/palworld/update_restart.sh").read()
                await message.channel.send(restartStatus)

        if msg.split(" ")[0] == "minecraft":
            minecraft = JavaServer.lookup("192.168.0.120:25565")
            if msg.split(" ")[1] == "players":
                query = minecraft.query()
                status = minecraft.status()
                if status.players.online > 0:
                    await message.channel.send("The server has the following players online: \n{}".format("\n".join(query.players.names)))
                else:
                    await message.channel.send("There are currently no players online")
            if msg.split(" ")[1] == "start":
                os.system("/bin/systemctl start minecraft")
                await message.channel.send("Starting Minecraft server")


client.run(TOKEN)