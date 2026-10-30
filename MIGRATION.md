# Переезд бота с SQLite на PostgreSQL

> **Выкачено 30.10.2026 в 20:39 UTC**, коммит 7d9419b с курсом «Перекус». Бот стоял около секунды. Финальный перенос сошёлся по всем таблицам: 15 пользователей, 159 попыток. После засева нового каталога попыток 149, как и ожидалось. Админка теперь только на 127.0.0.1:8080, оффер выключен (`OFFER_ENABLED=false`).
>
> Для отката на сервере лежат:
> - старая папка `/home/deploy/apps/stepik-killer-sqlite`;
> - финальная копия SQLite `~/backups/stepik_killer-final-2026-10-30-2039.db`;
> - дамп Postgres до засева нового каталога `~/backups/pg-before-catalog-2026-10-30-2039.sql.gz`.
>
> **Не запускай `deploy.sh`, пока `origin/main` не обновлён до этой ветки:** он сбросит код на старый `main`.

Выкатываешь сам, руками по этой инструкции. На сервере я только читал: pm2, одну строку `DB_PATH` из `.env`, список файлов, логи. Ничего не останавливал, не перезапускал и не записывал. Базу скачал копией через `scp`.

## Прогон на копии прода

Источник — копия `/home/deploy/apps/stepik-killer/stepik_killer.db` от 30.10, 23:21 МСК, 340 КБ. Последняя попытка в ней — 30.10 в 08:57 UTC. Целостность SQLite в порядке. Схема совпадает с той, на которую рассчитан скрипт: все 8 таблиц, все колонки, лишних таблиц нет.

Перенос в пустую базу, два запуска подряд, оба с кодом 0. Отчёт второго запуска:

| Таблица | В SQLite | Перенесено | Битые ссылки | В Postgres | Лишних в PG | Число | Содержимое |
|---|---|---|---|---|---|---|---|
| users | 15 | 15 | 0 | 15 | 0 | ✓ | ✓ |
| modules | 4 | 4 | 0 | 4 | 0 | ✓ | ✓ |
| topics | 8 | 8 | 0 | 8 | 0 | ✓ | ✓ |
| personal_sets | 2 | 2 | 0 | 2 | 0 | ✓ | ✓ |
| personal_set_access | 4 | 4 | 0 | 4 | 0 | ✓ | ✓ |
| tasks | 74 | 74 | 0 | 74 | 0 | ✓ | ✓ |
| catalog_meta | 1 | 1 | 0 | 1 | 0 | ✓ | ✓ |
| solutions | 159 | 159 | 0 | 159 | 0 | ✓ | ✓ |

Новые колонки в `users` (источник, оффер) получили значения по умолчанию.

После переноса я дважды прогнал запуск бота, то есть сидинг каталога и личных блоков. Результат:
- все 159 решений остались на тех же задачах;
- личные блоки Александра не задвоились;
- в админке 15 учеников и 159 попыток.

У 11 из 15 пользователей телеграм-id больше int32, поэтому в Postgres колонка `id_tg` — BigInteger.

### Что делает скрипт

`scripts/migrate_sqlite_to_pg.py`:

- **Открывает SQLite только на чтение.** Подходят и старые схемы, недостающие колонки получают значения по умолчанию.
- **Сохраняет id.** Пишет через upsert по первичному ключу, поэтому повторный запуск ничего не дублирует.
- **Не теряет битые строки.** Решения на удалённые задачи складывает в `<отчёт>.orphans.json`. На проде таких сейчас нет.
- **Отказывается писать в базу с чужими строками.** Например, если бот уже стартовал на пустом Postgres и залил каталог с другими id.
- **Сверяет каждую таблицу** по числу строк и по хешу содержимого. Код выхода 0 только если всё сошлось.
- **Сдвигает счётчики id** за максимум в источнике.

## Что нашёл на сервере

- **Бот лежал с 24 по 29 октября.** Telegram отклонял токен, бот падал на первом же запросе, pm2 перезапустил его 131 066 раз. 29.10 в 19:08 бот пересоздали, с тех пор он работает. В папке остался `.env.bak-2026-10-29`. Новый обработчик ошибок такое не ловит: падение происходит до старта бота.
- **Лог ошибок pm2 весит 864 МБ, и в нём открытым текстом лежит старый токен.** Telegram его уже отклоняет, но лог лучше почистить и включить ротацию:
  ```bash
  pm2 flush stepik-killer && pm2 install pm2-logrotate
  ```
