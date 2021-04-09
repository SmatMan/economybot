from __future__ import unicode_literals # just for correct text processing bc python doesnt like unicode characters sometimes, like emojis or other characters like stars n shit

import ast
import re
import discord
from discord import User
import time
import random
import asyncio
from discord.ext import commands
from discord.ext.tasks import loop
from discord.ext.commands import Bot
import json
from collections import defaultdict
import os # you can use os.system("shell command") to run a shell command
import subprocess # for deploy
import mysql.connector # mysql stuff, reading off of https://www.w3schools.com/python/python_mysql_getstarted.asp 
from datetime import datetime
import yfinance as yf
from gtts import gTTS 
import parsedatetime as pdt
import math

### Local File Imports
import constants 
import cooldowns as cd
import commandconfigs as cfg
import filtered_words as fil

bot = commands.Bot(command_prefix=commands.when_mentioned_or(';'))
#bot = commands.Bot(command_prefix=';')
bot.remove_command("help")
language = "en"
token = "" ## TOKEN HERE
# gaming 
allowed_people = [""] ## put bot admin ids in here
allowed_tickers = ["AAPL", "MSFT", "TSCO", "PYPL", "TSLA", "FVRR"] 

punishEmojis = ["👢", "<:BanHammer:608760061749362705>", "1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "⏲", "🚫"]
muteEmojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "⏲"]
muteTimes = ["1800", "3600", "21600", "86400", "604800", "1814400"]

### DATABASE SETUP -------------------

db = mysql.connector.connect( ## sql db creds in here
  user="",
  host="",
  password="",
  database=""
)

db.autocommit = True

dbcursor = db.cursor(buffered=True)


### END DATABASE SETUP -------------------

### CONFIG SETUP ------------------

global_rob_chance = cfg.global_rob_chance
USER_MENTION_RE = re.compile('<@!?([0-9]+)>')
autocash_flag = 0

### NON-ASYNCIO FUNCTIONS -------------------
def safePing(args):
    if "@everyone" in args or "@here" in args:
        return False
    else:
        return True

def getTime(): # not really useful, i just wanted to make this a function bc its cleaner
    t = time.localtime()
    current_time = time.strftime("%H:%M:%S", t)
    return(current_time)

def pingDB(): # function not working properly yet, will add once db is setup
    if db.is_connected():
        return ("**Database Connected**")
    else:
        return("**No Connection**")

def checkIfValidUser(userid):
    sql = "select balance from balances where userid = " + str(userid)
    dbcursor.execute(sql)
    result = dbcursor.fetchall()
    if not result:
        return False
    else:
        return True

async def joinVC(ctx):
    if ctx.author.voice is None or ctx.author.voice.channel is None:
        await ctx.send("get in a fucking vc")
    else:
        voice_channel = ctx.author.voice.channel
        if ctx.voice_client is None:
            vc = await voice_channel.connect()
        else:
            await ctx.voice_client.move_to(voice_channel)
            vc = ctx.voice_client
    return vc

async def createUserIfNotExist(userid, ctx):
    if checkIfValidUser(userid):
        return 0
    else:
        sql = "INSERT INTO balances (userid, balance, bank) VALUES (" + str(userid) + ", 0, 0);"
        dbcursor.execute(sql)
        sql = "INSERT INTO autocash (userid, payout) VALUES (" + str(userid) + ", 0);"
        dbcursor.execute(sql)
        sql = "INSERT INTO stocks (userid, AAPL, MSFT, TSCO, PYPL, TSLA, FVRR) VALUES (" + str(userid) + ", 0, 0, 0, 0, 0, 0);"
        dbcursor.execute(sql)
        embed=discord.Embed(title="Hey! Welcome to the NOKCONOMY bot!", description="Since this is your first time using the bot, your profile has been created! Have fun!", color=0xee719e)
        await ctx.send(embed=embed)

def getBalance(userid):
    sql = "select balance from balances where userid = " + str(userid)
    dbcursor.execute(sql)
    result = dbcursor.fetchall()
    for row in result:
        return str(row[0])

def setBalance(userid, newValue):
    sql = "UPDATE balances SET balance = " + str(newValue) + " WHERE userid = " + str(userid)
    dbcursor.execute(sql)
    

def getBank(userid):
    sql = "select bank from balances where userid = " + str(userid)
    dbcursor.execute(sql)
    result = dbcursor.fetchall()
    for row in result:
        return str(row[0])

def setBank(userid, newValue):
    sql = "UPDATE balances SET bank = " + str(newValue) + " WHERE userid = " + str(userid)
    dbcursor.execute(sql)
    result = dbcursor.fetchall()
    for row in result:
        return str(row[0])
        
def getAutoCash(userid):
    sql = "select payout from autocash where userid = " + str(userid)
    dbcursor.execute(sql)
    result = dbcursor.fetchall()
    for row in result:
        return str(row[0])

def getUserStocks(userid, stock):
    sql = f"select {stock} from stocks where userid = {userid}"
    dbcursor.execute(sql)
    result = dbcursor.fetchall()
    for row in result:
        return(str(row[0]))

def getStockPrice(ticker):
    ticker_yahoo = yf.Ticker(ticker)
    data = ticker_yahoo.history()
    last_quote = (data.tail(1)['Close'].iloc[0])
    return round(int(last_quote) * 10)

@loop(seconds=int(cfg.autocashloop))
async def autocash_task():
    #if autocash_flag > 0:
    sql = "select userid from autocash"
    dbcursor.execute(sql)
    result = dbcursor.fetchall()
    print(result)
    for row in result:
        userid = str(row[0])

        sql = "select payout from autocash where userid = " + str(userid)
        dbcursor.execute(sql)
        result = dbcursor.fetchall()
        for row in result: 
            sql = "UPDATE balances SET balance = " + str(int(getBalance(userid)) + int(row[0])) + " WHERE userid = " + str(userid)
            dbcursor.execute(sql)

    print("done autocash on {}".format(str(time.time())))
    #else:
    #    autocash_flag = 1
    #    return

def searchMembers(ctx, search_term: str):
    members = ctx.guild.members
    search_results = []
    for member in members:
        if search_term in str(member):
            search_results.append(str(member))
    return search_results

async def searchAndPickMembers(ctx, search_term: str, embed_title: str):
    try:
        id = int(search_term)
        user = bot.get_user(id)
        return user
    except:
        pass       
    members = ctx.guild.members
    search_results = []
    for member in members:
        if search_term.upper() in str(member).upper():
            search_results.append(str(member))
    if search_results == []:
        await ctx.send("I couldn't find a user with that name!")
        return None
    else:
        embed = discord.Embed(title=embed_title, color=0xB447C2)
        embed.set_footer(text="Type `cancel` to cancel. Sadly if you enter something wrong you will have to wait until the cooldown runs out.")
        for index, result in enumerate(search_results):
            embed.add_field(name="{}.".format(index + 1), value=search_results[index], inline=False)
        await ctx.send(embed=embed)
        def check(message: discord.Message):
            return message.channel == ctx.channel and message.author != ctx.me and message.author == ctx.message.author
        option = await bot.wait_for('message', check=check)
        print(option.content)
        if str(option.content).lower() == "cancel":
            await ctx.send("Cancelled.")
            return None
        return search_results[int(option.content) - 1]
    
async def checkRegex(message, input: str):
    if bool(re.search(fil.filter_regex, input)):
        return f"Please don't swear, <@{message.author.id}>!"
    elif bool(re.search(fil.invite_regex, input)):
        return f"No one wants to join your server, <@{message.author.id}>."
    #elif bool(re.search(fil.website_regex, input)):
    #       return f"Put links in #media, <@{message.author.id}>!"
    else:
        return False

