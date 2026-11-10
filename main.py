
import os
import asyncio
import discord
from discord.ext import commands
from fastapi import FastAPI
import httpx

TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("WELCOME_CHANNEL_ID", "0"))

intents = discord.Intents.default()
intents.members = True
intents.presences = True

bot = commands.Bot(command_prefix="!", intents=intents)
app = FastAPI()

@app.get("/")
async def home():
    return {"status": "Crypto Radar Bot is running"}

@app.get("/health")
async def health():
    return {"ok": True, "discord_connected": bot.is_ready()}

@bot.event
async def on_ready():
    print(f"Crypto Radar Bot online as {bot.user}")
    try:
        await bot.tree.sync()
        print("Slash commands synced")
    except Exception as error:
        print(error)

@bot.event
async def on_member_join(member):
    if CHANNEL_ID:
        channel = bot.get_channel(CHANNEL_ID)
        if channel:
            await channel.send(f"Welcome {member.mention}!")

@bot.tree.command(name="crypto", description="Check a cryptocurrency price")
async def crypto(interaction: discord.Interaction, coin: str):
    await interaction.response.defer(ephemeral=True)
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={
                "ids": coin.lower(),
                "vs_currencies": "usd",
                "include_24hr_change": "true"
            }
        )
    data = response.json().get(coin.lower())
    if not data:
        await interaction.followup.send("Coin not found. Try bitcoin, ethereum, or solana.")
        return
    price = data.get("usd", "unavailable")
    change = data.get("usd_24h_change", "unavailable")
    await interaction.followup.send(
        f"{coin.title()}: ${price} USD\n24-hour change: {change}%"
    )

@bot.tree.command(name="recentmembers", description="Show recent members in this server")
async def recentmembers(interaction: discord.Interaction):
    members = sorted(
        interaction.guild.members,
        key=lambda member: member.joined_at or discord.utils.utcnow(),
        reverse=True
    )
    lines = [
        f"{member.display_name} — {discord.utils.format_dt(member.joined_at, style='R')}"
        for member in members[:10]
    ]
    await interaction.response.send_message(
        "\n".join(lines) if lines else "No member data available.",
        ephemeral=True
    )

async def run_bot():
    if TOKEN:
        await bot.start(TOKEN)
    else:
        print("DISCORD_TOKEN is missing")

@app.on_event("startup")
async def startup():
    asyncio.create_task(run_bot())

@app.on_event("shutdown")
async def shutdown():
    if not bot.is_closed():
        await bot.close()
