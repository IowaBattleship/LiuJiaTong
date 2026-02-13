import json

CONFIG_NAME = 'LiuJiaTong.json'

class Config:
    def __init__(self, ip, port, name, cookie=None):
        self.ip = ip
        self.port = port
        self.name = name
        self.cookie = cookie # 使用cookie实现断线重连
    
    def __eq__(self, other):
        if isinstance(other, Config) is False:
            return False
        return self.ip == other.ip and self.port == other.port and self.name == other.name

    def __ne__(self, other) -> bool:
        if isinstance(other, Config) is False:
            return True
        return self.ip != other.ip or self.port != other.port or self.name != other.name
    
    def dump(self):
        with open(CONFIG_NAME, "w") as file:
            data = {
                "ip": self.ip,
                "port": self.port,
                "name": self.name,
                "cookie": self.cookie,
            }
            json.dump(data, file)
    
    def update_cookie(self, cookie):
        self.cookie = cookie
        self.dump()