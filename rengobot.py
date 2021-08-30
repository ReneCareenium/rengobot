import os
import ast
import time
from datetime import datetime, timedelta
import asyncio

import sgfengine

import discord
from discord.ext import commands

# We don't use fancy slash commands here. It seems there is this library for python but it looks a bit more involved.
# https://pypi.org/project/discord-py-slash-command/
bot = commands.Bot(command_prefix='$', help_command=None)

# People who can start and resign games :O
# Later we might replace this with checking for a role.
admins=[ 756220448118669463, # Young Sun
         732403731810877450, # Yeonwoo
         145294584077877249, # Mrchance
         477895596141707264  # René
        ]

with open("token.txt") as f:
    token = f.readlines()[0] # Get your own token and put it in token.txt
f.close()

#client= discord.Client()

#@bot.command()
#async def test(ctx, arg1, arg2):
#    await ctx.send('You passed {} and {}'.format(arg1, arg2))

@bot.command()
async def help(ctx):
    print(ctx.message.content)
    await ctx.send(
            '$help : shows this help\n\n'+
            '$join : join the game in this channel\n'+
            '$leave: leave the game in this channel\n'+
            '$play <move>: play a move. For example, `$play Q16`\n\n'+
            '$sgf: get the sgf file of the game\n'+
            '$queue: get the queue of players\n\n'+
            '$newgame <queue/random>: starts a game in this channel (admin only!)\n'+
            '$resign <B/W>: resigns the game in this channel (admin only!)'
            )
    # ctx has guild, message, author, send, and channel (?)

@bot.command()
async def play(ctx, arg):
    channel_id= ctx.channel.id
    user = ctx.author

    # lowest effort serialization
    with open("state.txt") as f: state = ast.literal_eval(f.read())
    f.close()

    filter_state= [i for i in range(len(state))  if state[i][0] == channel_id]
    if not filter_state:
        await ctx.send("No active game in this channel!")
        return

    i= filter_state[0]

    if state[i][1] == queue and user.id not in state[i][4]:
        await ctx.send("Player hasn't joined yet! Join us with `$join`")
        return

    if state[i][1] == queue and user.id!= state[i][4][0]:
        await ctx.send("It is not your turn yet!")
        return

    legal_moves=[chr(col+ord('A')-1)+str(row) for col in range(1,21) if col!=9 for row in range(1,20)] 
    if arg not in legal_moves:
        await ctx.send("I don't understand the move! Please input it in the format `$play Q16`")
        return

    # TODO test for last player to move and time in free games
    # perhaps we could switch it to max one move per player every 5 turns, put the last few players in state[i][4]

    try:
        sgfengine.play_move(str(channel_id), arg, user.name)
    except ValueError as e:
        await ctx.send(str(e))
        return

    state[i][4].pop(0)
    state[i][4].append(user.id)

    file = discord.File(str(ctx.channel.id)+".png")
    if state[i][1]=="queue":
        next_player=(await bot.fetch_user(state[i][4][0]))
        await ctx.send(file=file, content="{}'s turn! ⭐".format(next_player.mention))
    else:
        await ctx.send(file=file)

    with open("state.txt", "w") as f: f.write(repr(state))
    f.close()

@bot.command()
async def join(ctx):
    channel_id= ctx.channel.id
    user = ctx.author

    # lowest effort serialization
    with open("state.txt") as f: state = ast.literal_eval(f.read())
    f.close()

    filter_state= [i for i in range(len(state))  if state[i][0] == channel_id]
    if not filter_state:
        await ctx.send("No active game in this channel!")
        return

    i= filter_state[0]

    if user.id in state[i][4]:
        await ctx.send("Player already in this game!")
        return

    if state[i][1] != "queue":
        await ctx.send("This game has no queue! Play whenever you want :P")
        return

    state[i][4].append(user.id)

    await ctx.send("User joined!")

    with open("state.txt", "w") as f: f.write(repr(state))
    f.close()

