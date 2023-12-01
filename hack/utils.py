import requests
import sys


def call_campaign(receiver_num):
    try:
        api_key = 'e809bcab95a1bc91bd9e91ceec44ed8c44560322c941f301'
        api_token = '63c686aae1d656641aa716c1628bdcf9f5bc36c09e0b9b51'
        subdomain = 'api.in.exotel.com'
        sid = 'Exotel'
        url = f"https://{api_key}:{api_token}@{subdomain}/v1/Accounts/{sid}/Calls/connect.json"
        # bot_num = '912249360063'
        bot_num = '08047364008'
        caller_id = '02241499987'
        payload = f'From={receiver_num}&CallerId={caller_id}&To={bot_num}&Url=http://my.in.exotel.com/Exotel/exoml/start_voice/10696'
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }

        response = requests.post(url, headers=headers, data=payload)
        print(response.text, '\n')
    except Exception as e:
        _, _, exc_tb = sys.exc_info()
        print('Error in call_campaign', e, 'at', exc_tb.tb_lineno)

# num_list = ['7988822020', '8074928457', '7506333280', '9720454250', '9920262298', '8181012821', '8859313763'] 
num_list = ['918074928457']
for num in set(num_list):
    call_campaign(num)
