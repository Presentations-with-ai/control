# PC Telegram Relay — AGENT ZIP

Это ZIP только для удалённых ПК: ноутбук, офисный ПК, домашний второй ПК и т.д.

Agent ПК:
- запускает своего agent-бота;
- ждёт команды через Telegram;
- выполняет команды;
- отправляет результат твоему Telegram-аккаунту;
- если main ПК выключен, agent всё равно продолжает работать и ждать команды;
- если интернет/Telegram временно упал, agent каждые 10 секунд пытается снова запустить polling.

## Установка

Распакуй, например:

```text
C:\pc_relay_agent
```

Запусти:

```bat
install_agent_windows.bat
```

Он:
- проверит/установит Python;
- создаст `.venv`;
- установит библиотеки;
- создаст `.env`;
- добавит автозагрузку без CMD-окна.

## Настройка `.env`

```env
ROLE=agent
OWNER_ID=123456789
PC_NAME=laptop
AGENT_BOT_TOKEN=токен_agent_бота_этого_ПК
```

На каждом ПК поставь разное имя:

```text
laptop
office
home
pc2
```

И каждому ПК лучше свой agent-бот через @BotFather.

## Проверка

Сначала со своего Telegram-аккаунта открой чат с agent-ботом и нажми:

```text
/start
```

Потом можно проверить:

```text
/pc
```

Он ответит своим `PC_NAME`.

## Как main найдёт agent

На main ПК в `.env` нужно добавить username этого agent-бота:

```env
AGENTS=laptop:@YourLaptopAgentBot
```

Если agent называется `office`:

```env
AGENTS=laptop:@YourLaptopAgentBot,office:@YourOfficeAgentBot
```

## Главное про выключенный main ПК

Если main выключен:
- agent не подключается к main напрямую;
- agent просто продолжает работать в Telegram и ждать;
- когда main включится, он сможет снова отправлять команды agent-боту.

То есть agent не зависит от Wi‑Fi main ПК и не требует Tailscale.


## Python version

Эта версия принудительно использует Python 3.12, потому что Pillow 10.4.0 не ставится на Python 3.14 без сборки из исходников.
Если ранее установка упала на Pillow, запусти `repair_remove_bad_venv.bat`, потом снова установщик.
