#!/bin/bash

# Check if the user has provided the WorkingDirectory path and conda environment
if [ -z "$1" ]; then
  echo "Usage: $0 <conda_environment>"
  exit 1
fi

# Assign the provided arguments to variables
WORKING_DIRECTORY="$(dirname "$(dirname "$(realpath "$0")")")/src/restart_service_app"
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
SERVICE_FILE_PATH="/etc/systemd/system/restart-service-app.service"

# Create the service file with the desired content
sudo tee $SERVICE_FILE_PATH > /dev/null <<EOL
[Unit]
Description=GenParse Server Restart Application
After=network.target

[Service]
User=$USER
WorkingDirectory=$WORKING_DIRECTORY
Environment="PATH=$CONDA_ENVIRONMENT/bin"
Environment="USERNAME=genparser"
Environment="PASSWORD=earley"
ExecStart=$CONDA_ENVIRONMENT/bin/python $WORKING_DIRECTORY/app.py
Restart=on-failure
StandardOutput=append:$LOG_DIRECTORY/genparse-restart-service.log
StandardError=append:$LOG_DIRECTORY/genparse-restart-service.log

[Install]
WantedBy=multi-user.target
EOL

# Reload the systemd manager configuration
sudo systemctl daemon-reload

# Enable the service to start on boot
sudo systemctl enable restart-service-app.service

# Start the service
sudo systemctl start restart-service-app.service

echo "Restart service created and started successfully."