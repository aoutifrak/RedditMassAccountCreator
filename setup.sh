# 1. Install dependencies
sudo apt-get install -y docker.io python3 python3-pip chromium-browser
sudo systemctl start docker
sudo usermod -aG docker $USER

# 2. Setup Python packages
cd reddit-register-vps
pip3 install -r requirements.txt

# 3. Edit credentials
nano config.json  # Set NordVPN email/password

# 4. Make executable
chmod +x register.py run.sh stop.sh

# 5. Test single instance
python3 register.py --instance 1

# 6. Run 3 instances in parallel
./run.sh 3