import os
import discord
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
import psycopg2
import psycopg2.extras

load_dotenv()
TOKEN = os.environ["TOKEN"]
DATABASE_URL = os.environ["DATABASE_URL"]  # Get DATABASE_URL from the environment

# Connect to your postgres DB using DATABASE_URL
conn = psycopg2.connect(DATABASE_URL, sslmode='require')  # Added sslmode as Heroku requires SSL connections
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS logs (
        id SERIAL PRIMARY KEY,
        user_id bigint,
        log_time TIMESTAMP,
        description TEXT
    )
''')
conn.commit()

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.typing = True
intents.members = True
bot = discord.Client(intents=intents)


def get_est_now():
    utc_now = datetime.now(timezone.utc)  # Current time in UTC
    est_now = utc_now - timedelta(hours=5)  # Convert UTC to EST (UTC-5)
    return est_now.strftime("%Y-%m-%d %H:%M:%S")


def isUserInDB(user_id):
    cursor.execute('''
        SELECT * FROM logs WHERE user_id = %s
    ''', (user_id,))
    return cursor.fetchone() is not None


def getLogCount(user_id):
    cursor.execute('''
        SELECT COUNT(*) FROM logs WHERE user_id = %s
    ''', (user_id,))
    return cursor.fetchone()[0]


def lastLog(user_id):
    cursor.execute('''
        SELECT log_time FROM logs WHERE user_id = %s ORDER BY id DESC LIMIT 1
    ''', (user_id,))
    return cursor.fetchone()[0]

WORKERS = {
    "Tommy" : "377929873991270410",
}

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if message.content.startswith('!log'):
        user_id = message.author.id

        if hasLoggedToday(user_id):
            await message.channel.send(f"<@{str(message.author.id)}> has already logged work today.")
            return

        desc = message.content[5:]
        now = get_est_now()
        cursor.execute('''
            INSERT INTO logs (user_id, log_time, description) VALUES (%s, %s, %s)
        ''', (user_id, now, desc))
        conn.commit()

        embed = discord.Embed(
            title="Work Logged", description=f"<@{str(message.author.id)}> has logged work for today.", color=0x00ff00)
        embed.add_field(name="Log Time", value=now, inline=True)
        embed.add_field(name="Days Worked",
                        value=f"{getLogCount(user_id)} Days", inline=True)
        embed.add_field(name="Description", value=desc, inline=False)
        await message.channel.send(embed=embed)

    if message.content.startswith('!leaderboard'):
        cursor.execute('''
            SELECT user_id, COUNT(*) FROM logs GROUP BY user_id ORDER BY COUNT(*) DESC
        ''')
        leaderboard = cursor.fetchall()
        guild = bot.get_guild(1207127307958100009)
        embed = discord.Embed(
            title="Leaderboard", description="Top 10 Users by Work Logged", color=0xff0000)
        for i, (user_id, count) in enumerate(leaderboard[:10]):
            if not user_id:
                continue
            member = guild.get_member(int(user_id))
            embed.add_field(
                name=f"{i+1}. {member.display_name} | {count} Days", value="", inline=False)
        await message.channel.send(embed=embed)

    if message.content.startswith('!lastmonth'):
        cursor.execute('''
            SELECT user_id, COUNT(*) FROM logs WHERE log_time >= CURRENT_DATE - INTERVAL '1 month' GROUP BY user_id ORDER BY COUNT(*) DESC
        ''')
        leaderboard = cursor.fetchall()
        guild = bot.get_guild(1207127307958100009)
        embed = discord.Embed(
            title="Leaderboard", description="Top 10 Users by Work Logged Last Month", color=0xff0000)
        for i, (user_id, count) in enumerate(leaderboard[:10]):
            if not user_id:
                continue
            member = guild.get_member(int(user_id))
            embed.add_field(
                name=f"{i+1}. {member.display_name} | {count} Days", value="", inline=False)
        await message.channel.send(embed=embed)

    if message.content.startswith('!help'):
        embed = discord.Embed(
            title="Timeclock Help", description="Commands for the Timeclock Bot", color=0xff0000)
        embed.add_field(
            name="!log", value="Log your work for the day.", inline=False)
        embed.add_field(
            name="!leaderboard", value="View the top 10 users by work logged.", inline=False)
        await message.channel.send(embed=embed)

    if message.content.startswith('!clearall'):
        if str(message.author.id) != WORKERS["Tommy"]:
            print(message.author.id)
            await message.channel.send("You do not have permission to clear the work log.")
            return
        
        cursor.execute('''
            DELETE FROM logs
        ''', (user_id,))
        conn.commit()
        await message.channel.send(f"Cleared entire work log.")

    if message.content.startswith('!stats'):
        args = message.content.split()
        user_id = str(message.author.id)
        if len(args) > 1:
            user_id = args[1]
        else:
            user_id = message.author.id

        if not isUserInDB(user_id):
            await message.channel.send(f"<@{str(message.author.id)}> has not logged any work.")
            return

        days_worked = getLogCount(user_id)
        embed = discord.Embed(
            title="Work Stats", description=f"Stats for <@{str(message.author.id)}>", color=0xff0000)
        embed.add_field(name="Days Worked",
                        value=f"{days_worked} Days", inline=False)
        embed.add_field(name="Last Log", value=lastLog(user_id), inline=False)
        await message.channel.send(embed=embed)

    if message.content.startswith('!purge'):
        args = message.content.split()
        if len(args) < 2:
            await message.channel.send("Please provide a number of messages to purge.")
            return

        await message.channel.purge(limit=int(args[1]))

bot.run(TOKEN)
