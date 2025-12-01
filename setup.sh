#!/bin/bash
# Setup script for Reddit Register VPS
# Usage: ./setup.sh 

#setup docker for debian vps and add user to docker group
sudo apt-get update
sudo apt-get install -y docker.io docker-compose xvfb python3-full 
sudo usermod -aG docker $USER

# clone repo if not already present
git clone https://github.com/aoutifrak/RedditMassAccountCreator.git
cd RedditMassAccountCreator/
# setup python environment
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
playwright install --with-deps firefox
# run reddit registration script
xvfb-run -a python3 reddit_register.py --instance 1

echo "Setup complete! Please log out and back in for docker group changes to take effect."