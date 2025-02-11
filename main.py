import random
import requests
import json
import threading
import string
import datetime

from loguru import logger
from time import sleep
from threading import Thread
from eth_account.signers.local import LocalAccount
from eth_account import Account
from web3.auto import w3
from eth_account.messages import encode_defunct

from better_proxy import Proxy
proxy_list = Proxy.from_file('proxies.txt')
def get_random_proxy():
    
    proxy = (random.choice(proxy_list)).as_proxies_dict
    return proxy

def get_nonce(prkey):
    main_acc: LocalAccount = Account.from_key(prkey)

    url = f'https://node.din.lol/api/account/web3/web3_nonce'
    headers = {
                'user-agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                'referer':'https://airdrop.din.lol/',
                'origin':'https://airdrop.din.lo',
                'content-type':'application/json',
            }
    
    data = {
        'address':f'{main_acc.address}'
    }
    data = json.dumps(data)

    while True:
        try:
            resp = requests.post(url, headers=headers, data=data, proxies=get_random_proxy())
            #print(resp.status_code)
            #print(resp.text)
            if resp.status_code == 200 or resp.status_code == 201:
                data = json.loads(resp.text)
                nonce = data['nonce']
                challenge = data['challenge']
                return nonce, challenge
            
            sleep(5)
        except Exception as e:
            logger.error(f'[{main_acc.address}][get_nonce] Error: {e}')
            sleep(5)

def get_random_string(length=16):
    chars = string.ascii_letters + string.digits  # Буквы (верхний + нижний регистр) и цифры
    return ''.join(random.choice(chars) for _ in range(length))

def sign_message(prkey, challenge):
    main_acc: LocalAccount = Account.from_key(prkey)

    utc_now = datetime.datetime.now(datetime.UTC)
    formatted_time = utc_now.strftime('%Y-%m-%dT%H:%M:%S.') + str(utc_now.microsecond // 1000).zfill(3) + 'Z'

    msg = f'''airdrop.din.lol wants you to sign in with your Ethereum account:
{main_acc.address}

{challenge}

URI: https://airdrop.din.lol
Version: 1
Chain ID: 56
Nonce: {get_random_string()}
Issued At: {formatted_time}'''
    
    message = encode_defunct(text=msg)
    signed_message = w3.eth.account.sign_message(message, private_key=prkey)
    signed_message = signed_message.signature.hex()

    return signed_message, msg

def get_bearer_token(prkey, signed_message, msg, nonce):
    main_acc: LocalAccount = Account.from_key(prkey)

    url = f'https://node.din.lol/api/account/web3/web3_challenge'
    headers = {
                'user-agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                'referer':'https://airdrop.din.lol/',
                'origin':'https://airdrop.din.lo',
                'content-type':'application/json',
            }
    
    data = {
        'address':f'{main_acc.address}',
        'challenge':f'{json.dumps({"msg": msg})}',
        'nonce':f'{nonce}',
        'referralCode':'',
        'signature':f'{signed_message}',
    }
    data = json.dumps(data)

    while True:
        try:
            resp = requests.post(url, headers=headers, data=data, proxies=get_random_proxy())
            #print(resp.status_code)
            #print(resp.text)
            if resp.status_code == 200 or resp.status_code == 201:
                data = json.loads(resp.text)
                token = data['extra']['token']
                return token
            
            sleep(5)
        except Exception as e:
            logger.error(f'[{main_acc.address}][get_bearer_token] Error: {e}')
            sleep(5)

def check_eligble(prkey, token):
    main_acc: LocalAccount = Account.from_key(prkey)

    url = f'https://node.din.lol/api/airdrop/getMerkleTreeForDINAirdrop'
    headers = {
                'user-agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                'referer':'https://airdrop.din.lol/',
                'origin':'https://airdrop.din.lo',
                'content-type':'application/json',
                'authorization':f'Bearer {token}'
            }
    
    data = {
        'account':f'{main_acc.address}',
        'chainId':56,
    }
    data = json.dumps(data)

    while True:
        try:
            resp = requests.post(url, headers=headers, data=data, proxies=get_random_proxy())
            #print(resp.status_code)
            #print(resp.text)
            if resp.status_code == 200 or resp.status_code == 201:
                if resp.text == '': 
                    return None
                
                data = json.loads(resp.text)
                
                dinAmount = data['dinAmount']
                return dinAmount
            
            sleep(5)
        except Exception as e:
            logger.error(f'[{main_acc.address}][check_eligble] Error: {e}')
            sleep(5)

def start(prkey):
    main_acc: LocalAccount = Account.from_key(prkey)

    nonce, challenge = get_nonce(prkey)
    signed_message, msg = sign_message(prkey, challenge)
    token = get_bearer_token(prkey, signed_message, msg, nonce)
    dinAmount = check_eligble(prkey, token)

    if dinAmount == None:
       logger.info(f'[{main_acc.address}] Not Eligible')

    else:
        with open(f'Eligible.txt', 'a', encoding='utf-8') as f:
            f.write(f'{prkey};{main_acc.address};{dinAmount}\n')

THREADS = int(input(f'Введите кол-во потоков: ')) + 1

file_name = 'wallets'
accs_list = open(file_name + '.txt', 'r').read().splitlines()

for el in accs_list:
    splited_data = el.split(';')
    prkey = splited_data[0]

    while threading.active_count() >= THREADS:
        sleep(1)

    Thread(target=start, args=(prkey, )).start()
    sleep(0.01)
