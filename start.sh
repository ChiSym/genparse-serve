#!/bin/bash

if [ -z "$1" ]; then
  echo "Usage: $0 <conda_environment>"
  exit 1
fi

sh scripts/init_genparse_service.sh $1
sh scripts/init_restart_service.sh $1