import win32console
import win32gui
import requests

ventana = win32console.GetConsoleWindow()
win32gui.ShowWindow(ventana,0)


#Cron de ejecucion en cada minuto

#Actualizar velas de Symbols Activos
url = "http://localhost:8000/bot/update_klines/all/"
response = requests.get(url)

# Print the response
response_json = response.json()
print(response_json)
