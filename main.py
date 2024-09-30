import requests
import pandas as pd

# First we set the key in order to be able to get the data from the API
API_Steam_Key = 'DC5161B0229D2AC6AC15F327189C8613'

# Set the url from which we'll take the data
url = 'https://api.steampowered.com'

def GetData():
    response = requests.get(url + '/ISteamApps/GetAppList/v2/')
    transformed_data = response.json()
    games = transformed_data['applist']['apps']
    print(games[:5])

if __name__ == '__main__':
    GetData()