- **Админка сейчас открыта в интернет.** Порт 8080 слушает этот же бот на `0.0.0.0`, то есть HTTP с паролем без шифрования. После переезда она будет только на `127.0.0.1`.
- **Порт 5434 занят** Postgres другого бота (`workout_bot`). Поэтому ниже база на **5435**.
- **`sqlite3` на сервере нет.** Копии базы ниже делаются через Python, он там есть.
- Docker 29.6, compose v5.3, Python 3.12, свободно 20 ГБ, образ песочницы уже скачан. Бот стоит на `main` с коммитом 6b5c5e3.

## Перед началом

0. Запушить ветку `personal-tasks` в `origin`. Я её не пушил, а шаг 1 клонирует её на сервер.

**Не вливай `personal-tasks` в `main` до шага 9.** Теперь `deploy.sh` сам поднимает Postgres и накатывает миграции. Если он отработает раньше переноса, бот стартует на пустой базе. Тогда базу придётся пересоздать, см. конец шага 4.

## Подготовка: бот работает, простоя нет

Дальше все команды выполняются на сервере, после `ssh deploy@193.233.136.221`.

1. Новая копия кода рядом со старой:
   ```bash
   cd /home/deploy/apps && git clone "$(git -C stepik-killer remote get-url origin)" stepik-killer-new -b personal-tasks
   ```
   ```bash
   cd /home/deploy/apps/stepik-killer-new && python3 -m venv env && ./env/bin/pip install -q -r requirements.txt
   ```

2. Настройки. Берём рабочий `.env` и дописываем базу со случайным паролем:
   ```bash
   cp /home/deploy/apps/stepik-killer/.env /home/deploy/apps/stepik-killer-new/.env
   ```
   ```bash
   PASS=$(openssl rand -hex 16) && printf 'POSTGRES_USER=stepik\nPOSTGRES_PASSWORD=%s\nPOSTGRES_DB=stepik_killer\nPOSTGRES_PORT=5435\nDATABASE_URL=postgresql+asyncpg://stepik:%s@127.0.0.1:5435/stepik_killer\nADMIN_HOST=127.0.0.1\n' "$PASS" "$PASS" >> /home/deploy/apps/stepik-killer-new/.env
   ```
   **`TRIAL_URL` — черновик**, допиши настоящую ссылку на пробный урок. Остальные новые переменные необязательны, значения по умолчанию в `.env.example`.

3. Postgres и схема:
   ```bash
   cd /home/deploy/apps/stepik-killer-new && docker compose up -d db && until docker compose exec -T db pg_isready -q; do sleep 1; done
   ```
   ```bash
   ./env/bin/python -m alembic upgrade head
   ```

4. Пробный перенос на свежей копии. Бот продолжает работать. Копия через Python безопасна на живой базе:
   ```bash
   mkdir -p ~/backups && python3 -c "import sqlite3; sqlite3.connect('/home/deploy/apps/stepik-killer/stepik_killer.db').backup(sqlite3.connect('$HOME/backups/stepik_killer-dry.db'))"
   ```
   ```bash
   ./env/bin/python -m scripts.migrate_sqlite_to_pg ~/backups/stepik_killer-dry.db --report ~/backups/dry_report.md
   ```
   Смотри итог: должно быть «всё сошлось».

   После пробы базу обнуляем. Финальный перенос пишет только в пустую базу:
   ```bash
   docker compose exec -T db sh -c 'dropdb -U "$POSTGRES_USER" "$POSTGRES_DB" && createdb -U "$POSTGRES_USER" "$POSTGRES_DB"' && ./env/bin/python -m alembic upgrade head
   ```

## Переключение: простой 2–5 минут

5. Остановить бота и снять финальную копию:
   ```bash
   pm2 stop stepik-killer
   ```
   ```bash
   F=$HOME/backups/stepik_killer-final-$(date +%F-%H%M).db && python3 -c "import sqlite3; sqlite3.connect('/home/deploy/apps/stepik-killer/stepik_killer.db').backup(sqlite3.connect('$F'))" && echo $F
   ```

6. Перенос. Должно быть «всё сошлось» и код выхода 0. Вместо `<файл>` подставь путь, который напечатал шаг 5:
   ```bash
   cd /home/deploy/apps/stepik-killer-new && ./env/bin/python -m scripts.migrate_sqlite_to_pg <файл> --report ~/backups/final_report.md; echo "exit=$?"
   ```
   Если код не 0, бота на Postgres не запускай. Верни старый: `pm2 start stepik-killer`.

7. Подменить папки и запустить. Состояние диалогов, то есть у кого какая задача открыта, переносим. pm2 запускает бота по абсолютному пути `/home/deploy/apps/stepik-killer/main.py` с `env/bin/python` оттуда же, так что после подмены поднимется новый код:
   ```bash
   cd /home/deploy/apps && cp stepik-killer/conversation_state.pkl stepik-killer-new/ 2>/dev/null; mv stepik-killer stepik-killer-sqlite && mv stepik-killer-new stepik-killer
   ```
   ```bash
   cd /home/deploy/apps/stepik-killer && pm2 restart stepik-killer --update-env && pm2 logs stepik-killer --lines 50
   ```
   В логах не должно быть трейсов.

