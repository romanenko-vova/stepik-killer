#!/bin/sh
# крутится на сервере: подтягивает main с GitHub и рестартит бота
# .env и env/ не трогаются; схема базы догоняется миграциями
set -e
cd "$(dirname "$0")"

git fetch origin
git reset --hard origin/main
./env/bin/pip install -q -r requirements.txt

# база в docker — поднимаем, если лежит, и ждём готовности
docker compose up -d db
until docker compose exec -T db pg_isready -q; do sleep 1; done
# через python -m: у скриптов в env/bin абсолютный путь, после переноса папки они ломаются
./env/bin/python -m alembic upgrade head

export NVM_DIR="$HOME/.nvm"
. "$NVM_DIR/nvm.sh"
pm2 restart stepik-killer
