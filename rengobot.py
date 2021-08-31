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

min_time_player= timedelta(seconds=1) # in random games, cooldown time between plays
time_to_skip= timedelta(days=1) # in queue games, how much time to wait for the next move
min_players = 2

# People who can start and resign games :O
admin_role = 'RCON' # Change this to the name of the role for your admins

with open("token.txt") as f:
    token = f.readlines()[0] # Get your own token and put it in token.txt

format="%Y_%m_%d_%H_%M_%S_%f"

# The state is a list of tuples (channel_id, "queue"/"random", last_players, last_times, [player_id])

@bot.command()
async def help(ctx):
    await ctx.send(
            '$help : shows this help\n\n'+

            '$join : join the game in this channel\n'+
            '$leave: leave the game in this channel\n'+
            '$play <move>: play a move. For example, `$play Q16`. Passing is not implemented!\n'+
            '$edit <move>: if you make a mistake in your move, you have 5 minutes to correct it with this command\n\n'+

            '$sgf: get the sgf file of the game\n'+
            '$board: shows the current board\n'+
            '$queue: get the queue of players\n\n'+

            '$newgame <queue/random>: starts a game in this channel (admin only!)\n'+
            '$resign <B/W>: resigns the game in this channel, and returns its sgf file (admin only!)'
            )
    # ctx has guild, message, author, send, and channel (?)

@bot.command()
async def play(ctx, arg):
    channel_id= ctx.channel.id
    user = ctx.author

    # lowest effort serialization
    with open("state.txt") as f: state = ast.literal_eval(f.read())

    filter_state= [i for i in range(len(state))  if state[i][0] == channel_id]
    if not filter_state:
        await ctx.send("No active game in this channel!")
        return

    i= filter_state[0]

    if state[i][1] == "queue" and user.id not in state[i][4]:
        await ctx.send("Player hasn't joined yet! Join us with `$join`")
        return

    if state[i][1] == "queue" and len(state[i][4]) <min_players:
        await ctx.send("Waiting for {} more players to join".format(min_players-len(state[i][4])))
        return

    if state[i][1] == "queue" and user.id!= state[i][4][0]:
        await ctx.send("It is not your turn yet!")
        return

    if state[i][1] == "random":
        assert( len(state[i][2]) == len(state[i][3]))

        if len(state[i][2])>0 and state[i][2][-1] == user.id:
            await ctx.send("No two consecutive moves by the same player!")
            return

        for j in range(len(state[i][2])):
            if (state[i][2][j] == user.id and
                datetime.now() - datetime.strptime(state[i][3][j],format) < min_time_player):
                await ctx.send("At most one move per player per day!")
                return


    if state[i][3] != [] and datetime.now()-datetime.strptime(state[i][3][-1],format)<timedelta(seconds=4):
        return #silent error

    legal_moves=[chr(col+ord('A')-1)+str(row) for col in range(1,21) if col!=9 for row in range(1,20)]
    legal_moves+=[chr(col+ord('a')-1)+str(row) for col in range(1,21) if col!=9 for row in range(1,20)]
    if arg not in legal_moves:
        await ctx.send("I don't understand the move! Please input it in the format `$play Q16`")
        return

    try:
        sgfengine.play_move(str(channel_id), arg, user.name)
    except ValueError as e:
        await ctx.send(str(e))
        return

    # move registered, let's do the other things
    state[i][2].append(user.id)
    state[i][3].append(datetime.now().strftime(format))

    if state[i][1] == "queue":
        state[i][4].pop(0)
        state[i][4].append(user.id)

    file = discord.File(str(ctx.channel.id)+".png")
    if state[i][1]=="queue":
        next_player=(await bot.fetch_user(state[i][4][0]))
        await ctx.send(file=file, content="{}'s turn! ⭐".format(next_player.mention))
    else:
        await ctx.send(file=file)

    with open("state.txt", "w") as f: f.write(repr(state))

@bot.command()
async def edit(ctx, arg): #literally play but with less things
    # It should wait until the queue has 4 players or so
    channel_id= ctx.channel.id
    user = ctx.author

    # lowest effort serialization
    with open("state.txt") as f: state = ast.literal_eval(f.read())

    filter_state= [i for i in range(len(state))  if state[i][0] == channel_id]
    if not filter_state:
        await ctx.send("No active game in this channel!")
        return

    i= filter_state[0]

    if state[i][1] == "queue" and user.id not in state[i][4]:
        await ctx.send("Player hasn't joined yet! Join us with `$join`")
        return

    if state[i][1] == "queue" and user.id!= state[i][4][0]:
        await ctx.send("It is not your turn yet!")
        return

    if state[i][2][-1] != user.id or datetime.now()-datetime.strptime(state[i][3][-1],format) > timedelta(minutes=5):
        await ctx.send("You cannot edit this move!")
        return

    legal_moves=[chr(col+ord('A')-1)+str(row) for col in range(1,21) if col!=9 for row in range(1,20)]
    legal_moves+=[chr(col+ord('a')-1)+str(row) for col in range(1,21) if col!=9 for row in range(1,20)]
    if arg not in legal_moves:
        await ctx.send("I don't understand the move! Please input it in the format `$play Q16`")
        return

    try:
        sgfengine.play_move(str(channel_id), arg, user.name, True)
    except ValueError as e:
        await ctx.send(str(e))
        return

    file = discord.File(str(ctx.channel.id)+".png")
    if state[i][1]=="queue":
        next_player=(await bot.fetch_user(state[i][4][0]))
        await ctx.send(file=file, content="{}'s turn! ⭐".format(next_player.name))
    else:
        await ctx.send(file=file)

    with open("state.txt", "w") as f: f.write(repr(state))

