import requests
import pandas as pd
import time
import random
import plotly.express as px
import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State

# First we set the key in order to be able to get the data from the API
API_Steam_Key = 'DC5161B0229D2AC6AC15F327189C8613'

# Set the url from which we'll take the data
url = 'https://api.steampowered.com'

# Method to obtain a list of games from Steam API
def getGamesList():
    response = requests.get(url + '/ISteamApps/GetAppList/v2/') # Get request
    if response.status_code != 200: # Chceck possible errors 
        print(f"Error in request: {response.status_code}")
        return None
    try:
        # Transform data and filter specific fields
        transformed_data = response.json()
        games = transformed_data['applist']['apps']
        
        # Filter games to avoid names like "TestXXX" and spaces in word
        games = [game for game in games if 'name' in game and game['name'].strip()
                 and 'test' not in game['name'].lower()]
        return games

    # Handle possible exceptions during execution
    except Exception as e:
        print(f"Error processing JSON: {e}")
        return []

# Method to obtain details of a game by its appid
def getGameDetails(appid):
    try:
        # Get request for selected game and data transformation to json
        resp = requests.get(f"https://store.steampowered.com/api/appdetails?appids={appid}")
        game_det = resp.json()
        # If there is appid and the request is valid
        if str(appid) in game_det and game_det[str(appid)]['success']:
            # Obtain genres, imgage url and a short_desc for the specified game
            data = game_det[str(appid)]['data']
            genres = data.get('genres', [])
            img_url = data.get('header_image', '') # Obtain image url from game
            short_desc = data.get('short_description', '') # Obtain game description

            # Make sure in genres we have a list, otherwise we set a list to avoid errors in data preprocessing
            if not isinstance(genres, list):
                genres = []
            genre_list = [genre['description'] for genre in genres] # Return genres

            return genre_list, img_url, short_desc # Return all details
        else:
            print(f"--- Game details not found for game with appid: {appid} ---")
    
    # Handle possible errors during execution
    except Exception as e:
            print(f"Error in game with appid {appid}: {e}")
    
    return [], '', '' # If exception, return this parameters to avoid errors during data preprocessing

# Obtain a list with valid games and all their fields
def getGamesWithGenres(num_games):
    games = getGamesList()[:num_games] # Sample spcified games in parameter
    games_genre = []

    for game in games:
        appid = game['appid']
        name = game['name']
        genres, img_url, short_desc = getGameDetails(appid)

        if genres and img_url: # Make sure this exists, otherwise we won't append to list
            games_genre.append({
                'appid': appid,
                'name': name,
                'genres': genres,
                'img_url': img_url,
                'description': short_desc
            })
        else:
            print(f"Skipped game '{name}' because of missing data")
        time.sleep(1) # Sleep 1 sec between requests to avoid getting blocked

    return games_genre 

# Run Dash application
app = dash.Dash(__name__)

# Obtener data
games_data = getGamesWithGenres(1000)
df = pd.DataFrame(games_data) # Set a DataFrame with obtained games
"""Filter DataFrame, we want only valid genre and avoid null values or other data types.
   We use a lambda function where x is every value of genre column. Finally the DataFrame will only
   contain columns in which genres is a list with at least a genre. """ 
df = df[df['genres'].apply(lambda x: isinstance(x, list) and len(x) > 0)]

# Organise games per genre in a dictionari
genre_dict = {}
for index, row in df.iterrows():
    for genre in row['genres']:
        if genre not in genre_dict:
            genre_dict[genre] = []
        genre_dict[genre].append({
            'name': row['name'],
            'img_url': row['img_url'],
            'description': row['description']
        })


# Set application layout
app.layout = html.Div([
    dcc.Graph(id='main-bubble-chart'),
    html.Button("Volver", id='back-button', style={'display': 'none'}),
    dcc.Store(id='reset-clickdata'),  # Add a Store to save reset status
    html.Div(id='game-info')  # Div to show game's info in HTML
])

# Def Callback of the graphic
@app.callback(
    [Output('main-bubble-chart', 'figure'),
     Output('back-button', 'style'),
     Output('reset-clickdata', 'clear'),
     Output('game-info', 'children')],
    [Input('main-bubble-chart', 'clickData'),
     Input('back-button', 'n_clicks')],
    [State('reset-clickdata', 'data')]
)
def display_bubble_chart(clickData, back_click, reset_data):
    ctx = dash.callback_context  # Obtain callback context to know which thing activated it

    # If user press "Volver" button show the main bubble graphic again
    if ctx.triggered[0]['prop_id'] == 'back-button.n_clicks':
        genre_df = pd.DataFrame({
            'Genre': list(genre_dict.keys()),
            'Game Count': [len(genre_dict[genre]) for genre in genre_dict]
        })
        fig = px.scatter(genre_df,
                         x=None,
                         y='Game Count',
                         size='Game Count',
                         color='Genre',
                         hover_name='Genre',
                         title='Bubble Chart of Games grouped by Genre',
                         size_max=60)

        fig.update_layout(
            xaxis_showgrid=False,
            yaxis_showgrid=False,
            xaxis_visible=False,
            yaxis_visible=False,
        )

        return fig, {'display': 'none'}, True, []  # Restore clickData and reset

    # If maing graphic has been shown after pressing "volver", and no click has been done to a bubble, reset clickData by hand
    if reset_data:
        clickData = None

    # If user hasn't clicked, show initial graph with bubbles
    if clickData is None:
        genre_df = pd.DataFrame({
            'Genre': list(genre_dict.keys()),
            'Game Count': [len(genre_dict[genre]) for genre in genre_dict]
        })
        fig = px.scatter(genre_df,
                         x=None,
                         y='Game Count',
                         size='Game Count',
                         color='Genre',
                         hover_name='Genre',
                         title='Bubble Chart of Games grouped by Genre',
                         size_max=60)

        fig.update_layout(
            xaxis_showgrid=False,
            yaxis_showgrid=False,
            xaxis_visible=False,
            yaxis_visible=False,
        )

        return fig, {'display': 'none'}, False, []  # Don't restore clickData

    # If click has been done, obtain genre wich has been clicked
    clicked_genre = clickData['points'][0]['hovertext']
    # Get 10 random games from all of the list of clicked genre
    top_games = random.sample(genre_dict[clicked_genre], min(len(genre_dict[clicked_genre]), 10))

    # Set HTML labels with game's name and image
    game_html = [
        html.Div([
            html.Img(src=game['img_url'], style={'width': '100px', 'height': '100px', 'display': 'block', 'margin': '0 auto'}),
            html.P(game['name'], style={'text-align': 'center'}),
            html.P(game['description'], style={'fontSize': 'small', 'text-align': 'center'})
        ], style={'display': 'inline-block', 'text-align': 'center', 'margin': '10px'})
        for game in top_games
    ]
    genre_title = html.H2(f"10 Games in Genre: {clicked_genre}", style={'text-align': 'center'})

    # Make an empty graph to avoid showing axis once clicked a bubble
    fig = px.scatter(x=None, y=None, title="") 
    fig.update_layout(
        xaxis=dict(showgrid=False, visible=False),
        yaxis=dict(showgrid=False, visible=False),
        margin=dict(l=0, r=0, t=0, b=0),
    )

    return fig, {'display': 'block'}, False, [genre_title] + game_html  # Don't restore clickData

# Run the application
if __name__ == '__main__':
    app.run_server(debug=False)