@bot.command()
async def queue(ctx):
    channel_id= ctx.channel.id

    # lowest effort serialization
    with open("state.txt") as f: state = ast.literal_eval(f.read())
    f.close()

    filter_state= [i for i in range(len(state))  if state[i][0] == channel_id]
    if not filter_state:
        await ctx.send("No active game in this channel!")
        return

    i= filter_state[0]

    if state[i][1] != "queue":
        await ctx.send("This game has no queue! Play whenever you want :P")
        return

    output= "Player list:\n"
    for i, player_id in enumerate(state[i][4]):
        player_name=(await bot.fetch_user(player_id)).name
        output+=str(i+1)+". "+ player_name+"\n"

    if not state[i][4]:
        output+="Nobody yet! Join us with `$join`"

    await ctx.send(output)

@bot.command()
async def sgf(ctx):
    file = discord.File(str(ctx.channel.id)+".sgf")
    await ctx.send(file=file)

@bot.command()
async def leave(ctx):
    channel_id= ctx.channel.id
    user = ctx.author

    # lowest effort serialization
    with open("state.txt") as f: state = ast.literal_eval(f.read())
    f.close()

    filter_state= [i for i in range(len(state))  if state[i][0] == channel_id]
    if not filter_state:
        await ctx.send("No active game in this channel!")
        return

    i= filter_state[0]

    if user.id not in state[i][4]:
        await ctx.send("Player not in this game!")
        return

    if state[i][1] != "queue":
        await ctx.send("This game has no queue! No need to leave!")
        return

    state[i][4].remove(user.id)

    await ctx.send("User left :(")

    with open("state.txt", "w") as f: f.write(repr(state))
    f.close()

@bot.command()
async def newgame(ctx, arg):
    channel_id= ctx.channel.id
    user = ctx.author

    if user.id not in admins:
        await ctx.send("You don't have permissions for this!")
        return

    if arg not in ["queue", "random"]:
        await ctx.send("Unrecognized game type! Please try `$newgame <queue/random>")
        return

    # lowest effort serialization
    with open("state.txt") as f: state = ast.literal_eval(f.read())
    f.close()

    if ctx.channel.id in [ ch for (ch,_,_,_,_) in state]:
        await ctx.send("A game is already active in this channel!")
        return

    sgfengine.new_game(str(ctx.channel.id))
    state.append((ctx.channel.id, arg, None, None, []))

    file = discord.File(str(ctx.channel.id)+".png")
    if arg=="queue":
        await ctx.send(file=file, content="A new game has started! Join with `$join`")
    else:
        await ctx.send(file=file, content="A new game has started! Play with `$play <move>`")

    with open("state.txt", "w") as f: f.write(repr(state))
    f.close()

@bot.command()
async def resign(ctx, arg):
    channel_id= ctx.channel.id
    user = ctx.author

    if user.id not in admins:
        await ctx.send("You don't have permissions for this!")
        return

    if arg not in ["W","B"]:
        await ctx.send("Unrecognized colour! Please try `$resign <B/W>` to resign as Black/White")
        return

    with open("state.txt") as f: state = ast.literal_eval(f.read())
    f.close()

    now=datetime.now()
    file_name= "rengo_"+now.strftime("%Y_%m_%d_%H_%M_%S_")+ctx.channel.name+".sgf" #remove the hour minute and second later

    sgfengine.resign(str(channel_id), arg, file_name)

    file = discord.File(file_name)
    await ctx.send(file=file, content=("Black" if arg=="W" else "White")+" wins!")

    state = [s for s in state if s[0]!=channel_id]

    with open("state.txt", "w") as f: f.write(repr(state))
    f.close()

async def background_task():
    await bot.wait_until_ready()
    print("bot ready!")

    guild=discord.utils.get(bot.guilds, name="Awesome Baduk")

    while not bot.is_closed():
        try:
            print("ping")
            await asyncio.sleep(1000)

            # lowest effort serialization
            with open("state.txt") as f: state = ast.literal_eval(f.read())
            f.close()

            #TODO find who has to move, skip players accordingly, notify if any has to move

            with open("state.txt") as f: f.write(repr(state))
            f.close()

        except ConnectionResetError:
            print("Connection error")

bot.loop.create_task(background_task())
bot.run(token)

