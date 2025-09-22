from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
import datetime
import os
from collections import defaultdict
from typing import List, Dict

# --- Configuração do Servidor Flask ---
app = Flask(__name__)
CORS(app) 

# --- CONFIGURAÇÃO DA API DE ESPORTES ---
API_KEY = "7baa5e00c8ae57d0e6240f790c6840dd" 
API_HOST = "v3.football.api-sports.io"
BASE_URL = f"https://{API_HOST}"
HEADERS = {
    'x-rapidapi-host': API_HOST,
    'x-rapidapi-key': API_KEY
}

# --- FUNÇÃO DE ANÁLISE (O CÉREBRO DO TIPSTER) ---
def process_and_analyze_stats(stats_data):
    # Lógica para agregar estatísticas de múltiplos times na temporada
    aggregated_stats = defaultdict(lambda: defaultdict(lambda: 0))
    total_games = 0
    total_minutes = 0
    total_rating_weighted = 0
    
    for team_stats in stats_data['statistics']:
        games_in_team = team_stats.get("games", {}).get("appearences", 0)
        if not games_in_team: continue
        total_games += games_in_team
        
        minutes_in_team = team_stats.get("games", {}).get("minutes", 0)
        total_minutes += minutes_in_team
        
        try:
            rating = float(team_stats.get("games", {}).get("rating", 0))
            if rating > 0:
                total_rating_weighted += rating * minutes_in_team
        except (ValueError, TypeError):
            pass

        for category, values in team_stats.items():
            if isinstance(values, dict):
                for key, value in values.items():
                    if isinstance(value, (int, float)):
                        aggregated_stats[category][key] += value or 0

    if total_games == 0:
        return {"key_stats": {}, "recommendations": []}

    def get_stat(category, key):
        return aggregated_stats.get(category, {}).get(key, 0)

    key_stats = {
        "Rating Médio": f"{(total_rating_weighted / total_minutes):.2f}" if total_minutes > 0 else "N/A",
        "Gols": f"{get_stat('goals', 'total') / total_games:.2f}",
        "Assistências": f"{get_stat('goals', 'assists') / total_games:.2f}",
        "Chutes": f"{get_stat('shots', 'total') / total_games:.2f}",
        "Chutes no Gol": f"{get_stat('shots', 'on') / total_games:.2f}",
        "Passes": f"{get_stat('passes', 'total') / total_games:.2f}",
        "Desarmes": f"{get_stat('tackles', 'total') / total_games:.2f}",
    }

    recommendations = []
    
    avg_goals = get_stat('goals', 'total') / total_games
    if avg_goals > 0.35:
        recommendations.append({"market": "Jogador para Marcar", "recommendation": "Sim", "confidence": min(0.95, avg_goals / 0.7), "reason": f"Média de {avg_goals:.2f} gols por jogo."})

    avg_shots_on = get_stat('shots', 'on') / total_games
    if avg_shots_on > 0.5 + 0.15:
         recommendations.append({"market": "Chutes no Gol", "line": "0.5", "recommendation": "Acima de", "confidence": min(0.95, (avg_shots_on - 0.5) / 1.0), "reason": f"Média de {avg_shots_on:.2f} chutes no gol por jogo."})

    return {"key_stats": key_stats, "recommendations": sorted(recommendations, key=lambda x: x['confidence'], reverse=True)}

# --- NOVA FUNÇÃO PARA BUSCAR ODDS DE JOGADORES ---
def find_player_odds(fixture_id: int, player_name: str, predictions: List[Dict]) -> List[Dict]:
    """Busca odds para um jogo e enriquece as previsões de um jogador específico."""
    params = {'fixture': fixture_id}
    odds_data = requests.get(f"{BASE_URL}/odds", headers=HEADERS, params=params).json()

    if not odds_data or not odds_data.get("response"):
        return predictions

    best_odds = {}
    player_name_parts = player_name.lower().split()

    odds_response = odds_data["response"]
    if not odds_response: return predictions
    
    for bookmaker in odds_response[0].get("bookmakers", []):
        bookmaker_name = bookmaker.get("name")
        for bet in bookmaker.get("bets", []):
            market_name = bet.get("name")
            for value in bet.get("values", []):
                # Mercados de jogador geralmente contêm o nome do jogador no 'value'
                odd_player_name = str(value.get("value", "")).lower()
                odd_value = float(value.get("odd", 0))

                # Lógica para "casar" o nome do jogador
                is_player_match = all(part in odd_player_name for part in player_name_parts)

                if is_player_match:
                    key = None
                    if market_name == "Anytime Goalscorer" and "Yes" in value.get("value", ""):
                        key = ("Jogador para Marcar", "Sim")
                    elif market_name == "Player Shots on Target" and "Over 0.5" in value.get("value", ""):
                        key = ("Chutes no Gol", "Acima de", "0.5")
                    
                    if key and odd_value > best_odds.get(key, {}).get("odd", 0):
                         best_odds[key] = {"odd": odd_value, "bookmaker": bookmaker_name}

    for pred in predictions:
        key_to_find = (pred["market"], pred["recommendation"])
        if "line" in pred:
            key_to_find = (pred["market"], pred["recommendation"], pred["line"])
            
        if key_to_find in best_odds:
            pred["best_odd"] = best_odds[key_to_find]["odd"]
            pred["bookmaker"] = best_odds[key_to_find]["bookmaker"]
            
    return predictions

