#!/usr/bin/env python3
import json
import os
import time
import requests
import subprocess
import logging
from datetime import datetime

# Telegram configuration
TELEGRAM_BOT_TOKEN = "7854831812:AAF5JDgaf43BsMgysPZOIBPzW_39p44gGxw"
TELEGRAM_CHAT_ID = "8111628064"

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='sms_bot.log'
)

def setup_termux_api():
    """Check and install Termux:API if needed"""
    try:
        # Check if termux-sms-list is available
        subprocess.run(["termux-sms-list", "-h"], 
                      stdout=subprocess.PIPE, 
                      stderr=subprocess.PIPE, 
                      check=True)
        logging.info("Termux:API is already installed")
    except (subprocess.SubprocessError, FileNotFoundError):
        logging.warning("Termux:API not found, attempting to install...")
        try:
            subprocess.run(["pkg", "update", "-y"], check=True)
            subprocess.run(["pkg", "install", "termux-api", "-y"], check=True)
            logging.info("Termux:API installed successfully")
        except subprocess.SubprocessError as e:
            logging.error(f"Failed to install Termux:API: {e}")
            raise

def get_sms_messages():
    """Retrieve SMS messages using Termux:API"""
    try:
        result = subprocess.run(["termux-sms-list"], 
                               stdout=subprocess.PIPE, 
                               stderr=subprocess.PIPE, 
                               text=True, 
                               check=True)
        return json.loads(result.stdout)
    except subprocess.SubprocessError as e:
        logging.error(f"Error retrieving SMS: {e}")
        return []
    except json.JSONDecodeError as e:
        logging.error(f"Error parsing SMS JSON: {e}")
        return []

def send_telegram_message(message):
    """Send message to Telegram"""
    api_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    
    try:
        response = requests.post(api_url, data=data)
        response.raise_for_status()
        return True
    except requests.RequestException as e:
        logging.error(f"Error sending to Telegram: {e}")
        return False

def format_sms(sms):
    """Format SMS message for Telegram"""
    timestamp = datetime.fromtimestamp(int(sms.get('received', '0'))/1000).strftime('%Y-%m-%d %H:%M:%S')
    return (
        f"<b>New SMS</b>\n"
        f"<b>From:</b> {sms.get('number', 'Unknown')}\n"
        f"<b>Time:</b> {timestamp}\n"
        f"<b>Message:</b> {sms.get('body', 'No content')}"
    )

def save_processed_sms(sms_ids):
    """Save IDs of processed SMS to avoid duplicate sending"""
    with open("processed_sms.txt", "w") as f:
        for sms_id in sms_ids:
            f.write(f"{sms_id}\n")

def load_processed_sms():
    """Load IDs of processed SMS"""
    if not os.path.exists("processed_sms.txt"):
        return set()
    
    with open("processed_sms.txt", "r") as f:
        return set(line.strip() for line in f)

def main():
    """Main function to monitor and forward SMS"""
    logging.info("Starting SMS forwarder to Telegram")
    print("SMS to Telegram forwarder started. Press Ctrl+C to stop.")
    
    # Setup Termux:API
    setup_termux_api()
    
    # Keep track of processed messages
    processed_sms = load_processed_sms()
    
    try:
        while True:
            # Get all SMS messages
            sms_messages = get_sms_messages()
            
            if not sms_messages:
                time.sleep(30)  # Wait 30 seconds before checking again
                continue
            
            # Check for new messages and send them
            new_messages_count = 0
            for sms in sms_messages:
                sms_id = str(sms.get('_id', ''))
                if sms_id and sms_id not in processed_sms:
                    formatted_message = format_sms(sms)
                    if send_telegram_message(formatted_message):
                        processed_sms.add(sms_id)
                        new_messages_count += 1
                        logging.info(f"Forwarded SMS from {sms.get('number', 'Unknown')}")
            
            # Save processed messages
            if new_messages_count > 0:
                save_processed_sms(processed_sms)
                print(f"Forwarded {new_messages_count} new messages to Telegram")
            
            # Wait before checking again
            time.sleep(60)  # Check every minute
            
    except KeyboardInterrupt:
        print("\nStopping SMS forwarder")
        logging.info("SMS forwarder stopped by user")
    except Exception as e:
        error_msg = f"Unexpected error: {e}"
        print(error_msg)
        logging.error(error_msg)
        send_telegram_message(f"⚠️ Error in SMS forwarder: {e}")

if __name__ == "__main__":
    main()
