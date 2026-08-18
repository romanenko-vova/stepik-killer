#!/bin/sh
# крутится на сервере: подтягивает main с GitHub и рестартит бота
# .env, env/ и база не трогаются
set -e
cd "$(dirname "$0")"

git fetch origin
git reset --hard origin/main

export NVM_DIR="$HOME/.nvm"
. "$NVM_DIR/nvm.sh"
pm2 restart stepik-killer
