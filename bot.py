import random, os, discord, asyncio
from datetime import datetime, timedelta
from discord.ext import commands
from dotenv import load_dotenv

ECHO_CHANNEL_ID = 1300604396555731074  # Wolves-alliance

DESTINATION_CHANNEL_IDS = [
    1300604396555731074,  # Wolves of War
    1300609238023934042,  # Redmoon Cult
    1300646389155627069,  # OneMillionBears
    # Add more destination channels as needed
]

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
last_win_time = {}  # To track last win time for each user

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

@bot.command(name="lootroll", description="React to participate in loot roll for a specific item with a timer")
async def lootroll(ctx, item: str, time: int = 30):
    global last_win_time
    cooldown_period = timedelta(minutes=5)  # Cooldown period for back-to-back wins

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
    while True:
        roll_numbers[item] = {user.name: random.randint(1, 100) for user in users}

        # Announce each user's roll
        for user, roll_value in roll_numbers[item].items():
            await ctx.send(f"🎲 {user} rolled a {roll_value}.")

        # Determine the highest roll(s)
        max_roll = max(roll_numbers[item].values())
        potential_winners = [user for user, roll in roll_numbers[item].items() if roll == max_roll]

        # If there's a tie, display it
        if len(potential_winners) > 1:
            await ctx.send(f"🤝 **It's a tie!** The following players have rolled the highest value of {max_roll}: {', '.join(potential_winners)}")

        # Check for back-to-back winners
        valid_winners = []
        for winner in potential_winners:
            last_win = last_win_time.get(winner)
            if not last_win or datetime.now() - last_win > cooldown_period:
                valid_winners.append(winner)

        if valid_winners:
            # If there's at least one valid winner, choose randomly among them
            winner_name = random.choice(valid_winners)
            roll_value = roll_numbers[item][winner_name]
            break
        else:
            # If all potential winners are disqualified, re-roll for everyone
            await ctx.send("🤔 All potential winners are disqualified for back-to-back wins! Rolling again...")
            users = [user for user in users if user.name in potential_winners]

    # Update the last win time for the winner
    last_win_time[winner_name] = datetime.now()

    if item not in winners:
        winners[item] = []
    winners[item].append(f"{winner_name} (Roll #{roll_value})")

    # List of random emojis for winner announcement
    winner_emojis = ["🏆", "🐔", "🖕", "🥇", "🕺", "🐺", "💣", "🔥"]
    random_emoji = random.choice(winner_emojis)  # Randomly select a winner emoji

    await ctx.send(f"Congratulations {winner_name}! You won the **{item}** with Roll #{roll_value}! {random_emoji}")  # Winner emoji

    # Lock the reactions by removing the bot's own reaction
    await message.clear_reactions()

@bot.command(name="clearall", description="Clear all messages in the channel, including older ones.")
@commands.has_permissions(manage_messages=True)
@commands.cooldown(1, 60, commands.BucketType.channel)  # Limit to 1 use per channel every 60 seconds
async def clearall(ctx):
    await ctx.send("🧹 Starting to clear messages older than 14 days...")

    # Define the cutoff time (14 days ago)
    cutoff_time = datetime.utcnow() - timedelta(days=14)

    async for message in ctx.channel.history(limit=None, before=cutoff_time):  # Retrieve messages before the cutoff time
        try:
            await message.delete()  # Try deleting each message
        except discord.Forbidden:
            await ctx.send("🚫 I don't have permission to delete some messages.")
            return
        except discord.HTTPException as e:
            print(f"Error deleting message: {e}")

    await ctx.send("✅ All messages older than 14 days have been cleared!", delete_after=5)  # Notify completion

@bot.command(name="announce", description="Sends an announcement to our alliance partners.")
@commands.has_permissions(manage_messages=True)
async def announce(ctx, *args):
    announcement_text = " ".join(args)

    not_found_channels = []
    for channel_id in DESTINATION_CHANNEL_IDS:
        destination_channel = bot.get_channel(channel_id)
        if destination_channel:
            await destination_channel.send(f"🐺 **ALLIANCE UPDATE:** {announcement_text}")
        else:
            not_found_channels.append(channel_id)

    if not_found_channels:
        await ctx.send(f"Could not find the following channels: {', '.join(map(str, not_found_channels))}")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if message.channel.id in DESTINATION_CHANNEL_IDS:
        for channel_id in DESTINATION_CHANNEL_IDS:
            if channel_id != message.channel.id:
                target_channel = bot.get_channel(channel_id)
                if target_channel:
                    await target_channel.send(
                        f"📢 **Message from {message.author.display_name} in {message.channel.name}:** {message.content}"
                    )

    await bot.process_commands(message)

@announce.error
async def announce_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("You don't have permission to use this command.")
    elif isinstance(error, commands.BotMissingPermissions):
        await ctx.send("I don't have permission to perform this action.")
    else:
        await ctx.send("An error occurred while running the command.")

bot.run(token)