def show_time(time):
        time = int(time)
        day = time // (24 * 3600)
        time = time % (24 * 3600)
        hour = time // 3600
        time %= 3600
        minutes = time // 60
        time %= 60
        seconds = time
        if day != 0:
                return "%d days %d hours %d minutes %d seconds" % (day, hour, minutes, seconds)
        elif day == 0 and hour != 0:
                return "%d hours %d minutes %d seconds" % (hour, minutes, seconds)
        elif day == 0 and hour == 0 and minutes != 0:
                return "%d minutes %d seconds" % (minutes, seconds)
        else:
                return "%d seconds" % (seconds)

async def modlog(ctx, punishedUser: discord.Member, punishedReason: str, punishedTime=None, punishedModerator: discord.Member=None, punishedType: str=None):
    embed = discord.Embed(title=f"{punishedType} - {str(punishedUser)}", color=0xf542ce)
    embed.set_thumbnail(url=punishedUser.avatar_url)
    embed.add_field(name=f"User", value=f"{str(punishedUser)} ({punishedUser.mention})", inline=True)
    embed.add_field(name=f"Moderator:", value=f"{str(punishedModerator.mention)}", inline=True)
    if punishedType == "Mute":
        embed.add_field(name=f"Punishment:", value=f"{punishedType} for {punishedTime}", inline=False)
    else:
        embed.add_field(name=f"Punishment:", value=f"{punishedType}", inline=False)
    embed.add_field(name=f"Reason:", value=f"{str(punishedReason)}", inline=True)
    channel = bot.get_channel(779180405617852437)
    await channel.send(embed=embed)
    channel = bot.get_channel(728740576907886633)
    await channel.send(embed=embed)

### END NON-ASYNCIO FUNCTIONS -------------------

### DISCORD EVENTS -----------------------

@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="the prefix ';'"))
    #autocash_task.start()
    print("ready")
    channel = bot.get_channel(758396274067636244)
    embed = discord.Embed(title='Ready!', description=f"{constants.TICK_EMOJI} I'm ready for use! My ping is `{round(bot.latency * 1000)}ms`\nDatabase Status: {pingDB()}", color=discord.Colour.green())
    #embed = discord.Embed(title='Ready', description="{} I'm ready for use! My ping is `{}ms`, and the database status is: {}".format(constants.TICK_EMOJI, round(bot.latency * 1000), pingDB()))
    await channel.send(embed=embed)
    #await channel.send('Ready')
    #await channel.send("Database Status: **{}**".format(pingDB()))

@bot.event
async def on_message(message):
    staff_role = discord.utils.get(message.guild.roles, id=608304799447777281)
    vet_channel = discord.utils.get(message.guild.channels, id=696834168025514096)
    regexAnswer = await checkRegex(message, str(message.content))
    if staff_role in message.author.roles:
        await bot.process_commands(message)
    else:
        if not message.author.bot:
            if message.channel != vet_channel:
                if message.guild is not None: # check if the message isnt in dms
                    if not regexAnswer: # check if filter finds smth
                            if discord.utils.get(message.author.roles, name="Eco Banned") is None: # check if user isn't eco banned
                                #await bot.process_commands(message)
                                #if str(message.channel.id) in cfg.allowed_channels or str(message.author.id) in allowed_people: # check if command (not msg) is in allowed channels
                                await bot.process_commands(message)
                    else:
                        await message.delete()
                        channel = message.channel
                        embed = discord.Embed(title="Hey!", description=regexAnswer, color=0xFF0000)
                        await channel.send(embed=embed)
                        embed = discord.Embed(title=f"Swear Alert", description=f"<@{message.author.id}> said an oopsie", color=0xFF0000)
                        embed.add_field(name="Message:", value=f"{str(message.content)}", inline=True)
                        embed.add_field(name="Channel:", value=f"<#{message.channel.id}>", inline=True)
                        channel = bot.get_channel(778721363753566219)
                        await channel.send(embed=embed)

@bot.event
async def on_message_edit(message, newMessage):
    regexAnswer = await checkRegex(newMessage, str(newMessage.content))
    if not regexAnswer:
        return
    else:
        await newMessage.delete()
        channel = newMessage.channel
        embed = discord.Embed(title="Hey!", description=regexAnswer, color=0xFF0000)
        await channel.send(embed=embed)
        embed = discord.Embed(title=f"Swear Alert", description=f"<@{newMessage.author.id}> said an oopsie (edit)", color=0xFF0000)
        embed.add_field(name="Previous Message:", value=f"{str(message.content)}", inline=True)
        embed.add_field(name="Edited Message:", value=f"{str(newMessage.content)}", inline=True)
        embed.add_field(name="Channel:", value=f"<#{newMessage.channel.id}>", inline=True)
        channel = bot.get_channel(778721363753566219)
        await channel.send(embed=embed)

### END DISCORD EVENTS ----------------------

@bot.event
async def on_command_error(message, error):
    if isinstance(error, commands.CommandOnCooldown):
        channel = message.channel
        embed = discord.Embed(title="Cooldown", description="**Hey {}!** Slow down! You can run this command in **{} seconds**!".format(message.author, round(error.retry_after)), color=0xFF0000)
        await channel.send(embed=embed)
    elif isinstance(error, commands.errors.MissingRequiredArgument) or isinstance(error, commands.errors.BadArgument):
        channel = message.channel
        embed = discord.Embed(title="Missing/Invalid Argument", description="Hey {}! You entered an argument wrong in your command, check your command and try running it again!".format(message.author), color=0xFF0000)
        await channel.send(embed=embed)
    else:
        raise error

@bot.command()
async def borisbus(ctx):
    await ctx.send("BORIS BUS")
    await ctx.send("https://cdn.discordapp.com/attachments/757701308395552803/757943027883966504/unknown-1.png")
    await ctx.send("BORIS BUS")

@bot.command()
async def status(ctx): # just a testing command
    statusEmbed = discord.Embed(title="Status", description="GAMING", color=0xB447C2)
    statusEmbed.add_field(name="Time:", value=getTime(), inline=True)
    statusEmbed.add_field(name="Database Ping Time", value=pingDB(), inline=True)
    await ctx.send(embed=statusEmbed)

@bot.command(aliases=['pull','git','restart'])
async def deploy(ctx): # pull from git
    if str(ctx.message.author.id) in allowed_people:
        print("pulling from git")
        await ctx.send("pulling from git...")
        process = subprocess.run(['git', 'pull'], stdout=subprocess.PIPE)
        await ctx.send(r'' + str(process.stdout))
        await ctx.send("logging out")
        await bot.logout()
        os.system("python3 gamingecobotngl.py")
    else:
        await ctx.send("no go away u dont have perms lol xd cringe")

@bot.command()
async def sql(ctx, *queryargs):
    if str(ctx.message.author.id) in allowed_people:
        query = ' '.join(queryargs)
        dbcursor.execute(str(query))
        try:
            result = dbcursor.fetchall()
            for row in result:
                await ctx.send("```" + str(row).strip("()") + "```")
        except mysql.connector.errors.InterfaceError:
            pass
        
    else:
        await ctx.send("no")

@bot.command(cooldown_after_parsing=True)
@commands.cooldown(1, cd.work, commands.BucketType.user)
async def work(ctx):
    await createUserIfNotExist(ctx.message.author.id, ctx)
    workamount = random.randint(cfg.work_min,cfg.work_max) # generate the amount of money to give
    currentbalance = getBalance(ctx.message.author.id) # grab the current users balance
    newbalance = workamount + int(currentbalance) # calculate the new balance

    sql = "UPDATE balances SET balance = " + str(newbalance) + " WHERE userid = " + str(ctx.message.author.id)
    dbcursor.execute(sql)

    balanceEmbed = discord.Embed(title="Work", description="You earned **$" + str(workamount) + "**!", color=0xB447C2)
    balanceEmbed.set_footer(text=f"Your networth is now ${str(int(newbalance) + int(getBank(ctx.message.author.id)))}.")
    await ctx.send(embed=balanceEmbed)


