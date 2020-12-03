from environs import Env
import requests

from .fsmodel import Directory, File

env = Env()


class BaseManager:
    def __init__(self, server_url):
        self.server_url = server_url

    def findByPrimaryKey(self, pk):
        bucket, path = pk
        url = f'{self.server_url}/{bucket}/{self.object_type}/{path}/'
        resp = requests.get(url)
        resp.raise_for_status()
        return self.model.deserialize_json(resp.content)


class DirectoryManager(BaseManager):
    object_type = "directory"
    model = Directory


class FileManager(BaseManager):
    object_type = "file"
    model = File


SERVER_URL = env.str("SERVER_URL", "http://localhost:5000")


def set_managers(server_url=None):
    server_url = server_url or SERVER_URL
    Directory.manager = DirectoryManager(server_url)
    File.manager = FileManager(server_url)


set_managers()
