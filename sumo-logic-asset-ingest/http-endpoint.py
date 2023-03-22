#!/usr/bin/env python3
import json
import requests
import os

# RUNZERO CONF
RUNZERO_EXPORT_TOKEN = os.environ['RUNZERO_EXPORT_TOKEN']
HEADERS = {'Authorization': f'Bearer {RUNZERO_EXPORT_TOKEN}'}
BASE_URL = 'https://console.runZero.com/api/v1.0'

# SUMO LOGIC CONF
HTTP_ENDPOINT = os.environ['SUMO_HTTP_ENDPOINT']


def main():
    url = BASE_URL + '/export/org/assets.json'
    assets = requests.get(url, headers=HEADERS)
    batchsize = 500
    for i in range(0, len(assets.json()), batchsize):
        batch = assets.json()[i:i+batchsize]
        f = open('upload.txt', 'w')
        f.truncate(0)
        for a in batch:
            json.dump(a, f)
            f.write('\n')
        f.close()
        r = open('upload.txt')
        requests.post(HTTP_ENDPOINT, data=r.read())
        r.close()


if __name__ == '__main__':
    main()
