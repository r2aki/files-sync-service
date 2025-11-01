from datetime import datetime

import requests
import os


class YaDiskClient:
    def __init__(self, token, cloud_folder):
        """
        Инициализирует клиент для работы с Яндекс.Диском.

        :param token: Токен доступа к Яндекс.Диску.
        :param cloud_folder: Путь к папке в Яндекс.Диске для синхронизации.
        """
        self.token = token
        self.cloud_folder = cloud_folder
        self.base_url = 'https://cloud-api.yandex.net/v1/disk/resources'
        self.headers = {
            'Authorization': f'OAuth {self.token}'
        }

        # Создаём папку в облаке, если её нет
        self._create_cloud_folder()

    def _create_cloud_folder(self):
        """
        Создаёт папку в облаке, если она не существует.
        """
        url = self.base_url
        params = {'path': self.cloud_folder}
        response = requests.put(url, headers=self.headers, params=params)
        # 409 Conflict означает, что папка уже существует
        if response.status_code not in [201, 409]:
            response.raise_for_status()

    def load(self, local_file_path):
        """
        Загружает файл в облако.

        :param local_file_path: Путь к локальному файлу.
        """
        filename = os.path.basename(local_file_path)
        cloud_file_path = f"{self.cloud_folder}/{filename}"

        # 1 Получить URL для загрузки
        upload_url = self._get_upload_url(cloud_file_path)

        # 2 Загрузить файл по полученному URL
        with open(local_file_path, 'rb') as f:
            response = requests.put(upload_url, data=f)
        response.raise_for_status()

    def reload(self, local_file_path):
        """
        Перезаписывает файл в облаке новой версией.

        :param local_file_path: Путь к локальному файлу.
        """
        # reload в Яндекс.Диске - это просто повторная загрузка
        self.load(local_file_path)

    def delete(self, filename):
        """
        Удаляет файл из облака.

        :param filename: Имя файла в облаке.
        """
        cloud_file_path = f"{self.cloud_folder}/{filename}"
        url = self.base_url
        params = {'path': cloud_file_path}
        response = requests.delete(url, headers=self.headers, params=params)
        # 404 Not Found - файла уже нет
        if response.status_code != 404:
            response.raise_for_status()

    def get_info(self):
        """
        Получает информацию о файлах в папке облака.

        :return: Словарь с информацией о файлах {имя_файла: {'mtime': timestamp, 'size': size}}.
        """
        url = self.base_url
        params = {'path': self.cloud_folder,
                  'fields': '_embedded.items.name,_embedded.items.modified,_embedded.items.size'}
        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()

        data = response.json()
        files_info = {}
        if '_embedded' in data and 'items' in data['_embedded']:
            for item in data['_embedded']['items']:
                # В Яндекс.Диске время приходит в формате ISO 8601, конвертируем в timestamp
                mtime_str = item.get('modified')
                if mtime_str:
                    try:
                        mtime = datetime.fromisoformat(mtime_str.replace('Z', '+00:00')).timestamp()
                    except ValueError:
                        # Если формат нестандартный, пропускаем
                        mtime = 0
                else:
                    mtime = 0

                size = item.get('size', 0)
                files_info[item['name']] = {
                    'mtime': mtime,
                    'size': size
                }
        return files_info

    def _get_upload_url(self, cloud_file_path):
        """
        Получает URL для загрузки файла.

        :param cloud_file_path: Путь к файлу в облаке.
        :return: URL для PUT-запроса.
        """
        url = f"{self.base_url}/upload"
        params = {'path': cloud_file_path, 'overwrite': 'true'}
        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        return response.json()['href']
