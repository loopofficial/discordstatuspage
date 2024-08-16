# 🌐 Discord Service Monitor Bot

Welcome to the **Discord Service Monitor Bot**! This bot is your all-in-one solution for monitoring the health of your online services directly from your Discord server. Whether you’re managing a web hosting platform, game servers, or any other critical online infrastructure, this bot keeps you informed and prepared for any situation.

## 🚀 Features

- **Real-Time Monitoring:** Keep an eye on your websites and servers 24/7 with real-time status updates.
- **Customizable Latency Alerts:** Set custom thresholds for latency to detect when a service is underperforming.
- **Instant Incident Notifications:** Get immediate alerts when services go down, complete with automatic role-based notifications.
- **Interactive Status Dashboard:** View live updates of your service status in a beautifully formatted Discord embed.
- **Incident Management:** Manage and clear incidents directly through Discord with interactive buttons.

## 🎯 Why Use This Bot?

In today’s fast-paced digital world, uptime and performance are everything. This bot empowers you to:

- **React Quickly:** With instant alerts, you and your team can respond to issues before they become critical.
- **Stay Informed:** Regular updates keep everyone on the same page, minimizing downtime and service disruptions.
- **Collaborate Effectively:** Role-based notifications ensure that the right team members are notified instantly, reducing response times.

## 🛠️ Getting Started

### Prerequisites

- **Python 3.7+**: Ensure you have the latest version of Python installed.
- **Discord Bot Token**: Create a bot on the [Discord Developer Portal](https://discord.com/developers/applications) and get your bot token.
- **Dependencies:** Install the necessary Python packages:
  ```bash
  pip install discord.py requests
  ```

### Installation

1. **Clone this repository**:
   ```bash
   git clone https://github.com/loopofficial/discordstatuspage.git
   cd discordstatuspage
   ```

2. **Configure your bot**:
   - Replace the `DISCORD_TOKEN` in `discordalerts.py` with your bot's token.
   - Update the `CHANNEL_ID` and `ALERT_CHANNEL_ID` with the IDs of the channels where you want the bot to send updates.
   - Add the websites and IPs you want to monitor in the `websites` and `ips` dictionaries.

3. **Run the bot**:
   ```bash
   python discordalerts.py
   ```

### Customization

- **Latency Thresholds:** Customize the latency alert thresholds by editing the `latency_thresholds` dictionary.
- **Ping Configuration:** Adjust `ping_attempts` and `ping_delay` to fine-tune the monitoring process.

## 💡 Example Use Cases

- **Website Uptime Monitoring:** Ensure your site is always available to users.
- **Game Server Health Check:** Monitor latency and uptime for your gaming servers, alerting admins when something goes wrong.
- **Critical Service Monitoring:** Keep track of essential services like databases, API endpoints, and more.

## 👥 Contributing

Have ideas to improve the bot? Contributions are welcome! Feel free to fork the repository and submit a pull request. Whether it’s new features, bug fixes, or documentation improvements, we’d love your help!

## 📝 License

This project is licensed under the NonCommercial 4.0 International (CC BY-NC 4.0) License. See the [LICENSE](LICENSE) file for more details.

---

### 🌟 Star This Repository

If you find this project useful, please consider starring the repository! It helps others find it and shows your support.

---

### 📬 Support

Need help? Feel free to open an issue on GitHub, or reach out to me via Discord.
