import random, os, discord, json, asyncio
from datetime import datetime
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

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

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
    while True:
        roll_numbers[item] = {user.name: random.randint(1, 100) for user in users}

        # Announce each user's roll
        for user, roll_value in roll_numbers[item].items():
            await ctx.send(f"🎲 {user} rolled a {roll_value}.")

        # Determine the highest roll(s)
        max_roll = max(roll_numbers[item].values())
        winners_list = [user for user, roll in roll_numbers[item].items() if roll == max_roll]

        if len(winners_list) == 1:
            break  # Single winner found
        else:
            # Announce the tie and re-roll
            tied_users = ", ".join(winners_list)
            await ctx.send(f"🤔 It's a tie between {tied_users}! Rolling again...")

            users = [user for user in users if user.name in winners_list]

    winner_name = winners_list[0]
    roll_value = max_roll

    if item not in winners:
        winners[item] = []
    winners[item].append(f"{winner_name} (Roll #{roll_value})")

    # List of random emojis for winner announcement
    winner_emojis = ["🏆", "🐔", "🖕", "🥇", "🕺", "🐺", "💣", "🔥"]
    random_emoji = random.choice(winner_emojis)  # Randomly select a winner emoji

    await ctx.send(f"Congratulations {winner_name}! You won the **{item}** with Roll #{roll_value}! {random_emoji}")  # Winner emoji

    # Lock the reactions by removing the bot's own reaction
    await message.clear_reactions()

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

@bot.command(name="announce", description="Sends an announcement to our alliance partners.")
@commands.has_permissions(manage_messages=True)
async def announce(ctx, *args):
    # Combine all arguments into a single string
    announcement_text = " ".join(args)

    # Send the announcement to each specified channel
    not_found_channels = []
    for channel_id in DESTINATION_CHANNEL_IDS:
        destination_channel = bot.get_channel(channel_id)
        if destination_channel:
            # Relay the message to each destination channel
            await destination_channel.send(f"🐺 **ALLIANCE UPDATE:** {announcement_text}")
        else:
            not_found_channels.append(channel_id)

    # Notify if any channels could not be found
    if not_found_channels:
        await ctx.send(f"Could not find the following channels: {', '.join(map(str, not_found_channels))}")

@bot.event
async def on_message(message):
    # Ignore messages from the bot itself
    if message.author == bot.user:
        return

    # Check if the message was sent in one of the monitored channels
    if message.channel.id in DESTINATION_CHANNEL_IDS:
        # Loop through each channel in DESTINATION_CHANNEL_IDS
        for channel_id in DESTINATION_CHANNEL_IDS:
            # Skip the channel where the message was sent
            if channel_id != message.channel.id:
                # Get the target channel to echo the message to
                target_channel = bot.get_channel(channel_id)
                if target_channel:
                    # Forward the message content to the target channel
                    await target_channel.send(
                        f"📢 **Message from {message.author.display_name} in {message.channel.name}:** {message.content}"
                    )

    # Ensure other commands can still function
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
