#!/bin/bash

sudo systemctl stop genparse-server-app.service
sudo systemctl stop restart-service-app.service

echo "Stopped services"