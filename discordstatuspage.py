import discord
from discord.ext import tasks, commands
import requests
import platform
import asyncio
from datetime import datetime, timedelta

# Discord token is removed for security reasons
DISCORD_TOKEN = 'YOUR_DISCORD_TOKEN'
CHANNEL_ID = 123456789012345678  # Replace with your main monitoring channel ID
ALERT_CHANNEL_ID = 123456789012345678  # Replace with your alert channel ID
ROLE_NAME = "ADD_ROLE_HERE"  # The name of the role to DM

websites = [
    "https://example.com",
    "https://anotherexample.com"
]

ips = {
    "Service 1": "192.168.1.1",
    "Service 2": "192.168.1.2",
}

# Custom latency thresholds
latency_thresholds = {
    "Service 2": 400,  # Example: Service 2 has a higher latency threshold
}

service_states = {
    service: {
        "status": "Up", 
        "down_since": None, 
        "latency": None, 
        "last_slow_alert": None,
        "incident_message_id": None,
        "failure_count": 0  # Track consecutive failures
    } for service in websites + list(ips.keys())
}

# Configuration parameters
ping_attempts = 8
ping_delay = 6  # seconds between pings
http_timeout = 10  # HTTP request timeout in seconds
failure_threshold = 7  # Number of consecutive failures before reporting a service as down

intents = discord.Intents.default()
intents.members = True  # Ensure we have the permission to access members
bot = commands.Bot(command_prefix="!", intents=intents)

# Initialize the live_message_id variable
live_message_id = None
current_incidents = {}

class ClearIncidentView(discord.ui.View):
    def __init__(self, service_name):
        super().__init__(timeout=None)
        self.service_name = service_name

    @discord.ui.button(label="Clear Incident", style=discord.ButtonStyle.danger)
    async def clear_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.message.delete()
        current_incidents.pop(self.service_name, None)
        await interaction.response.defer()

async def update_live_stats():
    global live_message_id
    channel = bot.get_channel(CHANNEL_ID)
    
    embed = discord.Embed(
        title="🌐 Service Status Dashboard",
        description="Real-time status of monitored services.",
        color=discord.Color.blue(),
        timestamp=datetime.now()
    )
    
    # Categorized fields
    categorized_services = {
        "Websites": ["https://example.com", "https://anotherexample.com"],
        "Service IPs": list(ips.keys())
    }
    
    for category, services in categorized_services.items():
        value = ""
        for service in services:
            state = service_states[service]
            status_color = "🟢" if state["status"] == "Up" else "🔴"
            latency = f" - Latency: {state['latency']}ms" if state["latency"] is not None else ""
            downtime = ""
            if state["status"] == "Down":
                downtime = f" - Downtime: {str(datetime.now() - state['down_since']).split('.')[0]}"
            value += f"{status_color} {service}: **{state['status']}**{latency}{downtime}\n"
        
        embed.add_field(name=category, value=value.strip(), inline=False)
    
    if live_message_id:
        message = await channel.fetch_message(live_message_id)
        await message.edit(embed=embed)
    else:
        message = await channel.send(embed=embed)
        live_message_id = message.id

async def monitor_services():
    down_services = []
    restored_services = []

    for site in websites:
        service_name = site
        is_up = await check_website(service_name)
        if not is_up:
            service_states[service_name]["failure_count"] += 1
        else:
            service_states[service_name]["failure_count"] = 0

        if service_states[service_name]["failure_count"] >= failure_threshold and service_states[service_name]["status"] == "Up":
            service_states[service_name]["status"] = "Down"
            service_states[service_name]["down_since"] = datetime.now()
            down_services.append(service_name)
        elif is_up and service_states[service_name]["status"] == "Down":
            down_duration = datetime.now() - service_states[service_name]["down_since"]
            service_states[service_name]["status"] = "Up"
            service_states[service_name]["down_since"] = None
            restored_services.append((service_name, down_duration))

    for name, ip in ips.items():
        service_name = name
        is_up, latency = await check_latency(service_name, ip)
        if not is_up:
            service_states[service_name]["failure_count"] += 1
        else:
            service_states[service_name]["failure_count"] = 0

        if service_states[service_name]["failure_count"] >= failure_threshold and service_states[service_name]["status"] == "Up":
            service_states[service_name]["status"] = "Down"
            service_states[service_name]["down_since"] = datetime.now()
            service_states[service_name]["latency"] = None
            down_services.append(service_name)
        elif is_up and service_states[service_name]["status"] == "Down":
            down_duration = datetime.now() - service_states[service_name]["down_since"]
            service_states[service_name]["status"] = "Up"
            service_states[service_name]["down_since"] = None
            service_states[service_name]["latency"] = latency
            restored_services.append((service_name, down_duration))
        elif is_up and latency:
            threshold = latency_thresholds.get(service_name, 100)  # Default to 100ms if not specified
            service_states[service_name]["latency"] = latency
            if latency > threshold and (not service_states[service_name]["last_slow_alert"] or datetime.now() - service_states[service_name]["last_slow_alert"] > timedelta(minutes=30)):
                service_states[service_name]["last_slow_alert"] = datetime.now()
                down_services.append(service_name)

    if down_services:
        await create_combined_incident_embed(down_services)
        await dm_users_with_role(down_services)
    for service_name, down_duration in restored_services:
        await update_incident_embed(service_name, down_duration)

