import logging
import os
import sys
import time
from logging import StreamHandler

import requests
import telegram
from dotenv import load_dotenv
from exceptions import (DataTypeError, EmptyVariables, EndpointError,
                        FormatError, HomeworkIsNone)

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PCM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TG_TOKEN')
TELEGRAM_CHAT_ID = 402588677

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверяет доступность переменных окружения."""
    for token in (PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID):
        if token is None:
            logging.critical('Отсутствует глобальная переменная')
            return False
        if not token:
            logging.critical('Пустая глобальная переменная')
            return False
    return True


def send_message(bot, message):
    """Отправляет переменные в Телеграмм чат."""
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message
        )
        logging.debug(f'Отправлено сообщение"{message}".')
    except telegram.error.TelegramError as error:
        logging.error(f'Ошибка при отправке'
                      f' сообщения в Telegram : {error}')


def get_api_answer(timestamp):
    """Делает запрос к единственному эндпоинту API."""
    params = {'from_date': timestamp}
    all_params = dict(url=ENDPOINT, headers=HEADERS, params=params)
    try:
        response = requests.get(**all_params)
    except requests.exceptions.RequestException as error:
        logging.error('Ошибка запроса {}'.format(error))
        raise telegram.error.TelegramError(
            '{error}, {url}, {headers}, {params}'.format(
                error=error,
                **all_params,
            ))
    response_status = response.status_code
    if response_status != 200:
        logging.error('Недоступность эндпоинта {}')
        raise EndpointError(
            '{response_status}, {url}, {headers}, {params}'.format(
                response_status=response_status,
                **all_params,
            ))
    try:
        return response.json()
    except Exception as error:
        logging.error('Формат не json {}'.format(error))
        raise FormatError('Формат не json {}'.format(error))


def check_response(response):
    """Проверяет ответ API на соответствие документации."""
    try:
        if response['homeworks'] != []:
            return response['homeworks'][0]
    except Exception as error:
        logging.error('Ответ пришел не в формате Json')
        raise TypeError('Пришел не список {}'.format(error))


def parse_status(homework):
    """Отображает статус домашней работы."""
    if homework is None:
        raise HomeworkIsNone('Последняя домашняя работа не найдена')

    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')

    if homework_status not in HOMEWORK_VERDICTS:
        logging.error('Неожиданный статус домашней работы')
        raise NameError('{}'.format(homework_status))

    if 'homework_name' not in homework:
        logging.error('Название работы по ключу homework_name не найдено')
        raise DataTypeError('Ответ получен не dict')

    verdict = HOMEWORK_VERDICTS[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logging.error('Ошибка глобальной переменной.')
        raise EmptyVariables('Ошибка глобальной переменной.')

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())

    while True:
        try:
            response = get_api_answer(timestamp)
            homework = check_response(response)
            message = parse_status(homework)
            send_message(bot, message)
            timestamp = response.get('current_date')
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
        finally:
            time.sleep(RETRY_PERIOD)
        logging.debug('Успешная отправка сообщения')


if __name__ == '__main__':
    logging.basicConfig(
        format='%(asctime)s, %(levelname)s, %(message)s',
        filename='main.log',
        filemode='w',
        level=logging.DEBUG,
    )
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    handler = StreamHandler(sys.stdout)
    logger.addHandler(handler)
    main()