## Проверка

8. В Telegram со своего аккаунта:
   - `/start` открывает меню, прогресс и уровень на месте;
   - «Следующая задача», затем заведомо неверный код. Тесты приходят сразу, разнос дописывается в то же сообщение через 10–15 секунд;
   - код с `open('tests.json')` падает с `FileNotFoundError`, а не проходит.

   С чужого аккаунта: `/start reel_test` сразу показывает задачу. Это первая из `config/starter.py`, а при пустом списке первая задача каталога.

   Админка через ssh-туннель, порт наружу больше не открыт:
   ```bash
   ssh -L 8080:127.0.0.1:8080 deploy@193.233.136.221
   ```
   Открой http://localhost:8080. Там должно быть 15 учеников, а в `/funnel` — источник `reel_test`. Снаружи `http://193.233.136.221:8080` открываться больше не должен.

9. Всё работает — вливай `personal-tasks` в `main`. После этого `deploy.sh` снова годится для выкаток.

## Откат на SQLite

После шага 5 SQLite-файл никто не трогал, он лежит в `/home/deploy/apps/stepik-killer-sqlite`.

```bash
pm2 stop stepik-killer && cd /home/deploy/apps && mv stepik-killer stepik-killer-pg && mv stepik-killer-sqlite stepik-killer && pm2 restart stepik-killer --update-env
```

Потеряется только то, что ученики успели сделать после переключения: обратного переноса нет. Postgres-контейнер боту на SQLite не мешает. Остановить его: `cd /home/deploy/apps/stepik-killer-pg && docker compose stop db`. Откатываться только подменой папок: старый код не знает про новые колонки.

## Слияние с веткой каталога `claude/course-rework-ad51f8`

Курс «Перекус» живёт в отдельной ветке, она ответвилась от этой после перевода на Postgres (f8bfca9). Порядок такой: **сначала эта ветка и переезд по шагам выше, потом каталог.** Сливаешь руками. Я ничего не сливал.

**1. Миграции.** У обеих веток своя «002», и обе идут от `001_initial`:

| Ветка | Цепочка |
|---|---|
| `personal-tasks` | `001_initial` → `002_onboarding` → `003_offer` |
| `course-rework` | `001_initial` → `002_difficulty_1_5` |

Без правки у Alembic будет две ветки миграций, и `alembic upgrade head` упадёт с «Multiple head revisions». Перенумеровать нужно миграцию каталога: мои 002 и 003 к тому моменту уже будут на проде. Номер 003 занят, поэтому каталог получает 004:

- файл `alembic/versions/002_difficulty_1_5.py` переименовать в `004_difficulty_1_5.py`;
- в нём `revision = "004_difficulty_1_5"` и `down_revision = "003_offer"`, в docstring так же.

**2. Текстовых конфликтов нет.** Я проверил это слиянием в памяти через `git merge-tree`, ветки не трогал. С перенумерацией из пункта 1 у Alembic одна голова, все 33 теста проходят на новом каталоге. После настоящего слияния проверь то же:
```bash
.venv/bin/python -m alembic heads && .venv/bin/python -m alembic check && .venv/bin/python -m pytest -q
```

**3. Перед выкаткой каталога сделай бэкап Postgres.** Команда в разделе «После переезда».

**4. Это решаешь ты.** Новый сидинг меняет данные учеников. Посчитал на копии прода:

| Что произойдёт | Задач | Попыток |
|---|---|---|
| Ключ остаётся, но задача под ним другая. Решения горят 🔄, в админке старый код висит под новым условием | 18 | 147 |
| Задача удаляется, попытки удаляются вместе с ней каскадом | 7 | 10, все у одного ученика на «Минутах в часы» |
| Личные задачи, их сидинг не трогает | — | 2 |

Если историю попыток нужно сохранить целиком, это правка в ветке каталога: например, старые задачи не удалять, а скрывать из меню. Решить нужно до выкатки.

**5. Стартовый набор.** После выкатки каталога заполни `config/starter.py` ключами новых задач. Иначе новичок начнёт с 01-01-01.

## После переезда

- `stepik-killer-sqlite` и бэкапы в `~/backups` держи хотя бы неделю.
- Бэкап Postgres, стоит повесить в cron раз в сутки:
  ```bash
  cd /home/deploy/apps/stepik-killer && docker compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' | gzip > ~/backups/pg-$(date +%F).sql.gz
  ```