@bot.command()
async def board(ctx):
    channel_id= ctx.channel.id
    user = ctx.author

    with open("state.txt") as f: state = ast.literal_eval(f.read())

    filter_state= [i for i in range(len(state))  if state[i][0] == channel_id]
    if not filter_state:
        await ctx.send("No active game in this channel!")
        return

    i= filter_state[0]

    file = discord.File(str(ctx.channel.id)+".png")
    if state[i][1]=="queue":
        next_player=(await bot.fetch_user(state[i][4][0]))
        await ctx.send(file=file, content="{}'s turn! ⭐".format(next_player.name))
    else:
        await ctx.send(file=file)

@bot.command()
async def join(ctx):
    channel_id= ctx.channel.id
    user = ctx.author

    # lowest effort serialization
    with open("state.txt") as f: state = ast.literal_eval(f.read())

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

@bot.command()
async def queue(ctx):
    channel_id= ctx.channel.id

    # lowest effort serialization
    with open("state.txt") as f: state = ast.literal_eval(f.read())

    filter_state= [i for i in range(len(state))  if state[i][0] == channel_id]
    if not filter_state:
        await ctx.send("No active game in this channel!")
        return

    i= filter_state[0]

    if state[i][1] != "queue":
        await ctx.send("This game has no queue! Play whenever you want :P")
        return

    output= "Player list:\n"
    for j, player_id in enumerate(state[i][4]):
        player_name=(await bot.fetch_user(player_id)).name
        output+=str(j+1)+". "+ player_name+"\n"

    if state[i][4]==[]:
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

@bot.command()
async def newgame(ctx, arg):
    channel_id= ctx.channel.id
    user = ctx.author
    roles = map(lambda x : x.name, user.roles)

    if admin_role not in roles:
        await ctx.send("You don't have permissions for this!")
        return

    if arg not in ["queue", "random"]:
        await ctx.send("Unrecognized game type! Please try `$newgame <queue/random>")
        return

    # lowest effort serialization
    with open("state.txt") as f: state = ast.literal_eval(f.read())

    if ctx.channel.id in [ ch for (ch,_,_,_,_) in state]:
        await ctx.send("A game is already active in this channel!")
        return

    sgfengine.new_game(str(ctx.channel.id))
    state.append((ctx.channel.id, arg, [], [], []))

    file = discord.File(str(ctx.channel.id)+".png")
    if arg=="queue":
        await ctx.send(file=file, content="A new game has started! Join with `$join`")
    else:
        await ctx.send(file=file, content="A new game has started! Play with `$play <move>`")

    with open("state.txt", "w") as f: f.write(repr(state))

@bot.command()
async def resign(ctx, arg):
    channel_id= ctx.channel.id
    user = ctx.author
    roles = map(lambda x : x.name, user.roles)

    if admin_role not in roles:
        await ctx.send("You don't have permissions for this!")
        return

    if arg not in ["W","B"]:
        await ctx.send("Unrecognized colour! Please try `$resign <B/W>` to resign as Black/White")
        return

    with open("state.txt") as f: state = ast.literal_eval(f.read())

    now=datetime.now()
    file_name= "rengo_"+now.strftime("%Y_%m_%d_%H_%M_%S_")+ctx.channel.name+".sgf" #remove the hour minute and second later

    sgfengine.resign(str(channel_id), arg, file_name)

    file = discord.File(file_name)
    await ctx.send(file=file, content=("Black" if arg=="W" else "White")+" wins!")

    state = [s for s in state if s[0]!=channel_id]

    with open("state.txt", "w") as f: f.write(repr(state))

async def background_task():
    await bot.wait_until_ready()
    print("bot ready!")

    guild=discord.utils.get(bot.guilds, name="Awesome Baduk")

    while not bot.is_closed():
        try:
            # lowest effort serialization
            with open("state.txt") as f: state = ast.literal_eval(f.read())
            #print(state)

            #TODO find who has to move, skip players accordingly, notify if any has to move
            for i in range(len(state)):
                if state[i][3] == [] or state[i][1]!="queue": continue

                channel_id= state[i][0]
                channel= bot.get_channel(channel_id)

                last_time= datetime.strptime(state[i][3][-1],format)
                time_left= last_time + time_to_skip-datetime.now()
                if time_left < time_to_skip * 2/3 and time_left > time_to_skip*2/3-timedelta(seconds=10): # Probably remove? Depends on how passive aggressive it is
                    next_user = await bot.fetch_user(state[i][4][0])
                    await channel.send("{}'s turn! Time is running up!".format(next_user.mention))#, time_left.total_seconds()/3600) )
                if time_left < timedelta():
                    state[i][3][-1]= datetime.strftime(datetime.now(),format)
                    state[i][2][-1]= None
                    user_id= state[i][4][0]
                    state[i][4].pop(0)
                    state[i][4].append(user_id)
                    next_player=(await bot.fetch_user(state[i][4][0]))
                    await channel.send(content="{}'s turn! ⭐".format(next_player.mention))
                    #Should I output the board too?

            with open("state.txt", "w") as f: f.write(repr(state))
            await asyncio.sleep(10)

        except ConnectionResetError:
            print("Connection error")

bot.loop.create_task(background_task())
bot.run(token)
