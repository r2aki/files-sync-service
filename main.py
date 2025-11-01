import os
import logging
import time
import json
from datetime import datetime
from configparser import ConfigParser
import yadisk_client


def load_config(config_path='config.ini'):
    """
    Загружает параметры из файла config.ini.

    :param config_path: Путь к файлу конфигурации.
    :return: Словарь с параметрами.
    """
    config = ConfigParser()
    config.read(config_path)

    params = {
        'local_folder': config.get('settings', 'local_folder'),
        'cloud_folder': config.get('settings', 'cloud_folder'),
        'token': config.get('settings', 'token'),
        'sync_interval': config.getint('settings', 'sync_interval'),
        'log_file': config.get('settings', 'log_file')
    }
    return params


def setup_logging(log_file):
    """
    Настраивает логирование в указанный файл.

    :param log_file: Путь к файлу лога.
    """
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )


def get_local_files_info(local_folder):
    """
    Собирает информацию о файлах в локальной папке.

    :param local_folder: Путь к локальной папке.
    :return: Словарь с информацией о файлах {имя_файла: {'mtime': время_модификации, 'size': размер}}.
    """
    files_info = {}
    for filename in os.listdir(local_folder):
        filepath = os.path.join(local_folder, filename)
        if os.path.isfile(filepath):
            stat = os.stat(filepath)
            files_info[filename] = {
                'mtime': stat.st_mtime,
                'size': stat.st_size
            }
    return files_info


def sync(local_folder, cloud_client):
    """
    Выполняет синхронизацию локальной папки с облачным хранилищем.

    :param local_folder: Путь к локальной папке.
    :param cloud_client: Экземпляр класса для работы с облаком (например, YaDiskClient).
    """
    local_files = get_local_files_info(local_folder)
    cloud_files = cloud_client.get_info()

    # Определяем файлы для загрузки или обновления
    for filename, local_info in local_files.items():
        cloud_info = cloud_files.get(filename)
        if cloud_info is None:
            # Файл новый
            local_path = os.path.join(local_folder, filename)
            try:
                cloud_client.load(local_path)
                logging.info(f"Файл '{filename}' загружен в облако.")
            except Exception as e:
                logging.error(f"Ошибка при загрузке файла '{filename}': {e}")
        else:
            # Файл существует, проверяем изменения
            if local_info['mtime'] != cloud_info.get('mtime') or local_info['size'] != cloud_info.get('size'):
                local_path = os.path.join(local_folder, filename)
                try:
                    cloud_client.reload(local_path)
                    logging.info(f"Файл '{filename}' обновлён в облаке.")
                except Exception as e:
                    logging.error(f"Ошибка при обновлении файла '{filename}': {e}")

    # Определяем файлы для удаления из облака
    for filename in cloud_files:
        if filename not in local_files:
            try:
                cloud_client.delete(filename)
                logging.info(f"Файл '{filename}' удалён из облака.")
            except Exception as e:
                logging.error(f"Ошибка при удалении файла '{filename}' из облака: {e}")


def main():
    """
    Основная функция программы.
    """
    try:
        config = load_config()
    except Exception as e:
        print(f"Ошибка при загрузке конфигурации: {e}. Проверьте файл config.ini.")
        return

    local_folder = config['local_folder']
    token = config['token']
    sync_interval = config['sync_interval']
    log_file = config['log_file']
    cloud_folder = config['cloud_folder']

    # Проверка существования локальной папки
    if not os.path.isdir(local_folder):
        print(f"Ошибка: Локальная папка '{local_folder}' не существует.")
        return

    # Настройка логирования
    setup_logging(log_file)
    logging.info(f"Программа синхронизации запущена. Локальная папка: {local_folder}")

    # Создание экземпляра клиента облака
    try:
        cloud_client = yadisk_client.YaDiskClient(token, cloud_folder)
    except Exception as e:
        print(f"Ошибка при инициализации клиента облака: {e}. Проверьте токен и настройки.")
        logging.error(f"Инициализация клиента облака не удалась: {e}")
        return

    # Первоначальная синхронизация
    logging.info("Начало первоначальной синхронизации.")
    sync(local_folder, cloud_client)
    logging.info("Первоначальная синхронизация завершена.")

    # Цикл отслеживания изменений
    while True:
        time.sleep(sync_interval)
        logging.info("Проверка изменений...")
        sync(local_folder, cloud_client)
        logging.info("Проверка изменений завершена.")


if __name__ == "__main__":
    main()
