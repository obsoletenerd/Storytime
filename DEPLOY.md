# Deploying to a Raspberry Pi (or any Linux web-server)

Flash the `Raspberry Pi OS Lite` image to your Pi using the [Raspberry Pi Imager](https://www.raspberrypi.com/software/). Make sure you set up the WiFi and SSH details so you can log into the Pi remotely after flashing or you'll have to plug the Pi into a monitor/keyboard/mouse and do it that way.

When it has finished flashing, plug the Pi in and give it a few minutes to do the first-boot stuff, then it should show up on your network and you can log in via SSH to do the following steps.

## Update and Install Supporting Packages

```bash
# Update the system
sudo apt update && sudo apt upgrade -y

# Install essential packages
sudo apt install -y python3-pip python3-venv nginx git

# Install Ollama (if you want local LLM support)
curl -fsSL https://ollama.ai/install.sh | sh
```

## Download the Application and Install Dependencies

First get the application code and get it ready to be served

```bash
# Clone the project from the Github repository
cd ~/
git clone https://github.com/obsoletenerd/Storytime.git
cd Storytime

# Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate

# Install the application dependencies
pip install -r requirements.txt

# Install Gunicorn for serving the Flask application in production
pip install gunicorn
```

Create the local .env file that doesn't come with the repository

```bash
nano .env
```

Put your API keys inside it. You at minimum need the OpenAI one if you want image generation with the stories, then whichever other LLMs you want for the text generation.

```bash
# Required for image generation and for ChatGPT-generated stories
OPENAI_API_KEY=your_key_here

# If you're using Ollama then put the host and model here for it to show up as an option
OLLAMA_HOST = http://localhost:11434 # or the IP of your Ollama server
OLLAMA_MODEL = mistral:latest

# Optional other LLMs for story generation
MISTRAL_API_KEY=your_key_here
ANTHROPIC_API_KEY=your_key_here
```

Create a Systemd service that will manage running the Flask application

```bash
sudo nano /etc/systemd/system/storytime.service
```

Put this content in that file but adjust the paths as necessary if you changed any of them

```ini
[Unit]
Description=Bedtime Stories Flask App
After=network.target

[Service]
User=storytime
Group=storytime
WorkingDirectory=/home/storytime/Storytime
Environment=PATH=/home/storytime/Storytime/venv/bin
EnvironmentFile=/home/storytime/Storytime/.env
ExecStart=/home/storytime/Storytime/venv/bin/gunicorn -c gunicorn.conf.py app:app
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

Configure nginx as the webserver by creating an nginx config file

```bash
sudo nano /etc/nginx/sites-available/storytime
```

Add this contents to the file:

```nginx
server {
    listen 80;
    server_name _;  # Accept any hostname

    client_max_body_size 16M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
        proxy_connect_timeout 120s;
        proxy_send_timeout 120s;
    }
}
```

Enable the nginx site:

```bash
sudo ln -s /etc/nginx/sites-available/storytime /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default  # Remove default site
sudo nginx -t  # Test configuration
```

You should see

```bash
nginx: the configuration file /etc/nginx/nginx.conf syntax is ok
nginx: configuration file /etc/nginx/nginx.conf test is successful
```

Start everything up!
```bash
# Start and enable your Flask app service
sudo systemctl daemon-reload
sudo systemctl enable storytime
sudo systemctl start storytime

# Start and enable Nginx
sudo systemctl enable nginx
sudo systemctl start nginx

# If using Ollama locally
sudo systemctl enable ollama
sudo systemctl start ollama

# Pull a model for Ollama (optional)
ollama pull mistral:latest
```

Check status:

```bash
# Check your Flask app
sudo systemctl status storytime

# Check Nginx
sudo systemctl status nginx

# Check logs if needed
sudo journalctl -u storytime -f  # Follow Flask app logs
sudo tail -f /var/log/nginx/error.log   # Nginx error logs
```

Useful management commands:

```bash
# Restart your app after code changes
git pull  # Get latest code
sudo systemctl restart storytime

# View logs
sudo journalctl -u storytime --since today

# Stop/start services
sudo systemctl stop storytime
sudo systemctl start storytime
```
