# Переезд бота с SQLite на PostgreSQL

Выкатывает пользователь руками по этой инструкции. Я на прод ничего не деплоил и бота не останавливал.

## Что проверено, а что нет

**Копию прод-базы я снять не смог.** Права Claude Code заблокировали и `ssh`, и `scp` на `deploy@193.233.136.221`. Поэтому прогон ниже сделан на локальной SQLite из репозитория. Это снимок от 24.09: 1 пользователь, 17 попыток, схема ещё без личных блоков.

Схему как на проде сейчас, с личными блоками, телеграм-id больше int32 и решениями на удалённые задачи, проверяет автотест `tests/test_migration.py`. Он гоняет перенос дважды и сверяет данные.

Первый шаг процедуры ниже — пробный прогон на копии прода. Он покажет настоящие цифры до остановки бота.

### Прогон на локальной копии

Источник `_archive/stepik_killer.db`, пустая база, два запуска подряд. Оба завершились с кодом 0. Отчёт второго запуска:

| Таблица | В SQLite | Перенесено | Битые ссылки | В Postgres | Лишних в PG | Число | Содержимое |
|---|---|---|---|---|---|---|---|
| users | 1 | 1 | 0 | 1 | 0 | ✓ | ✓ |
| modules | 4 | 4 | 0 | 4 | 0 | ✓ | ✓ |
| topics | 8 | 8 | 0 | 8 | 0 | ✓ | ✓ |
| personal_sets | 0 | 0 | 0 | 0 | 0 | ✓ | ✓ |
| personal_set_access | 0 | 0 | 0 | 0 | 0 | ✓ | ✓ |
| tasks | 61 | 61 | 0 | 61 | 0 | ✓ | ✓ |
| catalog_meta | 1 | 1 | 0 | 1 | 0 | ✓ | ✓ |
| solutions | 17 | 17 | 0 | 17 | 0 | ✓ | ✓ |

Таблиц личных блоков в этом снимке ещё не было, новые колонки получили значения по умолчанию. После переноса я запустил сидинг каталога, как при старте бота. Все 17 решений остались на тех же задачах, ни одна задача не сменила id.

### Что делает скрипт

`scripts/migrate_sqlite_to_pg.py`:

- **Читает SQLite только на чтение.** Подходят старые схемы, недостающие колонки получают значения по умолчанию.
- **Сохраняет id.** Пишет через upsert по первичному ключу, поэтому повторный запуск ничего не дублирует.
- **Не теряет битые строки.** SQLite не проверял внешние ключи, и там могут лежать решения на удалённые задачи. Postgres их не примет. Скрипт складывает их в `<отчёт>.orphans.json` и считает отдельной колонкой.
- **Отказывается писать в базу с чужими строками.** Если бот уже стартовал на пустом Postgres и засидил каталог, id разойдутся. Тогда скрипт остановится с объяснением.
- **Сверяет каждую таблицу двумя способами:** по числу строк и по хешу содержимого общих колонок. Код выхода 0 только если всё сошлось.
- **Двигает счётчики id** дальше максимума в источнике, включая битые строки.

## Перед началом

- На сервере есть Docker с плагином compose. Песочница уже его использует, проверь `docker compose version`.
- Python для `env/` не ниже 3.10: `python3 --version`.
- Ниже путь бота везде `~/stepik-killer`. Я его не видел, поправь, если он другой.
- Посмотри, как бот запущен в pm2: `pm2 describe stepik-killer`. Запомни script, interpreter и cwd. Ниже предполагается `env/bin/python main.py` из папки бота.

**Не вливай `personal-tasks` в `main` до шага 9.** `deploy.sh` теперь сам поднимает Postgres и накатывает миграции. Если он отработает раньше переноса, бот стартует на пустой базе. Тогда базу придётся пересоздать, см. шаг 4.

## Подготовка: бот работает, простоя нет

1. Новая копия кода рядом со старой:
   ```bash
   cd ~ && git clone "$(git -C ~/stepik-killer remote get-url origin)" stepik-killer-new -b personal-tasks
   ```
   ```bash
   cd ~/stepik-killer-new && python3 -m venv env && ./env/bin/pip install -q -r requirements.txt
   ```

2. Настройки. Берём старый `.env` и дописываем базу со случайным паролем:
   ```bash
   cp ~/stepik-killer/.env ~/stepik-killer-new/.env
   ```
   ```bash
   PASS=$(openssl rand -hex 16) && printf 'POSTGRES_USER=stepik\nPOSTGRES_PASSWORD=%s\nPOSTGRES_DB=stepik_killer\nPOSTGRES_PORT=5434\nDATABASE_URL=postgresql+asyncpg://stepik:%s@127.0.0.1:5434/stepik_killer\n' "$PASS" "$PASS" >> ~/stepik-killer-new/.env
   ```
   Остальные новые переменные необязательны, значения по умолчанию в `.env.example`. **`TRIAL_URL` — черновик**, поставь настоящую ссылку на пробный урок. Нужен `ADMIN_PASSWORD`, иначе админка не стартует.

