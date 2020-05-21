import requests
from requests.auth import HTTPBasicAuth


class RequestService:
    def __init__(self, host, headers, auth):
        self.host = host
        self.headers = headers
        self.auth = self.__create_auth__(auth)

    def get(self, url):
        return requests.get(self.host + url, headers=self.headers, auth=self.auth)

    def post(self, url, data):
        return requests.post(self.host + url, headers=self.headers, auth=self.auth, data=data)

    @staticmethod
    def __create_auth__(auth):
        return HTTPBasicAuth(auth['id'], auth['pxd'])
