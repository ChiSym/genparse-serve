#!/bin/bash

# Check if the user has provided the WorkingDirectory path, and conda environment
if [ -z "$1" ]; then
  echo "Usage: $0 <conda_environment>"
  exit 1
fi

# Assign the provided arguments to variables
WORKING_DIRECTORY="$(dirname "$(dirname "$(realpath "$0")")")/src/genparse_server"
USER=$USER
CONDA_ENVIRONMENT=$1

# Define the log directory path
LOG_DIRECTORY=$WORKING_DIRECTORY/log

# Create the log directory if it doesn't exist
if [ ! -d "$LOG_DIRECTORY" ]; then
  sudo mkdir -p $LOG_DIRECTORY
  sudo chown $USER:$USER $LOG_DIRECTORY
fi

# Define the service file path
SERVICE_FILE_PATH="/etc/systemd/system/genparse-server-app.service"

# Create the service file with the desired content
sudo tee $SERVICE_FILE_PATH > /dev/null <<EOL
[Unit]
Description=GenParse Server
After=network.target

[Service]
User=$USER
WorkingDirectory=$WORKING_DIRECTORY
Environment="PATH=$CONDA_ENVIRONMENT/bin"
ExecStart=$CONDA_ENVIRONMENT/bin/python $WORKING_DIRECTORY/app.py
Restart=on-failure
StandardOutput=append:$LOG_DIRECTORY/genparse-service.log
StandardError=append:$LOG_DIRECTORY/genparse-service-error.log

[Install]
WantedBy=multi-user.target
EOL

# Reload the systemd manager configuration
sudo systemctl daemon-reload

# Enable the service to start on boot
sudo systemctl enable genparse-server-app.service

# Start the service
sudo systemctl start genparse-server-app.service

echo "GenParse service created and started successfully."