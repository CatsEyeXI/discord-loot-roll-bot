import random, os, discord, json, asyncio
from datetime import datetime
from discord.ext import commands
from dotenv import load_dotenv

# Load environment variables
load_dotenv('bot_config.env')
token = os.getenv("DISCORD_TOKEN")

# Configure bot intents
intents = discord.Intents.default()
intents.reactions = True
intents.messages = True  # Ensure the bot can read messages
intents.message_content = True

# Initialize the bot
bot = commands.Bot(command_prefix="!", intents=intents, case_insensitive=True)

# Dictionary to store winners and roll numbers
winners = {}
roll_numbers = {}  # To track roll numbers per loot roll session

# Load winners from JSON
def load_winners():
    global winners
    if os.path.exists("winners.json"):
        with open("winners.json", "r") as f:
            winners = json.load(f)

# Save winners to JSON
def save_winners():
    with open("winners.json", "w") as f:
        json.dump(winners, f)

# Log winner information to a file
def log_winner(item, winner_name, roll_value):
    with open("winners_log.txt", "a") as f:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"{timestamp} - {winner_name} (Roll #{roll_value}) won the {item}\n")

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    load_winners()

@bot.command(name="lootroll", description="React to participate in loot roll for a specific item with a timer")
async def lootroll(ctx, item: str, time: int = 30):
    # Initialize roll numbers for this item
    roll_numbers[item] = {}
    
    message = await ctx.send(f"💰 Time to get rich! React with 🎲 to claim the **{item}**! ⏳ Time left: {time} seconds!")
    await message.add_reaction("🎲")

    await asyncio.sleep(time)  # Wait for the set time

    reaction_message = await ctx.channel.fetch_message(message.id)
    reaction = discord.utils.get(reaction_message.reactions, emoji="🎲")

    if not reaction:
        await ctx.send(f"🙁 No reactions found for the **{item}**. Better luck next time!")
        return

    users = [user async for user in reaction.users()]
    users = [user for user in users if user != bot.user]

    if not users:
        await ctx.send(f"🙁 Nobody reacted for the **{item}**. Try again next time!")
        return

    # Assign random roll numbers (between 1 and 100) to users
    for user in users:
        roll_value = random.randint(1, 100)  # Generate a random roll number
        roll_numbers[item][user.name] = roll_value

        await ctx.send(f"🎲 {user} rolled a {roll_value}.")

    winner_name = max(roll_numbers[item], key=roll_numbers[item].get)  # Get the user with the highest roll
    roll_value = roll_numbers[item][winner_name]

    if item not in winners:
        winners[item] = []
    winners[item].append(f"{winner_name} (Roll #{roll_value})")
    save_winners()

    # List of random emojis for winner announcement
    winner_emojis = ["🏆", "🐔", "🖕", "🥇", "🕺", "🐺", "💣", "🔥"]
    random_emoji = random.choice(winner_emojis)  # Randomly select a winner emoji

    log_winner(item, winner_name, roll_value)

    await ctx.send(f"Congratulations {winner_name}! You won the **{item}** with Roll #{roll_value}! {random_emoji}")  # Winner emoji

    # Lock the reactions by removing the bot's own reaction
    await message.clear_reactions()  # This line will remove all reactions after the roll is done

@bot.command(name="checkwinners", description="Check all winners in an embedded list")
async def check_winners(ctx):
    if winners:
        embed = discord.Embed(title="📜 Loot Roll Winners", color=discord.Color.gold())
        for item, winners_list in winners.items():
            winners_str = "\n".join([f"• {winner}" for winner in winners_list])
            embed.add_field(name=f"**{item}**", value=winners_str, inline=False)
    else:
        embed = discord.Embed(
            title="📜 Loot Roll Winners",
            description="No winners recorded yet.",
            color=discord.Color.gold()
        )

    await ctx.send(embed=embed)

@bot.command(name="listitems", description="List all items with loot rolls")
async def list_items(ctx):
    if winners:
        items_str = "\n".join([f"• {item}" for item in winners.keys()])
        embed = discord.Embed(
            title="📦 Items with Loot Rolls",
            description=items_str,
            color=discord.Color.blue()
        )
    else:
        embed = discord.Embed(
            title="📦 Items with Loot Rolls",
            description="No loot rolls have been conducted yet.",
            color=discord.Color.blue()
        )

    await ctx.send(embed=embed)

@bot.command(name="clearall", description="Clear all messages in the channel (up to 100).")
@commands.has_permissions(manage_messages=True)
@commands.cooldown(1, 60, commands.BucketType.channel)  # Limit to 1 use per channel every 60 seconds
async def clearall(ctx):
    await ctx.channel.purge(limit=100)  # Adjust the limit as needed (up to 100)
    await ctx.send("🧹 Cleared all messages!", delete_after=5)  # Message will disappear after 5 seconds

@clearall.error
async def clearall_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"This command is on cooldown. Please wait {int(error.retry_after)} seconds before using it again.")

@bot.command(name="clear", description="Clear a specified number of messages.")
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int):
    await ctx.channel.purge(limit=amount)
    await ctx.send(f"🧹 Cleared {amount} messages!", delete_after=5)

bot.run(token)
