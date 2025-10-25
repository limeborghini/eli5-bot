# bot.py  (make sure the file is NOT named discord.py)
import os
import logging
import discord
from discord.ext import commands
from dotenv import load_dotenv, find_dotenv
from pathlib import Path
from openai import OpenAI

# === Environment (robust) ===
ENV_PATH = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=ENV_PATH) or load_dotenv(find_dotenv())

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OPENAI_KEY = (os.getenv("OPENAI_API_KEY") or "").strip()

# === Logging ===
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')

# === Intents ===
intents = discord.Intents.default()
intents.message_content = True   # needed for prefix commands to read message content
intents.members = True

# === OpenAI client (new SDK) — pass key explicitly ===
client = OpenAI(api_key=OPENAI_KEY)

# === Bot ===
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} (id: {bot.user.id})')

# ---------- Commands ----------

@bot.command(name="hello")
async def hello(ctx: commands.Context):
    """Greets the user."""
    try:
        await ctx.send(f"Hello {ctx.author.mention}! 👋")
    except Exception as e:
        print("hello error:", e)

@bot.command(name="helpme")
async def helpme(ctx: commands.Context):
    """Shows available commands."""
    help_text = (
        "Here are the commands you can use:\n"
        "!hello - Greets the user.\n"
        "!helpme - Displays this help message.\n"
        "!explain <question> - Provides a simple explanation for the given question."
    )
    await ctx.send(help_text)

@bot.command(name="explain")
async def explain(ctx: commands.Context, *, question: str):
    """Explain something in simple terms using OpenAI."""
    if not OPENAI_KEY:
        await ctx.send("⚠️ OPENAI_API_KEY is missing. Add it to your .env and restart.")
        return

    try:
        async with ctx.typing():
            resp = client.chat.completions.create(
                model="gpt-4o-mini",  # choose a model you have access to
                messages=[
                    {"role": "system", "content": "You explain things simply and clearly."},
                    {"role": "user", "content": f"Explain the following in simple terms: {question}"}
                ],
                max_tokens=200,
                temperature=0.7,
            )
            answer = resp.choices[0].message.content.strip()
        await ctx.send(answer)

    except Exception as e:
        import traceback
        traceback.print_exc()

        err = str(e).lower()
        if "401" in err or "invalid_api_key" in err:
            hint = "Invalid or missing API key. Check OPENAI_API_KEY in your .env."
        elif "429" in err or "rate limit" in err:
            hint = "Rate limit hit. Try again later."
        elif "model" in err and ("not found" in err or "does not exist" in err):
            hint = "Model name may be wrong or not enabled for your account."
        else:
            hint = "See logs for details."
        await ctx.send(f"⚠️ OpenAI error: {hint}")

# === Run Bot ===
if not DISCORD_TOKEN:
    raise RuntimeError("DISCORD_TOKEN missing. Add it to your .env")
bot.run(DISCORD_TOKEN, log_handler=handler, log_level=logging.DEBUG)


# === Setup answer cache ===
# - Create a data structure (e.g., a list or deque) to hold the last 10 answers.
# - Each entry can store: the original question, the generated answer, and maybe who asked it.
# - Keep the cache global or attached to the bot so all commands can access it.

# === When user calls !explain ===
# 1. Check if the question matches something already in the cache:
#    - Loop through the cache (or use a dictionary for quick lookup).
#    - If found, reuse the cached answer instead of calling OpenAI again.
#    - Send the cached answer to the user.
#
# 2. If not found in cache:
#    - Call OpenAI as usual to generate a new answer.
#    - Send the answer to the user.
#    - Insert this new (question, answer) pair into the cache.
#    - If the cache already has 10 entries, remove the oldest one so size stays at 10.