@bot.command(aliases=["bal", "money", "cash", "bank"])
async def balance(ctx, member=None):
    await createUserIfNotExist(ctx.message.author.id, ctx)
    if member == None:
        member = ctx.message.author
    else:
        member = ctx.guild.get_member_named(await searchAndPickMembers(ctx, str(member), "Who's balance would you like to see?"))
        print(member)
        print(member.id)
        print(type(member))
        if member == None:
            member = ctx.message.author
    try:
        bal = getBalance(str(member.id))
        bank = getBank(str(member.id))
        embed=discord.Embed(title=str(member) + "'s Money", color=0xee719e)
        embed.add_field(name="Wallet:", value="$" + bal, inline=False)
        embed.add_field(name="Bank:", value="$" + bank, inline=False)
        embed.add_field(name="Net Worth:", value="$" + str(int(bal) + int(bank)), inline=False)
        await ctx.send(embed=embed)
    except TypeError:
        await ctx.send("This member has not joined the Economy yet! Tell them to run a command first.")

@bot.command(aliases=["set-money"])
async def setMoney(ctx, target: discord.User, money, *reason):
    reason = ' '.join(reason)
    if reason == '': 
        reason = 'No Reason Provided'
    if target == None:
        target = ctx.message.author
    if str(ctx.message.author.id) in allowed_people:
        sql = "UPDATE balances SET balance = " + str(money) + " WHERE userid = " + str(target.id)
        dbcursor.execute(sql)
        await ctx.send(":white_check_mark: Successfully set {}'s balance to {}. REASON: `{}`".format(str(target), str(money), reason))

@bot.command(aliases=["set-bank"])
async def setBank(ctx, target: discord.User, money, *reason):
    reason = ' '.join(reason)
    if reason == '': 
        reason = 'No Reason Provided'
    if target == None:
        target = ctx.message.author
    if str(ctx.message.author.id) in allowed_people:
        sql = "UPDATE balances SET bank = " + str(money) + " WHERE userid = " + str(target.id)
        dbcursor.execute(sql)
        await ctx.send(":white_check_mark: Successfully set {}'s `bank` amount to {}. REASON: `{}`".format(str(target), str(money), reason))

@bot.command()
async def ecoban(ctx, user: discord.Member):
    if str(ctx.message.author.id) in allowed_people:
        if user is not None:
            role = discord.utils.get(ctx.guild.roles,name="Eco Banned")
            await user.add_roles(role)
            embed = discord.Embed(title="Succesfully Eco Banned {}".format(str(user)), description="F", color=0x349D9D)
            embed.set_image(url="https://cdn.bren.rocks/i/fwW8M.gif")
            await ctx.send(embed=embed)

@bot.command(aliases=["dep"])
async def deposit(ctx, amount):
    currentBalance = getBalance(ctx.message.author.id)
    currentBank = getBank(ctx.message.author.id)
    if amount == "all" or amount == "ALL":
        amount = currentBalance
    if int(currentBalance) >= int(amount) and int(amount) != 0 and int(amount) > 0:    
        sql = "UPDATE balances SET balance = " + str(int(currentBalance) - int(amount)) + " WHERE userid = " + str(ctx.message.author.id)
        dbcursor.execute(sql)
        sql2 = "UPDATE balances SET bank = " + str(int(currentBank) + int(amount)) + " WHERE userid = " + str(ctx.message.author.id)
        dbcursor.execute(sql2)
        embed = discord.Embed(title="Deposit", description="**$" + str(amount) + " has been deposited successfully into your bank!**", color=0xB447C2)
        embed.set_footer(text=f"Your bank balance is now ${getBank(ctx.message.author.id)}.")

        await ctx.send(embed=embed)
    else:
        embed = discord.Embed(title="Deposit Unsuccessful", description="You either don't have the money to deposit, are broke, or have entered a wrong number. Try again!", color=0xB447C2)
        await ctx.send(embed=embed)

@bot.command(aliases=["with"])
async def withdraw(ctx, amount):
    currentBalance = getBalance(ctx.message.author.id)
    currentBank = getBank(ctx.message.author.id)
    if amount == "all" or amount == "ALL":
        amount = currentBank
    if int(currentBank) >= int(amount) and int(amount) > 0 and int(amount) > 0:
        sql = "UPDATE balances SET balance = " + str(int(currentBalance) + int(amount)) + " WHERE userid = " + str(ctx.message.author.id)
        dbcursor.execute(sql)
        sql2 = "UPDATE balances SET bank = " + str(int(currentBank) - int(amount)) + " WHERE userid = " + str(ctx.message.author.id)
        dbcursor.execute(sql2)
        embed = discord.Embed(title="Withdraw", description="**$" + str(amount) + " has been withdrawed successfully into your wallet!**", color=0xB447C2)
        embed.set_footer(text=f"Your bank balance is now ${getBank(ctx.message.author.id)}.")
        await ctx.send(embed=embed)
    else:
        embed = discord.Embed(title="Withdraw Unsuccessful", description="You either don't have the money to withdraw, are broke, or have entered a wrong number. Try again!", color=0xB447C2)
        await ctx.send(embed=embed)

@bot.command(cooldown_after_parsing=True, aliases=["send"])
@commands.cooldown(1, cd.give, commands.BucketType.user)
async def give(ctx, user, amount: int):
    user = ctx.guild.get_member_named(await searchAndPickMembers(ctx, str(user), "Who would you like to give money to?"))

    if user == None:
        return
    
    try:
        userBalance = getBalance(ctx.message.author.id)
        targetBalance = getBalance(user.id)
        if amount == "all" or amount == "ALL":
            amount = userBalance
        if int(userBalance) >= int(amount) and int(amount) != 0 and int(amount) > 0 and user != ctx.message.author:
            sql = "UPDATE balances SET balance = " + str(int(userBalance) - int(amount)) + " WHERE userid = " + str(ctx.message.author.id)
            dbcursor.execute(sql)
            sql2 = "UPDATE balances SET balance = " + str(int(targetBalance) + int(amount)) + " WHERE userid = " + str(user.id)
            dbcursor.execute(sql2)
            embed = discord.Embed(title="Sent", description="**$" + str(amount) + " has been sent successfully to <@" + str(user.id) + ">**", color=0xB447C2)
            await ctx.send(embed=embed)
            embed2 = discord.Embed(title="Payment Alert", description=f"{str(ctx.author)} (`{str(ctx.author.id)}`) has sent **{str(amount)}** to <@{str(user.id)}> (`{str(user.id)}`)", color=0xB447C2)
            ecoLogs = bot.get_channel('780201398214197248')
            await ecoLogs.send(embed=embed2)
        else:
            embed = discord.Embed(title="Money Sending Unsuccessful", description="You either don't have the money to send, are broke, specified yourself as the recipient, or have entered a wrong number. Try again!", color=0xB447C2)
            await ctx.send(embed=embed)
    except TypeError:
        await ctx.send("This user does not exist!")

@bot.command(cooldown_after_parsing=True, aliases=["lb"])
@commands.cooldown(1, cd.lb, commands.BucketType.user)
async def leaderboard(ctx, option="net"):
    if str(option) == "net": 
        sql = "SELECT userid, GREATEST( balance, bank ) AS net_worth FROM balances ORDER BY net_worth DESC LIMIT 10"
        dbcursor.execute(sql)
        result = dbcursor.fetchall()
        lbEmbed = discord.Embed(title="Leaderboard", description="Top 10 Users by **Net Worth**", color=0xB447C2)
        for index, row in enumerate(result, start=1):
            user = await bot.fetch_user(row[0])
            lbEmbed.add_field(name=str(index) + ". " + str(user), value="$" + str(row[1]), inline=False)
        await ctx.send(embed=lbEmbed)
    elif str(option) == "-cash" or str(option) == "cash" or str(option) == "balance":
        sql = "SELECT userid, balance FROM balances ORDER BY balance DESC LIMIT 10"
        dbcursor.execute(sql)
        result = dbcursor.fetchall()
        lbEmbed = discord.Embed(title="Leaderboard", description="Top 10 Users by **Cash Balance**", color=0xB447C2)
        for index, row in enumerate(result, start=1):
            user = await bot.fetch_user(row[0])
            lbEmbed.add_field(name=str(index) + ". " + str(user), value="$" + str(row[1]), inline=False)
        await ctx.send(embed=lbEmbed)
    

