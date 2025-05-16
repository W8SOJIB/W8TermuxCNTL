#!/data/data/com.termux/files/usr/bin/bash

echo "Setting up SMS to Telegram Forwarder..."

# Update packages
pkg update -y
pkg upgrade -y

# Install required packages
pkg install python -y
pkg install termux-api -y

# Install Python dependencies
pip install -r requirements.txt

# Set executable permissions
chmod +x TermuxAndroidHK.py

echo "Requesting SMS permissions..."
termux-setup-storage
termux-sms-list

echo "Setup complete! Run the script with: python TermuxAndroidHK.py"
echo "To run in background: nohup python TermuxAndroidHK.py &" 
