import requests

url = "ttp://localhost:11434/api/generate -d"  # Prova direttamente l'endpoint /v1/ask
response = requests.get(url)
print(response.text)
