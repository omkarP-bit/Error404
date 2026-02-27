#!/bin/bash
# Run this on a cloud server (AWS EC2, DigitalOcean, etc.)

# Install squid proxy
sudo apt update
sudo apt install squid -y

# Configure squid
sudo bash -c 'cat > /etc/squid/squid.conf << EOF
http_port 3128
acl allowed_ips src YOUR_LOCAL_IP/32
http_access allow allowed_ips
http_access deny all
EOF'

# Restart squid
sudo systemctl restart squid
sudo systemctl enable squid

echo "Proxy running on port 3128"
echo "Use: HTTPS_PROXY=http://SERVER_IP:3128"
