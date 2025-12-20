#!/bin/bash

# Update system
echo "Updating system..."
sudo apt-get update && sudo apt-get upgrade -y

# Install Python and Pip
echo "Installing Python3 and pip..."
sudo apt-get install -y python3 python3-pip python3-venv

# Set Timezone to IST (Optional, useful for logs)
echo "Setting timezone to Asia/Kolkata..."
sudo timedatectl set-timezone Asia/Kolkata

# Install Python Dependencies
echo "Installing Python dependencies..."
# Using --break-system-packages because we are in a VM dedicated to this bot
# Alternatively, we could use a venv, but this is simpler for a single-purpose VM.
pip3 install flask pandas numpy requests pytz --break-system-packages

echo "Setup complete! You can now run your bot."