@bot.command(cooldown_after_parsing=True)
@commands.cooldown(1, cd.rob, commands.BucketType.user)
async def rob(ctx, target):
    target = ctx.guild.get_member_named(await searchAndPickMembers(ctx, str(target), "Who would you like to rob?"))
    if target == None:
        return
    try:
        rob_chance = random.randint(1, 100)
        userBalance = getBalance(ctx.message.author.id)
        targetBalance = getBalance(target.id)
        rob_amount_percentage = random.randint(1,100)
        rob_amount = (float(targetBalance) * float(rob_amount_percentage/100))

        if int(rob_chance) <= int(global_rob_chance) and int(targetBalance) > 0 and target != ctx.message.author:
            sql = "UPDATE balances SET balance = " + str(int(targetBalance) - int(rob_amount)) + " WHERE userid = " + str(target.id)
            dbcursor.execute(sql)
            sql2 = "UPDATE balances SET balance = " + str(int(userBalance) + int(rob_amount)) + " WHERE userid = " + str(ctx.message.author.id)
            dbcursor.execute(sql2)
            embed = discord.Embed(title="Rob Successful!", description="You have succesfully robbed **$" + str(rob_amount) + "** from <@" + str(target.id) + ">!", color=0xB447C2)
            await ctx.send(embed=embed)
            embed2 = discord.Embed(title="Rob Alert", description=f"**Command Used:** {ctx.message}", color=0xB447C2)
            logChannel = bot.get_channel("780201398214197248")
            await logChannel.send(embed2)

        elif target == ctx.message.author:
            print("target == message author")
            embed = discord.Embed(title="Rob", description="You snuck up on someone, tried to steal their wallet, and realized you were just looking in the mirror!", color=0xFF0000)
            await ctx.send(embed=embed)
        elif int(targetBalance) <= 0:
            print("target balance is 0")
            embed = discord.Embed(title="Rob", description="Not sure what you're trying to do, the person you're trying to rob is broke!", color=0xFF0000)
            await ctx.send(embed=embed)
        elif int(rob_chance) > int(global_rob_chance):
            fine = random.randint(0, cfg.crime_fine)
            print("rob chance failed L")
            sql = "UPDATE balances SET balance = " + str(int(userBalance) - int(fine)) + " WHERE userid = " + str(ctx.message.author.id)
            dbcursor.execute(sql)
            embed = discord.Embed(title="Rob", description="You tried to rob " + str(target) + ", but they pulled out a weapon before you could take their wallet. You got reverse mugged and lost $" + str(fine) + "!", color=0xFF0000)
            await ctx.send(embed=embed)
    except TypeError:
        embed = discord.Embed(title="Rob", description="You tried to rob someone, but it turns out they don't even exist!", color=0xFF0000)
        await ctx.send(embed=embed)

@bot.command(cooldown_after_parsing=True)
@commands.cooldown(1, cd.rob, commands.BucketType.user)
async def crime(ctx):
    await createUserIfNotExist(ctx.message.author.id, ctx)
    crimeChance = random.randint(1, 100)
    currentbalance = int(getBalance(ctx.message.author.id))
    crimeAmount = random.randint(cfg.crime_min, cfg.crime_max)

    if crimeChance <= global_rob_chance:
        sql = "UPDATE balances SET balance = " + str(currentbalance + crimeAmount) + " WHERE userid = " + str(ctx.message.author.id)
        dbcursor.execute(sql)
        embed = discord.Embed(title="Crime Successful!", description="You have succesfully stolen **$" + str(crimeAmount) + "**!", color=0xB447C2)
        await ctx.send(embed=embed)
    else:
        fine = random.randint(0, cfg.crime_fine)
        sql = "UPDATE balances SET balance = " + str(currentbalance - fine) + " WHERE userid = " + str(ctx.message.author.id)
        dbcursor.execute(sql)
        embed = discord.Embed(title="Crime Failed!", description="You tried stealing money from the local Charity for Children, but you were caught and lost ${}.".format(str(fine)), color=0xFF0000)
        await ctx.send(embed=embed)



### Rock Paper Scissors

