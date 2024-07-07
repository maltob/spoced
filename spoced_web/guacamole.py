import hmac
import hashlib
from Crypto.Cipher import AES
from Crypto.Util import Padding
from base64 import b64encode
from requests import request
from urllib.parse import quote_plus,quote
import json

class Guacamole():
    def __init__(self,config=None) -> None:
        self.guacamole_url = str(config.get('GUAC_SERVER_PATH'))
        self.guacamole_key = bytes.fromhex(config.get('GUAC_JSON_SECRET_KEY').strip())
    def get_guac_token(self,json_data):
        encoding = "UTF-8"
        
        digest= hmac.digest(key=self.guacamole_key,msg=bytes(json_data,encoding=encoding),digest=hashlib.sha256)
        aes = AES.new(key=self.guacamole_key,IV=b'\x00'*16,mode=AES.MODE_CBC)
        
        hmac_msg = digest+json_data.encode(encoding)
        ciphered = aes.encrypt(Padding.pad(hmac_msg,aes.block_size))

        b64data = b64encode(ciphered)
        req = request("POST",url=f"{self.guacamole_url}/api/tokens",data=f'data={quote_plus(b64data)}',headers={"Content-type":"application/x-www-form-urlencoded"})
        if((req) and req.ok):
            return (json.loads(req.content)['authToken'])
        else:
            print(req)
            return False
    def generate_guac_json(self,connections:dict,username:str,expires_time:int):
        connections_json = []
        for key in connections:
            connections_json.append( f"\n\"{key}\" : { connections[key].toJson() }")

        return f"{{ \"username\":\"{username}\",  \"connections\":{{ { str.join(',',connections_json) } \n }} }}"


class GuacamoleRDP:
    def __init__(self, hostname: str,  ignore_cert: bool, preoconnection_blob:str = None, username :str = None, password :str = None,port:int=3389, security:str='any') -> None:
        self.protocol = 'rdp'
        self.parameters = {'hostname':hostname,'port':str(port),'ignore-cert':str(ignore_cert).lower()}
        if(preoconnection_blob != None):
            self.parameters['preoconnection_blob']=preoconnection_blob
        if(username != None):
            self.parameters['username']=username
        if(password != None):
            self.parameters['password']=password
        if(security != None):
            self.parameters['security']=security
    def toJson(self):
        return json.dumps(self, default=lambda o: o.__dict__)
    
