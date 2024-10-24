import requests
import pandas as pd
import time
import plotly.express as px
import dash
from dash import dcc, html
from dash.dependencies import Input, Output

# First we set the key in order to be able to get the data from the API
API_Steam_Key = 'DC5161B0229D2AC6AC15F327189C8613'

# Set the url from which we'll take the data
url = 'https://api.steampowered.com'

def getGamesList():
    response = requests.get(url + '/ISteamApps/GetAppList/v2/')
    if response.status_code != 200:
        print(f"Error in request: {response.status_code}")
        return None
    try:
        transformed_data = response.json()
        games = transformed_data['applist']['apps']
        if not games:
            print("List of games is empty!!")
            return None
        
        # Filter games 
        games = [game for game in games if 'name' in game and game['name'].strip()
                 and 'test' not in game['name'].lower()]
        return games

    except ValueError as e:
        print(f"Error processing JSON: {e}")
        return None

def getGameDetails(appid):
    try:
        resp = requests.get(f"https://store.steampowered.com/api/appdetails?appids={appid}")
        game_det = resp.json()
        if str(appid) in game_det and game_det[str(appid)]['success']:
            genres = game_det[str(appid)]['data'].get('genres', [])
            if genres:
                return [genre['description'] for genre in genres] # Return genres
            else: 
                return []
    except Exception as e:
            print(f"Error in game with appid {appid}: {e}")
            return["Exception"]

def getGamesWithGenres():
    games = getGamesList()[:10] # Sample 50 games
    games_genre = []

    for game in games:
        appid = game['appid']
        name = game['name']
        genres = getGameDetails(appid)
        games_genre.append({
            'appid': appid,
            'name': name,
            'genres': genres
        })
        time.sleep(1) # Sleep 1 sec between requests to avoid getting blocked

    return games_genre 

if __name__ == '__main__':
    games_data = getGamesWithGenres()

    df = pd.DataFrame(games_data)
    
    df = df[df['genres'].apply(lambda x: isinstance(x, list) and len(x) > 0)]

    # Exploding genres to count the occurrences of each genre
    genre_count = df.explode('genres').groupby('genres')['appid'].count().reset_index()
    genre_count.columns = ['genre', 'count']

    fig = px.scatter(genre_count, x='genre', y='count', size='count', color='genre', 
                    hover_name='genre', size_max=60, title="Géneros de Videojuegos")

    # Inicializar la aplicación Dash
    app = dash.Dash(__name__)

    # Layout de la aplicación
    app.layout = html.Div([
        dcc.Graph(id='bubble-chart', figure=fig),
        html.Div(id='popup-content', style={'display': 'none', 'position': 'absolute', 
                                            'top': '100px', 'left': '50px', 'zIndex': '1000',
                                            'backgroundColor': 'white', 'border': '1px solid black',
                                            'padding': '10px'})  # Estilo para el pop-up
    ])

    # Callback para manejar el clic en las burbujas
    @app.callback(
        Output('popup-content', 'children'),
        [Input('bubble-chart', 'clickData')]
    )

    def display_popup(clickData):
        if clickData:
            # Depuración para verificar qué se captura en el click
            print(clickData)  # Imprimir los datos del clic

            genre_clicked = clickData['points'][0]['hovertext']  # El género sobre el cual se hizo clic
            # Filtrar los juegos pertenecientes a ese género
            games_in_genre = df[df['genres'].apply(lambda genres: genre_clicked in genres)]

            # Crear un gráfico de burbujas para los juegos dentro de ese género
            game_count = games_in_genre.groupby('name')['appid'].count().reset_index()
            game_count.columns = ['name', 'count']

            fig_games = px.scatter(game_count, x='name', y='count', size='count', color='name', 
                                   hover_name='name', size_max=40, title=f'Juegos en {genre_clicked}')

            # Cambiar el estilo del pop-up para que sea visible
            return html.Div([
                dcc.Graph(figure=fig_games)  # Mostrar gráfico de juegos dentro de la ventana emergente
            ], style={'display': 'block', 'position': 'absolute', 
                      'top': '100px', 'left': '50px', 'zIndex': '1000',
                      'backgroundColor': 'white', 'border': '1px solid black',
                      'padding': '10px'})
        return None

    app.run_server(debug=True)
    
    """
    games_data = getGamesWithGenres()

    df = pd.DataFrame(games_data)
    #print(df['genres'])
    
    df = df[df['genres'].apply(lambda x: isinstance(x, list) and len(x) > 0)]
    #print(df.head())
    #print("PRUEBA REALIZADA\n")

    df_grouped = df.groupby(['appid', 'name']).agg({'genres': lambda x: ', '.join(sum(x, []))}).reset_index(drop=True, inplace=True)
    #print(f"Tamaño del contenido del dataframe: {df['name'].size}")
    # print(df.head(n=50))

    genre_count = df.explode('genres').groupby('genres')['appid'].count().reset_index()
    genre_count.columns = ['genre', 'count']

    fig = px.scatter(genre_count, x='genre', y='count', size='count', color='genre', 
                    hover_name='genre', size_max=60, title="Géneros de Videojuegos")


    # Create list of games and genres
    genre_dict = {}
    for index, row in df.iterrows():
        for genre in row ['genres']:
            if genre not in genre_dict:
                genre_dict[genre] = []
            genre_dict[genre].append(row['name'])
    
    # Create DataFrame from genres dict
    genres = list(genre_dict.keys())
    games_genre = [len(genre_dict[genre]) for genre in genres]
    games_list_per_genre = ['<br>'.join(genre_dict[genre]) for genre in genres] # Games list in HTML format

    genre_df = pd.DataFrame({
        'Genre': genres,
        'Game Count': games_genre,
        'Games': games_list_per_genre # Add list of games to each bubble
    })

    # Create graphic
    fig = px.scatter(genre_df,
                     x=None,
                     y='Game Count',
                     size='Game Count',
                     color='Genre', # Eah genre will have a different color
                     hover_name='Genre',
                     hover_data={'Games': True}, # Show games list for each genre
                     title='Bubble Chart of Games grouped by Genre',
                     size_max=60,
                     template='plotly')
    
    # Update layout in order to avoid showing X and Y axis
    fig.update_layout(
        xaxis_showgrid=False,
        yaxis_showgrid=False,
        xaxis_visible=False,
        yaxis_visible=False,
    )
    
    # Show graphic
    fig.show()"""