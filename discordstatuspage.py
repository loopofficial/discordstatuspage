import discord
from discord.ext import tasks, commands
import requests
import asyncio
import platform
from datetime import datetime, timedelta

# Replace the token with your actual Discord bot token
DISCORD_TOKEN = 'YOUR_DISCORD_TOKEN'

# Replace with the actual channel ID where you want to post status updates
CHANNEL_ID = 123456789012345678

# Replace with the actual channel ID where alerts should be sent
ALERT_CHANNEL_ID = 123456789012345678

# Replace with the actual role name that should receive direct messages in case of incidents
ROLE_NAME = "YOUR_ROLE_NAME"

# List of websites to monitor
# Add or remove URLs depending on what services you want to monitor
websites = [
    "https://example.com",
    "https://another-example.com",
    "https://yet-another-example.com/"
]

# Dictionary of services and their corresponding IPs to monitor latency
# Customize the names and IP addresses to match the services you are monitoring
ips = {
    "Service 1": "123.123.123.123",
    "Service 2": "234.234.234.234",
    "Service 3": "345.345.345.345",
    "Service 4": "456.456.456.456",
    "Service 5": "567.567.567.567"
}

# Latency thresholds (in milliseconds) for specific services
# If a service exceeds this threshold, it will be considered slow
latency_thresholds = {
    "Service 5": 400,  # Adjust the threshold according to your needs
}

# Initial state configuration for all monitored services
service_states = {
    service: {
        "status": "Up", 
        "down_since": None, 
        "latency": None, 
        "last_slow_alert": None,
        "incident_message_id": None,
        "failure_count": 0
    } for service in websites + list(ips.keys())
}

# Number of attempts to ping a service before marking it as down
ping_attempts = 3

# Delay between each ping attempt (in seconds)
ping_delay = 0.5

# Timeout duration for HTTP requests (in seconds)
http_timeout = 5

# Number of consecutive failures required to consider a service as down
failure_threshold = 3

# Discord bot intents (permissions) configuration
intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

live_message_id = None
current_incidents = {}

class ClearIncidentView(discord.ui.View):
    def __init__(self, service_name):
        super().__init__(timeout=None)
        self.service_name = service_name

    @discord.ui.button(label="Clear Incident", style=discord.ButtonStyle.danger)
    async def clear_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        message_id = current_incidents.get(self.service_name)
        if not message_id:
            await interaction.response.defer()
            return

        try:
            channel = bot.get_channel(ALERT_CHANNEL_ID)
            message = await channel.fetch_message(message_id)
            embed = message.embeds[0]
            
            # Remove the field corresponding to the restored service
            embed.clear_fields()
            down_services = []
            for service, state in service_states.items():
                if state["status"] == "Down":
                    downtime = f" - Downtime: {str(datetime.now() - state['down_since']).split('.')[0]}"
                    embed.add_field(name=service, value=f"Service Down{downtime}", inline=False)
                    down_services.append(service)
            
            if down_services:
                await message.edit(embed=embed)
            else:
                await message.delete()
                current_incidents.clear()
            
            current_incidents.pop(self.service_name, None)
            service_states[self.service_name]["incident_message_id"] = None
            
            await interaction.response.defer()
        except discord.NotFound:
            pass

async def update_live_stats():
    global live_message_id
    channel = bot.get_channel(CHANNEL_ID)
    
    embed = discord.Embed(
        title="🌐 Service Status Dashboard",
        description="Real-time status of monitored services.",
        color=discord.Color.blue(),
        timestamp=datetime.now()
    )
    
    categorized_services = {
        "Websites": websites,
        "Service Group 1": ["Service 1"],
        "Service Group 2": ["Service 2", "Service 3", "Service 4"],
        "Service Group 3": ["Service 5"]
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

    tasks = []
    for site in websites:
        tasks.append(check_website(site))

    for name, ip in ips.items():
        tasks.append(check_latency(name, ip))

    results = await asyncio.gather(*tasks)

    for result in results:
        service_name, is_up, latency = result
        if is_up:
            service_states[service_name]["failure_count"] = 0
            if service_states[service_name]["status"] == "Down":
                down_duration = datetime.now() - service_states[service_name]["down_since"]
                service_states[service_name]["status"] = "Up"
                service_states[service_name]["down_since"] = None
                service_states[service_name]["latency"] = latency
                restored_services.append((service_name, down_duration))
            elif latency:
                threshold = latency_thresholds.get(service_name, 100)
                service_states[service_name]["latency"] = latency
                if latency > threshold and (not service_states[service_name]["last_slow_alert"] or datetime.now() - service_states[service_name]["last_slow_alert"] > timedelta(minutes=30)):
                    service_states[service_name]["last_slow_alert"] = datetime.now()
                    down_services.append(service_name)
        else:
            service_states[service_name]["failure_count"] += 1
            if service_states[service_name]["failure_count"] >= failure_threshold and service_states[service_name]["status"] == "Up":
                service_states[service_name]["status"] = "Down"
                service_states[service_name]["down_since"] = datetime.now()
                down_services.append(service_name)

    if down_services:
        await create_combined_incident_embed(down_services)
        await dm_users_with_role(down_services)
    for service_name, down_duration in restored_services:
        await update_incident_embed(service_name, down_duration)

async def check_website(site):
    service_name = site
    for _ in range(ping_attempts):
        try:
            response = requests.get(site, timeout=http_timeout)
            if response.status_code == 200:
                return service_name, True, None
        except requests.RequestException:
            pass
        await asyncio.sleep(ping_delay)
    return service_name, False, None

async def check_latency(service_name, ip):
    latencies = []
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
                latency = float(stdout.decode().split('time=')[-1].split('ms')[0].strip())
                latencies.append(latency)
            except (IndexError, ValueError):
                continue
        await asyncio.sleep(ping_delay)
    
    if latencies:
        avg_latency = round(sum(latencies) / len(latencies), 2)
        return service_name, True, avg_latency
    return service_name, False, None

async def create_combined_incident_embed(down_services):
    channel = bot.get_channel(ALERT_CHANNEL_ID)
    if not current_incidents:
        service_count = len(down_services)
        embed_title = "🚨 Incident Report"
        embed_description = f"{service_count} service{'s' if service_count > 1 else ''} have gone down."

        embed = discord.Embed(
            title=embed_title,
            description=embed_description,
            color=discord.Color.red(),
            timestamp=datetime.now()
        )
        for service_name in down_services:
            embed.add_field(name=service_name, value="Service Down", inline=False)
        message = await channel.send(embed=embed)
        for service_name in down_services:
            current_incidents[service_name] = message.id
            service_states[service_name]["incident_message_id"] = message.id
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
                    service_states[service_name]["incident_message_id"] = message_id
            await message.edit(embed=embed)
        except discord.NotFound:
            pass

async def update_incident_embed(service_name, down_duration):
    message_id = current_incidents.get(service_name)
    if not message_id:
        return

    try:
        channel = bot.get_channel(ALERT_CHANNEL_ID)
        message = await channel.fetch_message(message_id)
        embed = message.embeds[0]
        
        for i, field in enumerate(embed.fields):
            if field.name == service_name:
                embed.set_field_at(i, name=service_name, value=f"Service Restored - Downtime: {str(down_duration).split('.')[0]}", inline=False)
                break
        
        await message.edit(embed=embed, view=ClearIncidentView(service_name))
    except discord.NotFound:
        pass

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
                dm_message = f"The following service{'s are' if len(down_services) > 1 else ' is'} down: {', '.join(down_services)}"
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

# Start the bot using the provided token
bot.run(DISCORD_TOKEN)
