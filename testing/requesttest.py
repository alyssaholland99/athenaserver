import requests

url = "https://transmission.alyssaserver.co.uk"

if 401 == requests.get(url).status_code:
    print("Yippee")