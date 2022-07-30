import logging
from logging import StreamHandler
import os  # чтобы получить доступ к переменным окружения из кода через getenv
import time
from http import HTTPStatus


import requests
import telegram

from dotenv import load_dotenv

load_dotenv()

# Взяли переменные из пространства переменных окружения
PRACTICUM_TOKEN = os.getenv('PRACTICUM')
TELEGRAM_TOKEN = os.getenv('TELEGRAM')
TELEGRAM_CHAT_ID = os.getenv('CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
# в заголовке запроса передан токен авторизации
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.',
}

START_MESSAGE = 'Привет! Давай узнаем что там с твоей домашкой!'

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
        logger.info(
            f'Сообщение в Telegram отправлено: {message}')
    except Exception as error:
        message = f'Сообщение в Telegram не отправлено: {error}'
        logger.error(message)


def get_api_answer(current_timestamp):
    """делает запрос к единственному эндпоинту API-сервиса.
    В качестве параметра функция получает временную метку.
    В случае успешного запроса должна вернуть ответ API,
    преобразовав его из формата JSON к типам данных Python.
    """
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}  # метка времени
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
        if response.status_code != HTTPStatus.OK:
            raise Exception('Ошибка статуса')
        logger.info('Запрос к API успешно выполнен.')

        return response.json()

    except Exception as error:
        message = f'Ошибка при запросе к API Практикум.Домашка: {error}'
        logger.error(message)
        raise Exception(message)


def check_response(response):
    """Проверяет ответ API на корректность.
    В качестве параметра функция
    получает ответ API, приведенный к типам данных Python.
    Если ответ API соответствует ожиданиям, то функция должна вернуть
    список домашних работ, доступный в ответе API по ключу 'homeworks'.
    """
    hw_list = response['homeworks']
    if not isinstance(hw_list, list):
        message = 'В ответе API домашки выводятся не списком.'
        logger.error(message)
        raise Exception(message)

    try:
        hw_list = response['homeworks']
        logger.info('Корректный ответ API.')

    except Exception:
        if type(response) is not dict:
            message = f'Некорректный тип данных: {response}'
            logger.error(message)
            raise TypeError(message)

        hw_list = response.get('homeworks')
        if len(hw_list) == 0:
            message = 'На проверку ничего не отправлено.'
            logger.error(message)
            raise Exception(message)

    return hw_list


def parse_status(homework):
    """Извлекает из информации о конкретной домашней работе статус этой работы.
    В качестве параметра функция получает только один элемент
    из списка домашних работ.
    В случае успеха, функция возвращает подготовленную для отправки в Telegram
    строку, содержащую один из вердиктов словаря HOMEWORK_STATUSES.
    """
    homework_name = homework['homework_name']
    homework_status = homework['status']

    try:
        verdict = HOMEWORK_STATUSES[homework_status]
        logger.info('Вердикт обновлен')

    except Exception:
        if homework_status not in HOMEWORK_STATUSES:
            message = f'Неизвестный статус домашней работы: {homework_status}'
            logger.error(message)
            raise Exception(message)

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверка доступности переменных окружения.
    Если отсутствует хотя бы одна переменная окружения —
    функция должна вернуть False, иначе — True.
    """
    vars_from_env = [PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]
    message = 'Нет обязательных переменных окружения во время запуска бота'

    if all(vars_from_env) is True:
        logger.info('Необходимые переменные окружения доступны.')

        return True

    else:
        logger.critical(message)

        return False


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
        exit()
    send_message(bot, START_MESSAGE)

    while True:
        try:
            response = get_api_answer(current_timestamp)
            homework = check_response(response)

            try:
                homework = check_response(response)[0]
                message = parse_status(homework)
            except IndexError:
                message = 'Нет домашки на проверку.'
                logger.error(message)
                raise Exception(message)
            current_timestamp = response.get('current_date')

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            send_message(bot, message)
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