@bot.command(cooldown_after_parsing=True)
@commands.cooldown(1, cd.rps, commands.BucketType.user)
async def rps(ctx, option: str, bet=0):
    options = ["rock", "paper", "scissors"];
    result = random.choice(options)
    userPicked = option.lower()
    currentBalance = getBalance(ctx.message.author.id)
    if bet != 0:
        if int(bet) <= int(currentBalance):
            bet = int(bet)
            sql = "UPDATE balances SET balance = " + str(int(currentBalance) - int(bet)) + " WHERE userid = " + str(ctx.message.author.id)
            dbcursor.execute(sql)
            currentBalance = getBalance(ctx.message.author.id)
        else:
            await ctx.send("Invalid Bet Amount!")
            bet = 0
        
    if userPicked == 'rock' and result == 'scissors':
        embed = discord.Embed(title = "Rock Paper Scissors", description = 'You picked {} and I Picked {}. You Win!'.format(constants.ROCK_EMOJI, constants.SCISSORS_EMOJI), color=0xFF0000)
        embed.set_footer(text="Optional Bet: {} | Won Amount: {}".format(int(bet), int(bet*2)))
        await ctx.send(embed=embed)
        #await ctx.send('You picked `rock` and I picked `scissors`. You win!')
        sql = "UPDATE balances SET balance = " + str(int(currentBalance) + int(bet)*2) + " WHERE userid = " + str(ctx.message.author.id)
        dbcursor.execute(sql)
    elif userPicked == 'rock' and result == 'paper':
        embed = discord.Embed(title = "Rock Paper Scissors", description = 'You picked {} and I Picked {}. I Win!'.format(constants.ROCK_EMOJI, constants.PAPER_EMOJI), color=0xFF0000)
        embed.set_footer(text="Optional Bet: {} | Won Amount: {}".format(int(bet), '0'))                
        await ctx.send(embed=embed)
        #await ctx.send('You picked `rock` and I picked `paper`. I win!') 
    elif userPicked == 'rock' and result == 'rock':
        embed = discord.Embed(title = "Rock Paper Scissors", description = "You picked {} and I Picked {}. It's a draw!".format(constants.ROCK_EMOJI, constants.ROCK_EMOJI), color=0xFF0000)
        embed.set_footer(text="Optional Bet: {} | Won Amount: {}".format(int(bet), int(bet)))
        await ctx.send(embed=embed)
        #await ctx.send("You picked `rock` and I picked `rock`. It's a draw!")
        sql = "UPDATE balances SET balance = " + str(int(currentBalance) + int(bet)) + " WHERE userid = " + str(ctx.message.author.id)
        dbcursor.execute(sql)
        
    elif userPicked == 'scissors' and result == 'paper':
        embed = discord.Embed(title = "Rock Paper Scissors", description = 'You picked {} and I Picked {}. You Win!'.format(constants.SCISSORS_EMOJI, constants.PAPER_EMOJI), color=0xFF0000)
        embed.set_footer(text="Optional Bet: {} | Won Amount: {}".format(int(bet), int(bet*2)))
        await ctx.send(embed=embed)
        #await ctx.send('You picked `scissors` and I picked `paper`. You win!')
        sql = "UPDATE balances SET balance = " + str(int(currentBalance) + int(bet)*2) + " WHERE userid = " + str(ctx.message.author.id)
        dbcursor.execute(sql)
    elif userPicked == 'scissors' and result == 'rock':
        embed = discord.Embed(title = "Rock Paper Scissors", description = 'You picked {} and I Picked {}. I Win!'.format(constants.SCISSORS_EMOJI, constants.ROCK_EMOJI), color=0xFF0000)
        embed.set_footer(text="Optional Bet: {} | Won Amount: {}".format(int(bet), '0'))
        await ctx.send(embed=embed)
        #await ctx.send('You picked `scissors` and I picked `rock`. I win!')
    elif userPicked == 'scissors' and result == 'scissors': 
        embed = discord.Embed(title = "Rock Paper Scissors", description = "You picked {} and I Picked {}. It's a draw!".format(constants.SCISSORS_EMOJI, constants.SCISSORS_EMOJI), color=0xFF0000)
        embed.set_footer(text="Optional Bet: {} | Won Amount: {}".format(int(bet), int(bet)))
        await ctx.send(embed=embed)
        #await ctx.send("You picked `scissors` and I picked `scissors`. It's a draw!")
        sql = "UPDATE balances SET balance = " + str(int(currentBalance) + int(bet)) + " WHERE userid = " + str(ctx.message.author.id)
        dbcursor.execute(sql)
        
    elif userPicked == 'paper' and result == 'rock':
        embed = discord.Embed(title = "Rock Paper Scissors", description = 'You picked {} and I Picked {}. You Win!'.format(constants.PAPER_EMOJI, constants.ROCK_EMOJI), color=0xFF0000)
        embed.set_footer(text="Optional Bet: {} | Won Amount: {}".format(int(bet), int(bet*2)))
        await ctx.send(embed=embed)
        #await ctx.send('You picked `paper` and I picked `rock`. You win!')
        sql = "UPDATE balances SET balance = " + str(int(currentBalance) + int(bet)*2) + " WHERE userid = " + str(ctx.message.author.id)
        dbcursor.execute(sql)
    elif userPicked == 'paper' and result == 'scissors':
        embed = discord.Embed(title = "Rock Paper Scissors", description = 'You picked {} and I Picked {}. I Win!'.format(constants.PAPER_EMOJI, constants.SCISSORS_EMOJI), color=0xFF0000)
        embed.set_footer(text="Optional Bet: {} | Won Amount: {}".format(int(bet), '0'))
        await ctx.send(embed=embed)
        #await ctx.send('You picked `paper` and I picked `scissors`. I win!')
    elif userPicked == 'paper' and result == 'paper':
        embed = discord.Embed(title = "Rock Paper Scissors", description = "You picked {} and I Picked {}. It's a draw!".format(constants.PAPER_EMOJI, constants.PAPER_EMOJI), color=0xFF0000)
        embed.set_footer(text="Optional Bet: {} | Won Amount: {}".format(int(bet), int(bet)))
        await ctx.send(embed=embed)
        #await ctx.send("You picked `paper` and I picked `paper`. It's a draw!")
        sql = "UPDATE balances SET balance = " + str(int(currentBalance) + int(bet)) + " WHERE userid = " + str(ctx.message.author.id)
        dbcursor.execute(sql)

    else:
        embed = discord.Embed(title = "Command Error", description='Oops! You entered the incorrect usage. `;rps <str:rock|paper|scissors>`', color=0xFF0000)
        await ctx.send(embed=embed)
        





### Trivia


'''
@bot.command()
async def addquestion(ctx, id,*questionToInput):
    id = random.randint(1, 100)
    sql = 'INSERT INTO triva (id, question) VALUES ({}, "{}");'.format(id, questionToInput)
    dbcursor.execute(sql)
    await ctx.send(":white_check_mark: Successfully added question `{}` with the ID of `{}`".format(questionToInput, id))

@bot.command()
async def trivia(ctx, id):
    query = "SELECT question FROM trivia WHERE id = " + id +" LIMIT 1;"
    questions = dbcursor.execute(query)
    dataToSend = questions
    embed = discord.Embed(title="Trivia", description="Question: `{}`".format(str(dataToSend)), color=0xB447C2)
    await ctx.send(embed=embed)
 '''

### Reset Balance (Eco)






@bot.command()
async def reset(ctx, target: discord.User, option: str, *reason):
    if str(ctx.message.author.id) in allowed_people:
        reason = ' '.join(reason)
        if reason == '': 
            reason = 'No Reason Provided'
        if option == 'all':
            query = "DELETE FROM balances WHERE userid = " + str(target.id) + ";"
            dbcursor.execute(query)
            query = "DELETE FROM autocash WHERE userid = " + str(target.id) + ";"
            dbcursor.execute(query)
            embed = discord.Embed(title="Success!", description="{} Successfully reset {}'s progress in the economy. REASON: `{}`".format(constants.TICK_EMOJI, str(target), reason))
            # await ctx.send(constants.TICK_EMOJI + " Successfully reset {}'s progress in the economy. REASON: `{}`".format(str(target), reason))
            await ctx.send(embed=embed)
            await target.send("Hello! Your progress in the NOKWOK Economy has been reset. The reason for this given by staff is `{}`. Please speak to a member of staff if you have an issue with this.".format(reason))
        elif option == 'bank': 
            query = "UPDATE balances SET bank = 0 WHERE userid = " + str(target.id) + ";"
            dbcursor.execute(query)
            embed = discord.Embed(title="Success!", description="{} Successfully reset {}'s bank balance in the economy. REASON: `{}`".format(constants.TICK_EMOJI, str(target), reason))
            # await ctx.send(constants.TICK_EMOJI + " Successfully reset {}'s bank balance in the economy. REASON: `{}`".format(str(target), reason))
            await ctx.send(embed=embed)
            await target.send("Hello! Your **bank** balance in the NOKWOK Economy has been reset. The reason for this given by staff is `{}`. Please speak to a member of staff if you have an issue with this.".format(reason))
        elif option == 'bal' or option == 'balance':
            query = "UPDATE balances SET balance = 0 WHERE userid = " + str(target.id) + ";"
            dbcursor.execute(query)
            embed = discord.Embed(title="Success!", description="{} Successfully reset {}'s wallet balance in the economy. REASON: `{}`".format(constants.TICK_EMOJI, str(target), reason))
            # await ctx.send(constants.TICK_EMOJI + " Successfully reset {}'s **wallet balance** in the economy. REASON: `{}`".format(str(target), reason))
            await ctx.send(embed=embed)
            await target.send("Hello! Your **wallet** balance in the NOKWOK Economy has been reset. The reason for this given by staff is `{}`. Please speak to a member of staff if you have an issue with this.".format(reason))
        else:
            await ctx.send(constants.CROSS_EMOJI + " Sorry! That isn't a valid option. Try using ;reset (User) (all|bank|balance) (reason).")
    else:
        embed = discord.Embed(title="Permission Error", description="{} Sorry! You don't have permission to use this.".format(constants.CROSS_EMOJI), color=0xFF0000)
        await ctx.send(embed=embed)


# Search


@bot.command()
async def search(ctx, q):
    if ctx.message.author.id in allowed_people:
        for member in ctx.guild.members:
            if str(q) in str(member):
                await ctx.send("```{} ({})".format(str(member), member.id))
            else:
                await ctx.send("I could not find any users matching this query.")
  
  
  # BROKEN
@bot.command()
async def search_test(ctx, query):
        
        queries = []

        if query.isdigit():
            queries.append((User.id == query))

        q = USER_MENTION_RE.findall(query)
        if len(q) and q[0].isdigit():
            queries.append((User.id == q[0]))
        else:
            queries.append((User.name ** '%{}%'.format(query.replace('%', ''))))

        if '#' in query:
            username, discrim = query.rsplit('#', 1)
            if discrim.isdigit():
                queries.append((
                    (User.name == username) &
                    (User.discriminator == int(discrim))))

        users = discord.utils.find(lambda m: m.name == username, ctx.guild.members)
        if len(users) == 0:
            await ctx.send('No users found for query `{}`'.format(S(query)))

        
        await ctx.send('Found the following users for your query: ```{}```'.format(
            '\n'.join(['{} ({})'.format(str(i), i.id) for i in users[:25]])
        ))
        
        
        # DEVELOPMENT


