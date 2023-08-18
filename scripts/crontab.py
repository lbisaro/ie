import requests

url = "http://localhost:8000/bot/api/bots/"


# A GET request to the API
response = requests.get(url)

# Print the response
response_json = response.json()
print(response_json)