# --- Endpoints da API ---
@app.route('/opta/countries', methods=['GET'])
def get_countries():
    response = requests.get(f"{BASE_URL}/countries", headers=HEADERS)
    return jsonify(response.json()['response'])

@app.route('/opta/leagues', methods=['GET'])
def get_leagues():
    country_code = request.args.get('country_code')
    params = {'code': country_code}
    response = requests.get(f"{BASE_URL}/leagues", headers=HEADERS, params=params)
    leagues = [{"id": item['league']['id'], "name": item['league']['name']} for item in response.json()['response']]
    return jsonify(leagues)

@app.route('/opta/teams', methods=['GET'])
def get_teams():
    league_id, season = request.args.get('league_id'), datetime.datetime.now().year
    params = {'league': league_id, 'season': season}
    response = requests.get(f"{BASE_URL}/teams", headers=HEADERS, params=params)
    teams = [{"id": item['team']['id'], "name": item['team']['name']} for item in response.json()['response']]
    return jsonify(teams)

@app.route('/opta/players', methods=['GET'])
def get_players():
    team_id, season = request.args.get('team_id'), datetime.datetime.now().year
    params = {'team': team_id, 'season': season}
    response = requests.get(f"{BASE_URL}/players", headers=HEADERS, params=params)
    players = [{"id": item['player']['id'], "name": item['player']['name']} for item in response.json()['response']]
    return jsonify(players)

# --- ENDPOINT DE ANÁLISE (MODIFICADO) ---
@app.route('/opta/analyze', methods=['GET'])
def analyze_player():
    player_id, season = request.args.get('player_id'), datetime.datetime.now().year
    if not player_id: return jsonify({"error": "Player ID is required"}), 400

    try:
        # 1. Pega as estatísticas sazonais do jogador
        params = {'id': player_id, 'season': season}
        response = requests.get(f"{BASE_URL}/players", headers=HEADERS, params=params)
        response.raise_for_status()
        api_data = response.json()['response']

        if not api_data or not api_data[0]['statistics']:
            return jsonify({"error": "No statistics found"}), 404

        player_data = api_data[0]
        player_info = {
            "name": player_data['player']['name'], "age": player_data['player']['age'],
            "photo": player_data['player']['photo'],
            "team": player_data['statistics'][0]['team']['name'],
            "position": player_data['statistics'][0]['games']['position']
        }

        # 2. Gera as recomendações baseadas nas estatísticas
        analysis_result = process_and_analyze_stats(player_data)
        
        # 3. Descobre o próximo jogo do time do jogador
        team_id = player_data['statistics'][0]['team']['id']
        fixtures_resp = requests.get(f"{BASE_URL}/fixtures", headers=HEADERS, params={'team': team_id, 'next': 1}).json()
        
        # 4. Se houver um próximo jogo, busca as odds e enriquece a análise
        if fixtures_resp and fixtures_resp.get("response"):
            next_fixture = fixtures_resp["response"][0]
            fixture_id = next_fixture["fixture"]["id"]
            
            # Chama a nova função para buscar odds
            analysis_result["recommendations"] = find_player_odds(fixture_id, player_info["name"], analysis_result["recommendations"])

        final_response = {"player_info": player_info, **analysis_result}
        return jsonify(final_response)

    except requests.exceptions.RequestException as e:
        return jsonify({"error": str(e)}), 500

@app.route('/')
def index():
    return "Servidor Opta IA (v5.0 - Odds de Jogador) está no ar!"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
