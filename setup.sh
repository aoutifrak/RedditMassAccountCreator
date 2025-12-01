# 1. Install dependencies
sudo apt update -y &&
apt-get install -y docker.io python3 python3-full chromium xvfb git
sudo systemctl start docker
sudo usermod -aG docker $USER

# add docker to sudoers
echo "$USER ALL=(ALL) NOPASSWD: /usr/bin/docker" | sudo tee /etc/sudoers.d/$USER-docker

# clone repo
git clone https://github.com/aoutifrak/RedditMassAccountCreator.git
cd RedditMassAccountCreator
# 2. Setup Python packages
python3 -m venv venv
source venv/bin/activate
pip3 install -r requirements.txt

# 4. Make executable
chmod +x register.py run.sh stop.sh

# 5. Test single instance
# python3 register.py --instance 1

# 6. Run 3 instances in parallel
./run.sh 2