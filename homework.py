import logging
import os
import sys
import time
from http import HTTPStatus
from logging.handlers import RotatingFileHandler

import requests
import telegram
from dotenv import load_dotenv
from exceptions import (DataTypeError, EmptyVariables, EndpointError,
                        FormatError, HomeworkIsNone, NoKeys)

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PCM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TG_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


LOG_FILE_FORMAT = '%(asctime)s, %(levelname)s, %(funcName)s, %(message)s'

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = RotatingFileHandler(
    filename=os.path.expanduser('main.log'),
    maxBytes=50000000,
    backupCount=5
)
formatter = logging.Formatter(LOG_FILE_FORMAT)
handler.setFormatter(formatter)
logger.addHandler(handler)


def check_tokens():
    """Проверяет доступность переменных окружения."""
    CHECK_TOKENS = {
        'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
        'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
        'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID,
                    }

    for token in CHECK_TOKENS.values():
        if token is None:
            logger.critical('Отсутствует глобальная переменная')
            return False
        if not token:
            logger.critical('Пустая глобальная переменная')
            return False
    return True


def send_message(bot, message):
    """Отправляет переменные в Телеграмм чат."""
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message
        )
        logger.debug(f'Отправлено сообщение"{message}".')
    except telegram.error.TelegramError as error:
        logger.error('Ошибка при отправке'
                     f' сообщения в Telegram : {error}')


def get_api_answer(timestamp):
    """Делает запрос к единственному эндпоинту API."""
    params = {'from_date': timestamp}
    all_params = dict(url=ENDPOINT, headers=HEADERS, params=params)
    try:
        response = requests.get(**all_params)
    except requests.exceptions.RequestException as error:
        logger.error('Ошибка запроса {}'.format(error))
        raise telegram.error.TelegramError(
            '{error}, {url}, {headers}, {params}'.format(
                error=error,
                **all_params,
            ))
    response_status = response.status_code
    if response_status != HTTPStatus.OK:
        logger.error('Недоступность эндпоинта {response_status},'
                     '{url}, {headers}, {params}')
        raise EndpointError(
            '{response_status}, {url}, {headers}, {params}'.format(
                response_status=response_status,
                **all_params,
            ))
    try:
        return response.json()
    except Exception as error:
        logger.error('Формат не json {}'.format(error))
        raise FormatError('Формат не json {}'.format(error))


def check_response(response):
    """Проверяет ответ API на соответствие документации."""
    if type(response) != dict:
        logging.error('Пришел не словарь')
        raise TypeError('Пришел не словарь с домашней работой')
    if 'homeworks' not in response:
        logging.error('Отсутствуют ключ homeworks')
        raise NoKeys('homeworks отсутствуют')
    if not isinstance(response['homeworks'], list):
        logger.error('Ошибка типа')
        raise TypeError('Ошибка типа объекта')
    if response['homeworks'] != []:
        return response['homeworks']
    else:
        raise EmptyVariables('Задание еще не проверено')


def parse_status(homework):
    """Отображает статус домашней работы."""
    if homework is None:
        raise HomeworkIsNone('Последняя домашняя работа не найдена')

    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')

    if homework_status not in HOMEWORK_VERDICTS:
        logger.error('-')
        raise NameError('{}'.format(homework_status))

    if 'homework_name' not in homework:
        logger.error('Название работы по ключу homework_name не найдено')
        raise DataTypeError('Ответ получен не dict')

    verdict = HOMEWORK_VERDICTS[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    logging.debug('Запуск бота')
    if not check_tokens():
        logger.critical('Ошибка глобальной переменной.')
        raise sys.exit(1)

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    STATUS = ''

    while True:
        try:
            response = get_api_answer(timestamp)
            homework = check_response(response)[0]
            if len(homework) == 0:
                logger.debug('Отсутствуют новые статусы')
            message = parse_status(homework)
            if message != STATUS:
                send_message(bot, message)
                STATUS = message
            timestamp = response.get('current_date')
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
        finally:
            time.sleep(RETRY_PERIOD)
        logger.debug('Успешная отправка сообщения')


if __name__ == '__main__':

    main()