3. Postgres и схема:
   ```bash
   cd ~/stepik-killer-new && docker compose up -d db && until docker compose exec -T db pg_isready -q; do sleep 1; done
   ```
   ```bash
   ./env/bin/python -m alembic upgrade head
   ```

4. Пробный перенос на свежей копии. Бот продолжает работать, `.backup` в SQLite безопасен на живой базе:
   ```bash
   mkdir -p ~/backups && sqlite3 ~/stepik-killer/stepik_killer.db ".backup $HOME/backups/stepik_killer-dry.db"
   ```
   ```bash
   ./env/bin/python -m scripts.migrate_sqlite_to_pg ~/backups/stepik_killer-dry.db --report ~/backups/dry_report.md
   ```
   Смотри итог: должно быть «всё сошлось». Если есть битые ссылки, загляни в `~/backups/dry_report.orphans.json`. Это решения на задачи, удалённые раньше. Они в боте и так не видны.

   После пробы базу обнуляем. Финальный перенос пишет только в пустую базу, иначе строки, удалённые в SQLite за это время, остались бы в Postgres:
   ```bash
   docker compose exec -T db sh -c 'dropdb -U "$POSTGRES_USER" "$POSTGRES_DB" && createdb -U "$POSTGRES_USER" "$POSTGRES_DB"' && ./env/bin/python -m alembic upgrade head
   ```

5. Образ песочницы заранее, чтобы первая проверка после старта не ждала скачивания:
   ```bash
   docker pull python:3.12-slim
   ```

## Переключение: простой 2–5 минут

6. Остановить бота и снять финальную копию:
   ```bash
   pm2 stop stepik-killer
   ```
   ```bash
   sqlite3 ~/stepik-killer/stepik_killer.db ".backup $HOME/backups/stepik_killer-final-$(date +%F-%H%M).db"
   ```

7. Перенос. Должно быть «всё сошлось» и код выхода 0:
   ```bash
   cd ~/stepik-killer-new && ./env/bin/python -m scripts.migrate_sqlite_to_pg ~/backups/stepik_killer-final-*.db --report ~/backups/final_report.md; echo "exit=$?"
   ```
   Если не 0 — бота на Postgres не запускай. Верни старого `pm2 start stepik-killer` и разбирайся с отчётом.

8. Подменить папки и запустить. Состояние диалогов, то есть кто какую задачу открыл, переносим:
   ```bash
   cp ~/stepik-killer/conversation_state.pkl ~/stepik-killer-new/ 2>/dev/null; mv ~/stepik-killer ~/stepik-killer-sqlite && mv ~/stepik-killer-new ~/stepik-killer
   ```
   ```bash
   cd ~/stepik-killer && pm2 restart stepik-killer --update-env && pm2 logs stepik-killer --lines 50
   ```
   В логах не должно быть трейсов. Сидинг каталога и личных блоков проходит при старте сам.

## Проверка

9. В Telegram со своего аккаунта:
   - `/start` открывает меню, прогресс и уровень на месте;
   - «Следующая задача» → прислать заведомо неверный код. Тесты приходят сразу, разнос дописывается через 10–15 секунд;
   - тот же код с `open('tests.json')` падает с `FileNotFoundError`, а не проходит.

   С нового аккаунта или с аккаунта друга: `/start reel_test` сразу показывает первую задачу. Это первая из `config/starter.py`, а если список пуст, первая задача каталога.

   Админка по ssh-туннелю. Наружу порт больше не торчит:
   ```bash
   ssh -L 8080:127.0.0.1:8080 deploy@193.233.136.221
   ```
   Открыть http://localhost:8080. Число учеников и попыток совпадает с отчётом. В `/funnel` виден источник `reel_test`.

   Всё работает — вливай `personal-tasks` в `main`. После этого `deploy.sh` снова годится для выкаток.

## Откат на SQLite

SQLite-файл после шага 6 никто не трогал, он лежит в `~/stepik-killer-sqlite`.

```bash
pm2 stop stepik-killer && mv ~/stepik-killer ~/stepik-killer-pg && mv ~/stepik-killer-sqlite ~/stepik-killer && cd ~/stepik-killer && pm2 restart stepik-killer --update-env
```

Потеряется только то, что ученики успели сделать на Postgres после переключения. Обратного переноса нет. Если откат через минуты, это несколько попыток. Postgres-контейнер можно оставить: бот на SQLite его не использует. Остановить: `cd ~/stepik-killer-pg && docker compose stop db`.

Старый код стоит на SQLite и не знает про новые колонки. Поэтому откатываться нужно именно подменой папок, а не `git checkout` в новой.

## После переезда

- `~/stepik-killer-sqlite` и бэкапы в `~/backups` держи хотя бы неделю.
- Бэкап Postgres:
  ```bash
  cd ~/stepik-killer && docker compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' | gzip > ~/backups/pg-$(date +%F).sql.gz
  ```
  Стоит повесить в cron раз в сутки.
