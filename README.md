# Бот-ассистент для проверки статуса домашней работы через Telegram

### Реализованы обращение к стороннему API сервиса Практикум.Домашка, отправка сообщения в Telegram при обновлении статуса, обработка исключений, логирование и уведомление о потенциальных проблемах сообщением в Telegram.
### Стек: Python 3, Client API и Bot API (Telegram), dotenv

### Как запустить проект:
### Клонировать репозиторий и перейти в него в командной строке:
```
git clone https://github.com/Savi-rina/homework_bot.git

cd homework_bot
```
### Cоздать и активировать виртуальное окружение:
```
python -m venv env
source env/bin/activate
```
### Установить зависимости из файла requirements.txt:
```
python -m pip install --upgrade pip
pip install -r requirements.txt
```
### Выполнить миграции:
```
python manage.py migrate
```
### Запустить проект:
```
python manage.py runserver
```
