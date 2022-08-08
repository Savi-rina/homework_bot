import json
import logging
from logging import StreamHandler
import os
import sys
import time
from http import HTTPStatus

import requests
import telegram
from telegram import TelegramError

from dotenv import load_dotenv

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM')
TELEGRAM_TOKEN = os.getenv('TELEGRAM')
TELEGRAM_CHAT_ID = os.getenv('CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.',
}


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = StreamHandler()
logger.addHandler(handler)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
handler.setFormatter(formatter)


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info(f'Сообщение в Telegram отправлено: {message}')
    except telegram.TelegramError as telegram_error:
        message = f'Сообщение в Telegram не отправлено: {telegram_error}'
        raise TelegramError(message)


def get_api_answer(current_timestamp):
    """делает запрос к единственному эндпоинту API-сервиса.
    В качестве параметра функция получает временную метку.
    В случае успешного запроса должна вернуть ответ API,
    преобразовав его из формата JSON к типам данных Python.
    """
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
        if response.status_code != HTTPStatus.OK:
            raise Exception('Ошибка статуса')
        logger.info('Запрос к API успешно выполнен.')

        return response.json()

    except json.decoder.JSONDecodeError:
        raise Exception('Преобразование в json не осуществлено')

    except Exception as error:
        message = f'Ошибка при запросе к API Практикум.Домашка: {error}'
        raise Exception(message)


def check_response(response):
    """Проверяет ответ API на корректность.
    В качестве параметра функция
    получает ответ API, приведенный к типам данных Python.
    Если ответ API соответствует ожиданиям, то функция должна вернуть
    список домашних работ, доступный в ответе API по ключу 'homeworks'.
    """
    if not isinstance(response, dict):
        message = f'Некорректный тип данных: {response}'
        raise TypeError(message)

    if 'homeworks' not in response:
        raise KeyError('Ключ homeworks отсутствует')

    homework_list = response['homeworks']
    logger.info('Корректный ответ API.')

    if not isinstance(homework_list, list):
        message = 'В ответе API домашки выводятся не списком.'
        raise Exception(message)

    if 'current_date' not in response:
        raise KeyError('Ключ current_date отсутствует')

    return homework_list


def parse_status(homework):
    """Извлекает из информации о конкретной домашней работе статус этой работы.
    В качестве параметра функция получает только один элемент
    из списка домашних работ.
    В случае успеха, функция возвращает подготовленную для отправки в Telegram
    строку, содержащую один из вердиктов словаря HOMEWORK_STATUSES.
    """
    if 'homework_name' not in homework:
        raise KeyError('Ключ homework_name отсутствует')

    if 'status' not in homework:
        raise KeyError('Ключ homework_status отсутствует')

    homework_name = homework['homework_name']
    homework_status = homework['status']

    try:
        verdict = HOMEWORK_STATUSES[homework_status]
        logger.info('Вердикт обновлен')
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'

    except Exception:
        if homework_status not in HOMEWORK_STATUSES:
            message = f'Неизвестный статус домашней работы: {homework_status}'
            raise Exception(message)


def check_tokens():
    """Проверка доступности переменных окружения.
    Если отсутствует хотя бы одна переменная окружения —
    функция должна вернуть False, иначе — True.
    """
    vars_from_env = [PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]

    return all(vars_from_env)


def main():
    """Основная логика работы бота.
    1) Сделать запрос к API. 2) Проверить ответ.
    2) Если есть обновления — получить статус работы из обновления
    и отправить сообщение в Telegram.
    3) Подождать некоторое время и сделать новый запрос.
    """
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())

    if not check_tokens():
        logger.critical('Токен(ы) отсутствует(ют)')
        sys.exit()

    first_message = ''

    while True:

        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            if homeworks:
                message = parse_status(homeworks[0])
                if first_message != message:
                    send_message(bot, message)
                    first_message = message
                else:
                    logger.error(f'Повторяющееся сообщение: {message}')
                current_timestamp = response['current_date']
            else:
                logger.info('домашек нет')

        except telegram.TelegramError as telegram_error:
            message = f'Сбой в работе Telegram: {telegram_error}'
            logger.error(message)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            if first_message != message:
                logger.error(message)
                send_message(bot, message)
                first_message = message
            else:
                logger.error(f'Повторяющееся сообщение: {message}')
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
