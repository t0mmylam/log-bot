import os
import discord
from datetime import datetime
from dotenv import load_dotenv
import sqlite3

load_dotenv()
TOKEN = os.environ["TOKEN"]

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.typing = True
intents.members = True
bot = discord.Client(intents=intents)

# Database setup
conn = sqlite3.connect('timeclock.db')
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        log_time TEXT
    )
''')
conn.commit()

def getLogCount(user_id):
    cursor.execute('''
        SELECT COUNT(*) FROM logs WHERE user_id = ?
    ''', (user_id,))
    return cursor.fetchone()[0]

def hasWorkedToday(user_id):
    cursor.execute('''
        SELECT * FROM logs WHERE user_id = ? AND log_time >= date('now')
    ''', (user_id,))
    return cursor.fetchone() != None

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if message.content.startswith('!log'):
        user_id = message.author.id

        if hasWorkedToday(user_id):
            await message.channel.send(f"<@{str(message.author.id)}> has already logged work for today.")
            return

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute('''
            INSERT INTO logs (user_id, log_time) VALUES (?, ?)
        ''', (user_id, now))
        conn.commit()

        embed = discord.Embed(title="Work Logged", description=f"<@{str(message.author.id)}> has logged work for today.", color=0xff0000)
        embed.add_field(name="Log Time", value=now.strftime("%Y-%m-%d %H:%M:%S"), inline=True)
        embed.add_field(name="Days Worked", value=f"{getLogCount(user_id)} Days", inline=True)
        await message.channel.send(embed=embed)
    
    if message.content.startswith('!leaderboard'):
        cursor.execute('''
            SELECT user_id, COUNT(*) FROM logs GROUP BY user_id ORDER BY COUNT(*) DESC
        ''')
        leaderboard = cursor.fetchall()
        embed = discord.Embed(title="Leaderboard", description="Top 10 Users by Work Logged", color=0xff0000)
        for i, (user_id, count) in enumerate(leaderboard[:10]):
            user = bot.get_user(int(user_id))
            embed.add_field(name=f"{i+1}. {user.name}", value=f"{count} Days", inline=False)
        await message.channel.send(embed=embed)

    if message.content.startswith('!help'):
        embed = discord.Embed(title="Timeclock Help", description="Commands for the Timeclock Bot", color=0xff0000)
        embed.add_field(name="!log", value="Log your work for the day.", inline=False)
        embed.add_field(name="!leaderboard", value="View the top 10 users by work logged.", inline=False)
        await message.channel.send(embed=embed)

    if message.content.startswith('!clear'):
        args = message.content.split()
        user_id = str(message.author.id)
        if len(args) > 1:
            user_id = args[1]
        else:
            print("Please provide a user id to clear.")

        cursor.execute('''
            DELETE FROM logs WHERE user_id = ?
        ''', (user_id,))
        conn.commit()
        await message.channel.send(f"<@{str(message.author.id)}> has cleared their work log.")
    
    if message.content.startswith('!stats'):
        user_id = message.author.id
        days_worked = getLogCount(user_id)
        embed = discord.Embed(title="Work Stats", description=f"Stats for <@{str(message.author.id)}>", color=0xff0000)
        embed.add_field(name="Days Worked", value=f"{days_worked} Days", inline=False)
        await message.channel.send(embed=embed)


bot.run(TOKEN)