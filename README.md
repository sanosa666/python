# Event Notifier Bot

This is a Telegram bot designed to assist with event notifications, and guest interaction management. The bot provides features such as user registration, messaging with administration and broadcasting messages to guests.

## Features
- **User Registration**: Guests can register themselves using a personalized link or QR code.
- **Broadcast Messages**: Admins can send announcements to all registered users.
- **Q&A**: Guests can ask questions, and admins can respond.

---

## Prerequisites

To run project the following tools should be installed:

1. **Python 3.8 or higher**
2. **Git**
3. **Telegram Bot API Token**

---

## Setup Instructions

1. **Clone the repository**:
   ```bash
   git clone https://github.com/sanosa666/python.git
   cd python
   ```

2. **Create and activate a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate   
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure the bot token**:
   Replace `replace_with_bot_token` in the `main.py` file with your actual bot token:
   ```python
   BOT_TOKEN = "replace_with_bot_token"
   ```

5. **Run the bot**:
   ```bash
   python main.py
   ```

---

## How to Use the Bot

   Users can register theirs account using link to bot encoded in QR code. This code could be scanned by device's camera. 
   Example of the encoded link:
   ```
   https://t.me/{example_bot_name}?start={example_guest_name}
   ```