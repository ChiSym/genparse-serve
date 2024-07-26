#!/bin/bash

# Check if the user has provided the WorkingDirectory path, user, and conda environment
if [ -z "$1" ] || [ -z "$2" ] || [ -z "$3" ]; then
  echo "Usage: $0 <working_directory> <user> <conda_environment>"
  exit 1
fi

# Assign the provided arguments to variables
WORKING_DIRECTORY=$1
USER=$2
CONDA_ENVIRONMENT=$3

# Define the log directory path
LOG_DIRECTORY=$WORKING_DIRECTORY/log

# Create the log directory if it doesn't exist
if [ ! -d "$LOG_DIRECTORY" ]; then
  sudo mkdir -p $LOG_DIRECTORY
  sudo chown $USER:$USER $LOG_DIRECTORY
fi

# Define the service file path
SERVICE_FILE_PATH="/etc/systemd/system/genparse-flask-app.service"

# Create the service file with the desired content
sudo tee $SERVICE_FILE_PATH > /dev/null <<EOL
[Unit]
Description=GenParse Flask Application
After=network.target

[Service]
User=$USER
WorkingDirectory=$WORKING_DIRECTORY
Environment="PATH=$CONDA_ENVIRONMENT/bin"
ExecStart=$CONDA_ENVIRONMENT/bin/python $WORKING_DIRECTORY/app.py
Restart=always
RestartSec=3
StandardOutput=append:$LOG_DIRECTORY/genparse-service.log
StandardError=append:$LOG_DIRECTORY/genparse-service-error.log

[Install]
WantedBy=multi-user.target
EOL

# Reload the systemd manager configuration
sudo systemctl daemon-reload

# Enable the service to start on boot
sudo systemctl enable genparse-flask-app.service

# Start the service
sudo systemctl start genparse-flask-app.service

echo "Service created and started successfully."