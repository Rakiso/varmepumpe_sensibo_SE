#!/bin/bash
# Update system and install dependencies
sudo apt-get update && sudo apt-get upgrade -y
sudo apt-get install -y python3-pip python3-venv nginx git

# Clone and setup application
git clone https://github.com/rakiso/varmepumpe_kontroll.git
cd varmepumpe_kontroll

# Setup Python environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Setup Nginx configuration
sudo tee /etc/nginx/sites-available/varmepumpe << EOF
server {
    listen 80;
    server_name \$host;
    
    location / {
        proxy_pass http://localhost:5001;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }
}
EOF

sudo ln -sf /etc/nginx/sites-available/varmepumpe /etc/nginx/sites-enabled
sudo nginx -t && sudo systemctl restart nginx

# Setup systemd service
sudo tee /etc/systemd/system/varmepumpe.service << EOF
[Unit]
Description=Varmepumpe Control System
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/varmepumpe_kontroll
Environment="PATH=/home/ubuntu/varmepumpe_kontroll/venv/bin"
ExecStart=/home/ubuntu/varmepumpe_kontroll/venv/bin/gunicorn --workers 4 --bind 127.0.0.1:5001 app:app
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl enable varmepumpe
sudo systemctl start varmepumpe