async def check_website(site):
    for _ in range(ping_attempts):
        try:
            response = requests.get(site, timeout=http_timeout)
            if response.status_code == 200:
                return True
        except requests.RequestException:
            pass
        await asyncio.sleep(ping_delay)
    return False

async def check_latency(service_name, ip):
    for _ in range(ping_attempts):
        param = '-n' if platform.system().lower() == 'windows' else '-c'
        command = ['ping', param, '1', ip]
        
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        is_up = process.returncode == 0
        if is_up:
            try:
                latency = int(stdout.decode().split('time=')[-1].split('ms')[0].strip())
                return True, latency
            except (IndexError, ValueError):
                pass
        await asyncio.sleep(ping_delay)
    
    return False, None

async def create_combined_incident_embed(down_services):
    channel = bot.get_channel(ALERT_CHANNEL_ID)
    if not current_incidents:
        embed = discord.Embed(
            title=f"🚨 Incident Report",
            description=f"Multiple services have gone down.",
            color=discord.Color.red(),
            timestamp=datetime.now()
        )
        for service_name in down_services:
            embed.add_field(name=service_name, value="Service Down", inline=False)
        message = await channel.send(embed=embed)
        for service_name in down_services:
            current_incidents[service_name] = message.id
        await send_clean_alert()
    else:
        message_id = next(iter(current_incidents.values()))
        try:
            message = await channel.fetch_message(message_id)
            embed = message.embeds[0]
            for service_name in down_services:
                if service_name not in current_incidents:
                    embed.add_field(name=service_name, value="Service Down", inline=False)
                    current_incidents[service_name] = message_id
            await message.edit(embed=embed)
        except discord.NotFound:
            pass  # Message was already deleted or not found.

async def update_incident_embed(service_name, down_duration):
    channel = bot.get_channel(ALERT_CHANNEL_ID)
    message_id = current_incidents.get(service_name)

    if message_id:
        try:
            message = await channel.fetch_message(message_id)
            embed = message.embeds[0]
            for i, field in enumerate(embed.fields):
                if field.name == service_name:
                    embed.set_field_at(i, name=service_name, value=f"Service Restored - Downtime: {str(down_duration).split('.')[0]}", inline=False)
                    embed.color = discord.Color.green()
                    break
            await message.edit(embed=embed, view=ClearIncidentView(service_name))
            current_incidents.pop(service_name)
        except discord.NotFound:
            pass  # Message was already deleted or not found.

async def send_clean_alert():
    channel = bot.get_channel(ALERT_CHANNEL_ID)
    notification = await channel.send("@everyone")
    await notification.delete()

async def dm_users_with_role(down_services):
    guild = bot.get_channel(ALERT_CHANNEL_ID).guild
    role = discord.utils.get(guild.roles, name=ROLE_NAME)
    
    if role:
        for member in role.members:
            try:
                dm_message = f"The following services are down: {', '.join(down_services)}"
                await member.send(dm_message)
            except discord.Forbidden:
                print(f"Could not DM {member.display_name}")

@bot.event
async def on_ready():
    print(f'Bot {bot.user.name} is now online and monitoring services.')
    update_dashboard.start()

@tasks.loop(seconds=10)
async def update_dashboard():
    await monitor_services()
    await update_live_stats()

bot.run(DISCORD_TOKEN)