# Ping
@bot.command(aliases=["latency"])
async def ping(ctx):
    embed = discord.Embed(title="Pong!", description="My latency is `{}ms`.\nDatabase Status: {}".format(round(bot.latency * 1000), pingDB()), color=discord.Colour.green())
    await ctx.send(embed=embed)


        
def insert_returns(body):
    # insert return stmt if the last expression is a expression statement
  if isinstance(body[-1], ast.Expr):
    body[-1] = ast.Return(body[-1].value)
    ast.fix_missing_locations(body[-1])

    # for if statements, we insert returns into the body and the orelse
  if isinstance(body[-1], ast.If):
    insert_returns(body[-1].body)
    insert_returns(body[-1].orelse)

    # for with blocks, again we insert returns into the body
  if isinstance(body[-1], ast.With):
    insert_returns(body[-1].body)
        
        
@bot.command(aliases=["eval"])
async def _eval(ctx, *, cmd):
    if str(ctx.message.author.id) in allowed_people:
        fn_name = "_eval_expr"

        cmd = cmd.strip("` ")

    # add a layer of indentation
        cmd = "\n".join(f"    {i}" for i in cmd.splitlines())

    # wrap in async def body
        body = f"async def {fn_name}():\n{cmd}"

        parsed = ast.parse(body)
        body = parsed.body[0].body

        insert_returns(body)

        env = {
            'bot': ctx.bot,
            'message': ctx.message,
            'author': ctx.message.author,
            'guild': ctx.message.guild,
            'discord': discord,
            'commands': bot.commands,
            'constants': constants,
            'db': db,
            'dbcursor': dbcursor,
            'ctx': ctx,
            '__import__': __import__,
            'os': os,
            'time': time,
            'yf': yf,
            'pdt': pdt
        }
        try:
            exec(compile(parsed, filename="<ast>", mode="exec"), env)
            result = (await eval(f"{fn_name}()", env))
        except Exception as e:
            await ctx.send("```py\n{}```".format(str(e)))
        await ctx.send('```py\n{}```'.format(result))
    else:
        await ctx.send("You don't have permission to run this!")

@bot.command(aliases=["ac"])
async def autocash(ctx, member: discord.User=None):
    await createUserIfNotExist(ctx.message.author.id, ctx)
    if member == None:
        member = ctx.message.author
    else:
        member = member
    embed=discord.Embed(title=str(member.name) + "'s Payout is ***__${}__***".format(getAutoCash(member.id)), color=0xee719e)
    embed.set_footer(text="Next AutoCash Payout in: {} seconds. Run ;buy to buy AutoCash Upgrades.".format(str(round(datetime.timestamp(autocash_task.next_iteration) - time.time(), 2))))
    await ctx.send(embed=embed)
'''
@bot.command()
async def autocash_test(ctx):
    sql = "select userid from autocash"
    dbcursor.execute(sql)
    result = dbcursor.fetchall()
    print(result)
    for row in result:
        userid = str(row[0])

        sql = "select payout from autocash where userid = " + str(userid)
        dbcursor.execute(sql)
        result = dbcursor.fetchall()
        for row in result: 
            sql = "UPDATE balances SET balance = " + str(int(getBalance(userid)) + int(row[0])) + " WHERE userid = " + str(userid)
            dbcursor.execute(sql)
'''

@bot.command(aliases=["buy"])
async def shop(ctx, item="None", amount=1):
    autocash_aliases = ["ac", "autocash", "acash", "autoc", "auto", "rolemoney"]
    if str(item).lower() in autocash_aliases:
        await createUserIfNotExist(ctx.message.author.id, ctx)

        userid = ctx.message.author.id
        autocash_amount = int(getAutoCash(userid))

        if autocash_amount >= 0 and autocash_amount <= 1000:
            autocash_price = 1000
            autocash_multiplyer = 100
        elif autocash_amount >= 1000 and autocash_amount <= 5000:
            autocash_price = 1500
            autocash_multiplyer = 150
        elif autocash_amount >= 5000 and autocash_amount <= 10000:
            autocash_price = 2000
            autocash_multiplyer = 200
        elif autocash_amount > 10000:
            autocash_price = 3000
            autocash_multiplyer = 350
        
        og_ac_price = autocash_price
        autocash_price = autocash_price * amount
        autocash_multiplyer = autocash_multiplyer * amount

        if int(getBalance(userid)) >= autocash_price:
            calculatingMessage = await ctx.send("Calculating your AutoCash Purchase...")
            embed=discord.Embed(title="Your AutoCash Purchase Invoice", color=0xee719e)
            embed.add_field(name="You will pay:", value="$" + str(autocash_price), inline=False)
            embed.add_field(name="You will get:", value="${} more AutoCash Dollars, resulting in a total of ${} AutoCash Dollars".format(str(autocash_multiplyer), autocash_multiplyer + autocash_amount), inline=False)
            await calculatingMessage.edit(message="␤")
            await calculatingMessage.edit(embed=embed)
            await ctx.send("**If you would like to purchase this, you may type `Yes` to buy. Otherwise type `No` or `Cancel` to cancel this purchase.**")
            
            def check(message):
                return message.content == ""
            try:
                def check(message: discord.Message):
                    return message.channel == ctx.channel and message.author != ctx.me and message.author == ctx.message.author
                purchaseChoice = await bot.wait_for('message', check=check)
                if str(purchaseChoice.content).lower() == "yes":
                    setBalance(userid, int(getBalance(userid)) - autocash_price)
                    print(autocash_price)
                    print(autocash_multiplyer + autocash_amount)
                    sql = "UPDATE autocash SET payout = {} WHERE userid = {}".format(autocash_multiplyer + autocash_amount, userid)
                    dbcursor.execute(sql)
                    await ctx.send("Purchased!")
                else:
                    await ctx.send("Cancelled!")
            except asyncio.TimeoutError:
                await ctx.send("Order Cancelled")
        else:
            embed = discord.Embed(title="Purchase Unsuccessful", description="You do not have the money to buy this! Either withdraw some money, or get some more! You need ${} more money.".format(str(autocash_price - int(getBalance(userid)))), color=0xFF0000)
            await ctx.send(embed=embed)
    else:
        embed = discord.Embed(title="Make sure you specify an item to buy!", description="Example: `;buy autocash 10`. Don't worry! This won't buy AutoCash instantly, it will tell you how much you will pay and how much you will get.", color=0xB492FF)
        await ctx.send(embed=embed)
    
@bot.command()
async def powerup(ctx, option=None):
    if option == None:
        embed = discord.Embed(title="Powerups Menu", description="Purchasable Powerups:\nDouble Work Income for **1 Hour** -- (`Price TBD`)\nDecreased Work Cooldown for **1 Hour** -- (`Price TBD`)", color=0xB492FF)
        await ctx.send(embed=embed)
    else:  
        if option == "double" or option == "doublework" or "doubleworkincome":
            await ctx.send("{} Successfully purchased double work income for 1 hour.".format(constants.TICK_EMOJI))
            # run sql stuff
        else:
            await ctx.send("Sorry! That is not a valid option. Please try ;powerup to see the available options")
    
