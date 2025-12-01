#!/usr/bin/env bash

# create new user
sudo adduser --disabled-password --gecos "" reddituser
sudo usermod -aG sudo reddituser

# 1. Install dependencies (run as root so no password prompt appears later)
sudo apt update -y
sudo apt-get install -y docker.io python3 python3-venv python3-pip chromium xvfb git

# start docker and add reddituser to docker group
sudo systemctl start docker
sudo usermod -aG docker reddituser

# allow reddituser to run docker without password for the docker binary only
echo "reddituser ALL=(ALL) NOPASSWD: /usr/bin/docker" | sudo tee /etc/sudoers.d/reddituser-docker
sudo -u reddituser
# clone repo and setup python environment as reddituser (no interactive su)
sudo -u reddituser -H bash -lc '
cd ~
if [ ! -d RedditMassAccountCreator ]; then
  git clone https://github.com/aoutifrak/RedditMassAccountCreator.git
fi
cd RedditMassAccountCreator
python3 -m venv venv
# shellcheck disable=SC1091
. venv/bin/activate
pip install -r requirements.txt
chmod +x register.py run.sh stop.sh
'

# To run the app as reddituser:
sudo -u reddituser -H bash -lc 'cd ~/RedditMassAccountCreator && . venv/bin/activate && ./run.sh 2'