@bot.command()
async def stocks(ctx, ticker=None):
    if ticker != None:
        ticker = ticker.upper()
    if str(ticker) in allowed_tickers and ticker != None:
        last_quote = getStockPrice(ticker)
        embed=discord.Embed(title=f"{ticker} is currently ${last_quote}.", description=f"You own {getUserStocks(ctx.message.author.id, ticker)} shares.", color=0xee719e)
        await ctx.send(embed=embed)
    elif ticker == None:
        embed=discord.Embed(title="Stocks that you can buy", color=0xee719e)
        for ticker in allowed_tickers:
            embed.add_field(name=f"{ticker}", value=f"Run `;stocks {ticker}` to see more about this stock, and run `;buystock {ticker}` to buy some stocks!", inline=False)
        await ctx.send(embed=embed)

@bot.command(aliases=["buystock", "buy-stock"])
async def buyStock(ctx, ticker=None, shares: int=1):
    if ticker != None:
        ticker = ticker.upper()
        if str(ticker) in allowed_tickers and ticker != None:
            currentBalance = int(getBalance(ctx.message.author.id))
            priceofeach = int(getStockPrice(ticker))
            price = int(priceofeach * 10)
            currentShares = int(getUserStocks(ctx.message.author.id, ticker))
            if currentBalance >= price:
                setBalance(ctx.message.author.id, currentBalance - price)
                sql = f"update stocks set {ticker} = {currentShares + shares} where userid = {ctx.message.author.id}"
                dbcursor.execute(sql)
                embed=discord.Embed(title=f"Successfully purchased {shares} {ticker} shares at ${priceofeach} each.", description="Make sure to keep that number in mind so you know when to sell!", color=0xee719e)
                await ctx.send(embed=embed)
            else:
                await ctx.send(f"Kinda broke ngl. Check stock prices with ;stocks {ticker}.")
        else:
            await ctx.send("That isn't a stock!")
    else:
        await ctx.send(f"If you would like to view a list of availible stocks, you can run `;stocks`!")

@bot.command(aliases=["sellstock", "sell-stock"])
async def sellStock(ctx, ticker=None, shares: int=1):
    if ticker != None:
        ticker = ticker.upper()
        if str(ticker) in allowed_tickers and ticker != None:
            currentBalance = int(getBalance(ctx.message.author.id))
            priceofeach = int(getStockPrice(ticker))
            price = int(priceofeach * 10)
            currentShares = int(getUserStocks(ctx.message.author.id, ticker))
            if currentShares >= shares:
                setBalance(ctx.message.author.id, currentBalance + price)
                sql = f"update stocks set {ticker} = {currentShares - shares} where userid = {ctx.message.author.id}"
                dbcursor.execute(sql)
                embed=discord.Embed(title=f"Successfully purchased {shares} {ticker} shares at ${priceofeach} each.", description="Make sure to keep that number in mind so you know when to sell!", color=0xee719e)
                await ctx.send(embed=embed)
            else:
                await ctx.send(f"You don't have enough of these stocks to sell! You currently have {currentShares} shares of {ticker}.")
        else:
            await ctx.send("That isn't a stock!")
    else:
        await ctx.send(f"If you would like to view a list of available stocks, you can run `;stocks`!")

@bot.command()
async def tts(ctx, *ttsargs):
    if str(ctx.message.author.id) in allowed_people:
        async with ctx.typing():
            ttstext = ' '.join(ttsargs)
            myobj = gTTS(text=ttstext, lang=language, slow=False) 
            myobj.save("tts.mp3")
        vc = await joinVC(ctx)
        
        vc.play(discord.FFmpegPCMAudio('tts.mp3'), after=lambda e: print('done', e))
        while vc.is_playing():
            await asyncio.sleep(1)
        await vc.disconnect()

@bot.command()
async def say(ctx, *sayargs):
    if str(ctx.message.author.id) in allowed_people or str(ctx.message.author.id) == "481461830808502278":
        await ctx.message.delete()
        await ctx.send(str(' '.join(sayargs)))
        print(f"{ctx.message.author.id} said {str(' '.join(sayargs))}")


# adding report command for preperation on when orange goes down because im really bored
@bot.command()
async def report(ctx, *content):
    if content == '' or content == ' ':
        await ctx.send('You must include something to report')
    else:
        embed = discord.Embed(title="New Report", color=0x15ebe3)
        embed.add_field(name="Report Content", value=f"```{' '.join(content)}```", inline=True)
        embed.add_field(name="User", value=f"<@{ctx.author.id}> (`{ctx.author.id}`)", inline=True)
        embed.set_author(name=f"{str(ctx.author)}", icon_url=ctx.author.avatar_url)      
        try:
            await ctx.author.send('Report Sent! Staff may contact you for further details.')
        except:
            await ctx.send(f"<@{ctx.author.id}> - Your DM's seem to be disabled. The command you ran was successful.")
        await ctx.message.delete()
        #reportLogs = bot.get_channel('757701308395552803')
        await ctx.send(embed=embed)

@bot.command(aliases=["commands"])
async def _commands(ctx):
    commandList = []
    for command in bot.commands:
        cmd = str(command)
        commandList.append(cmd)
    em = discord.Embed(title="Commands List", color=0x15ebe3)
    em.add_field(name="Commands", value=f"`{', '.join(commandList)}`", inline=False)    
    await ctx.send(embed=em)

@bot.command(aliases=["cf"])
async def coinflip(ctx, embed=None):
    if embed != None and embed.lower() == 'noembed':
        options = ["Heads", "Tails"]
        option = random.choice(options)
        await ctx.send(f'I flipped a coin and got `{option}`!')
    else:
        options = ["Heads", "Tails"]
        option = random.choice(options)
        embed = discord.Embed(title='Coin Flip', description=f"I flipped a coin and got `{option}`!", color=0x15ebe3)
        await ctx.send(embed=embed)  


@bot.command()
async def punish(ctx, userToPunish: discord.Member):
    staffRole = discord.utils.get(ctx.guild.roles, name="Staff")
    if staffRole in userToPunish.roles:
        await ctx.send('You cannot punish other staff members.')
        return 0
    punishmentTime = None
    embed=discord.Embed(title=f"Punishing {str(userToPunish)}...", description=f"Please choose a punishment from the reactions below.", color=0x15ebe3)
    embed.set_thumbnail(url=userToPunish.avatar_url)
    embed.add_field(name=f"Kick", value=f"👢", inline=True)
    embed.add_field(name=f"Ban", value=f"<:BanHammer:608760061749362705>", inline=True)
    embed.add_field(name=f"30min", value=f":one:", inline=True)
    embed.add_field(name=f"1 hour", value=f":two:", inline=True)
    embed.add_field(name=f"6 hours", value=f":three:", inline=True)
    embed.add_field(name=f"1 day", value=f":four:", inline=True)
    embed.add_field(name=f"7 days", value=f":five:", inline=True)
    embed.add_field(name=f"21 days", value=f":six:", inline=True)
    embed.add_field(name=f"Custom Mute Value", value=f":timer:", inline=True)
    embed.add_field(name=f"Cancel", value=f":no_entry_sign:", inline=True)
    embed.set_footer(text="The minute/hour/day values are mutes.")
    message = await ctx.send(embed=embed)
    for i in range(len(embed.fields)):
        await message.add_reaction(punishEmojis[i])
    await asyncio.sleep(0.1)
    def reacCheck(reaction, user):
        return str(reaction.emoji) in punishEmojis and user == ctx.author
    try:
        reaction, user = await bot.wait_for("reaction_add", timeout=60.0, check=reacCheck)
    except asyncio.TimeoutError:
        message = await ctx.fetch_message(message.id)
        await message.clear_reactions()
        embed = discord.Embed(title="Timed Out", description="This punishment command has timed out.", color=0xFF0000)
        await message.edit(embed=embed)

    punishmentToDo = str(reaction.emoji)
    if punishmentToDo == ":no_entry_sign:" or punishmentToDo == "🚫":
        message = await ctx.fetch_message(message.id)
        await message.clear_reactions()
        embed = discord.Embed(title="Punishment Cancelled", description="This punishment command has been cancelled.", color=0xFF0000)
        await message.edit(embed=embed)
        return 0
    message = await ctx.fetch_message(message.id)
    await message.clear_reactions()

    def check(m):
        return m.author == ctx.author
    
    if punishmentToDo == ":timer:" or punishmentToDo == "⏲":
        embed = discord.Embed(title="How long should this mute last?", description="Type `cancel` to cancel.", color=0x15ebe3)
        await message.edit(embed=embed)
        punishmentTimeRaw = await bot.wait_for("message", timeout=60.0, check=check)
        if str(punishmentTimeRaw.content) == "cancel":
            embed = discord.Embed(title="Punishment Cancelled", description="This punishment command has been cancelled.", color=0xFF0000)
            await message.edit(embed=embed)
            return 0
        punishmentTime = str(punishmentTimeRaw.content)
        cal = pdt.Calendar()
        diff = cal.parseDT(str(punishmentTimeRaw.content), sourceTime=datetime.min)[0] - datetime.min
        punishmentTime = str(math.trunc(int(diff.total_seconds())))

    
    
    embed = discord.Embed(title="Please type in the reason for this punishment...", description="Type `cancel` to cancel.", color=0x15ebe3)
    await message.edit(embed=embed)

    punishmentReasonRaw = await bot.wait_for("message", timeout=60.0, check=check)
    punishmentReason = str(punishmentReasonRaw.content)
    if punishmentReasonRaw.content == "cancel":
        embed = discord.Embed(title="Punishment Cancelled", description="This punishment command has been cancelled.", color=0xFF0000)
        await message.edit(embed=embed)
        return 0
    if punishmentToDo == ":boot:" or punishmentToDo == "👢":
        await userToPunish.kick(reason=str(punishmentReason))
        await modlog(ctx, userToPunish, punishmentReason, None, ctx.author, "Kick")
        embed = discord.Embed(title="Successfully Kicked", description=f"You have successfully kicked someone.", color=0xFF0000)
        embed.add_field(name=f"User:", value=f"{str(userToPunish)}", inline=True)
        embed.add_field(name=f"Punishment:", value=f"Kick", inline=True)
        embed.add_field(name=f"Reason:", value=f"{str(punishmentReason)}", inline=True)
        await message.edit(embed=embed)
    if punishmentToDo == "<:BanHammer:608760061749362705>":
        await userToPunish.ban(reason=str(punishmentReason))
        await modlog(ctx, userToPunish, punishmentReason, None, ctx.author, "Ban")
        embed = discord.Embed(title="Successfully Ban", description=f"You have successfully banned someone.", color=0xFF0000)
        embed.add_field(name=f"User:", value=f"{str(userToPunish)}", inline=True)
        embed.add_field(name=f"Punishment:", value=f"Ban", inline=True)
        embed.add_field(name=f"Reason:", value=f"{str(punishmentReason)}", inline=True)
        await message.edit(embed=embed)
    if punishmentToDo in muteEmojis:
        if punishmentTime == None:   
            for i in range(len(muteEmojis)):
                if str(muteEmojis[i]) == punishmentToDo:
                    punishmentTime = muteTimes[i]

        mutedRole = discord.utils.get(ctx.guild.roles, name="Muted")
        await userToPunish.add_roles(mutedRole)
        print(punishmentTime)
        embed = discord.Embed(title="Successfully Muted", description=f"You have successfully muted someone.", color=0xFF0000)
        embed.add_field(name=f"User:", value=f"{str(userToPunish)}", inline=True)
        embed.add_field(name=f"Punishment:", value=f"Mute for {show_time(punishmentTime)}.", inline=True)
        embed.add_field(name=f"Reason:", value=f"{str(punishmentReason)}", inline=True)
        await message.edit(embed=embed)
        await modlog(ctx, userToPunish, punishmentReason, show_time(punishmentTime), ctx.author, "Mute")

@bot.command()
async def selfdestruct(ctx):
    embed=discord.Embed(title=f"Self Destructing Millobot", description=f"Please wait.", color=0xFF0000)
    embed.add_field(name=f"Self destructing...", value=f"Loading", inline=True)
    orgmsg = await ctx.send(embed=embed)
    async def newStatus(status):
        embed=discord.Embed(title=f"Self Destructing Millobot", description=f"Please wait.", color=0xFF0000)
        embed.add_field(name=f"Self destructing...", value=f"{status}", inline=True)
        await orgmsg.edit(embed=embed)
    await newStatus("Deleting Files...")
    time.sleep(1)
    await newStatus("Deleting Codebase...")
    time.sleep(0.7)
    await newStatus("Deleting Database...")
    time.sleep(0.8)
    await newStatus("Purging Bot Cache...")
    time.sleep(0.5)
    await newStatus("Preparing for destruction...")
    time.sleep(3)
    await newStatus("3")
    time.sleep(1)
    await newStatus("2")
    time.sleep(1)
    await newStatus("1")
    time.sleep(1)
    await newStatus("Goodbye.")
    await bot.logout()

'''
@bot.command()
async def blackjack(ctx):
    result = "Pending"
    hand1 = random.randint(1, 21)
    def check(message):
        return message.content == ""
    try:
        def check(message: discord.Message):
            return message.channel == ctx.channel and message.author != ctx.me and message.author == ctx.message.author
    choiceRaw = await bot.wait_for('message', timeout=60.0, check=check)
    choice = str(choiceRaw.content) 
    if choice.lower() == 'hit':
        hand2 = random.randint(1, 21)
        if hand1 + hand2 > 21:
            await ctx.send('Bust! Game over.')
        elif hand1 + hand2 = 21:
            await ctx.send('Blackjack! You win!')
        elif hand1 + hand2 < 21:
            await ctx.send(f"Current deck: {str(hand1 + hand2)} - Would you like to hit or stand?")
            choice2Raw = await bot.wait_for('message', timeout=60.0, check=check)
            choice2 = str(choice2Raw.content)
            if choice2.lower() == 'hit':
                hand3 = random.randint(1, 21)
                if hand1 + hand2 + hand3 > 21:
                    await ctx.send('Bust! Game over.')
                elif hand1 + hand2 + hand3 = 21:
                    await ctx.send('Blackjack! You win!')
                elif hand1 + hand2 + hand3 < 21:
                    await ctx.send(f"Current deck: {str(hand1 + hand2 + hand3)} - You survived until round 3 therefore you won!")             
        else: 
            await ctx.send('Unknown Error: {}'.format(str(hand1 + hand2)))
    elif choice.lower() == 'stand':
        if hand1 = 21:
            await ctx.send('Blackjack! You won!')
        elif hand1 > 21:
            await ctx.send('Bust! Game over.')
        elif hand1 < 21:
            await ctx.send('Your hand was below 21. You stood. You lost.')        
 '''

@bot.command()
async def blackjack(ctx):
    hand = random.randint(1, 21)
    if hand == 21:
        await ctx.send('You win! Congratulations')
    else:    
        embed = discord.Embed(title="Please pick from the reactions to hit, stand or cancel.", description=f"Your hand was {hand}.")
        msg = await ctx.send(embed=embed)
        await msg.add_reaction('🇭')
        await msg.add_reaction('🇸')
        def reacCheck(reaction, user):
            return str(reaction.emoji) in ['🇭', '🇸'] and user == ctx.author
    try:
        reaction, user = await bot.wait_for("reaction_add", timeout=60.0, check=reacCheck)
        if str(reaction.emoji) == '🇭':
            await ctx.send('hit')
        elif str(reaction.emoji) == '🇸':
            await ctx.send('stand')    
        else:
            await ctx.send('not an option')    
    except asyncio.TimeoutError:
        message = await ctx.fetch_message(message.id)
        await message.clear_reactions()
        embed = discord.Embed(title="Timed Out", description="This punishment command has timed out.", color=0xFF0000)
        await msg.edit(embed=embed)         

        
bot.run(token)

