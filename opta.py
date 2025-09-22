from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
import datetime
import os

# --- Configuração do Servidor Flask ---
app = Flask(__name__)
CORS(app) 

# --- CONFIGURAÇÃO DA API DE ESPORTES ---
# Sua chave de API foi inserida aqui. 
# O ideal em projetos profissionais é usar "Environment Variables" para não expor a chave no código.
API_KEY = "7baa5e00c8ae57d0e6240f790c6840dd" 
API_HOST = "v3.football.api-sports.io"
BASE_URL = f"https://{API_HOST}"

# Cabeçalhos padrão para todas as requisições
HEADERS = {
    'x-rapidapi-host': API_HOST,
    'x-rapidapi-key': API_KEY
}

# --- FUNÇÃO DE ANÁLISE (O CÉREBRO DO TIPSTER) ---
# Esta função não muda, pois ela apenas processa os dados que recebe.
def process_and_analyze_stats(stats_data):
    # O primeiro item da lista de estatísticas geralmente contém os dados da liga principal do jogador
    stats = stats_data['statistics'][0]
    games = stats["games"]["appearences"]

    if not games or games == 0:
        return {"key_stats": {}, "recommendations": []}

    # Helper para evitar erros com dados nulos (muito comum em APIs reais)
    def get_stat(category, key, default=0):
        # A API pode não retornar uma categoria se o jogador não tiver stats nela (ex: um atacante sem desarmes)
        if category not in stats or stats[category] is None or key not in stats[category] or stats[category][key] is None:
            return default
        return stats[category][key]

    key_stats = {
        "Rating Médio": stats["games"]["rating"] or "N/A",
        "Gols": f"{get_stat('goals', 'total') / games:.2f}",
        "Assistências": f"{get_stat('goals', 'assists') / games:.2f}",
        "Chutes": f"{get_stat('shots', 'total') / games:.2f}",
        "Chutes no Gol": f"{get_stat('shots', 'on') / games:.2f}",
        "Passes": f"{get_stat('passes', 'total') / games:.2f}",
        "Passes Chave": f"{get_stat('passes', 'key') / games:.2f}",
        "Desarmes": f"{get_stat('tackles', 'total') / games:.2f}",
        "Interceptações": f"{get_stat('tackles', 'interceptions') / games:.2f}",
        "Duelos Ganhos": f"{get_stat('duels', 'won') / games:.2f}",
        "Dribles": f"{get_stat('dribbles', 'success') / games:.2f}",
        "Faltas Sofridas": f"{get_stat('fouls', 'drawn') / games:.2f}",
        "Faltas Cometidas": f"{get_stat('fouls', 'committed') / games:.2f}",
    }

    recommendations = []
    
    def add_over_recommendation(market, average, lines, margin, reason_stat_name):
        for line in lines:
            if average > line + margin:
                recommendations.append({
                    "market": market,
                    "recommendation": f"Acima de {line}",
                    "confidence": min(0.95, (average - line) / (line * 1.5)),
                    "reason": f"Média de {average:.2f} {reason_stat_name} por jogo."
                })
    
    add_over_recommendation("Chutes do Jogador", get_stat('shots', 'total') / games, [0.5, 1.5, 2.5, 3.5], 0.2, "chutes")
    add_over_recommendation("Chutes no Gol", get_stat('shots', 'on') / games, [0.5, 1.5, 2.5], 0.15, "chutes no gol")
    add_over_recommendation("Desarmes do Jogador", get_stat('tackles', 'total') / games, [0.5, 1.5, 2.5, 3.5], 0.25, "desarmes")
    
    avg_goals = get_stat('goals', 'total') / games
    if avg_goals > 0.35:
        recommendations.append({"market": "Jogador para Marcar", "recommendation": "Sim", "confidence": min(0.95, avg_goals / 0.7), "reason": f"Média de {avg_goals:.2f} gols por jogo."})

    avg_assists = get_stat('goals', 'assists') / games
    if avg_assists > 0.20:
        recommendations.append({"market": "Jogador para dar Assistência", "recommendation": "Sim", "confidence": min(0.95, avg_assists / 0.4), "reason": f"Média de {avg_assists:.2f} assistências por jogo."})

    card_points = (get_stat('cards', 'yellow') + (get_stat('cards', 'red') * 2)) / games
    avg_fouls_committed = get_stat('fouls', 'committed') / games
    if card_points > 0.3 or (card_points > 0.25 and avg_fouls_committed > 1.5):
        recommendations.append({"market": "Jogador para receber Cartão", "recommendation": "Sim", "confidence": min(0.95, card_points / 0.5), "reason": f"Recebe {card_points:.2f} 'pontos de cartão' e comete {avg_fouls_committed:.2f} faltas p/ jogo."})
    
    return {"key_stats": key_stats, "recommendations": sorted(recommendations, key=lambda x: x['confidence'], reverse=True)}


# --- Endpoints da API (AGORA COM DADOS REAIS) ---

@app.route('/opta/countries', methods=['GET'])
def get_countries():
    try:
        response = requests.get(f"{BASE_URL}/countries", headers=HEADERS)
        response.raise_for_status()
        # A API já retorna no formato que precisamos: { "name": "Brazil", "code": "BR" }
        return jsonify(response.json()['response'])
    except requests.exceptions.RequestException as e:
        return jsonify({"error": str(e)}), 500

@app.route('/opta/leagues', methods=['GET'])
def get_leagues():
    country_code = request.args.get('country_code')
    if not country_code: return jsonify({"error": "Country code is required"}), 400
    
    try:
        params = {'code': country_code}
        response = requests.get(f"{BASE_URL}/leagues", headers=HEADERS, params=params)
        response.raise_for_status()
        
        # Formata a resposta da API para o formato que o frontend espera
        leagues = [{"id": item['league']['id'], "name": item['league']['name']} for item in response.json()['response']]
        return jsonify(leagues)
    except requests.exceptions.RequestException as e:
        return jsonify({"error": str(e)}), 500

@app.route('/opta/teams', methods=['GET'])
def get_teams():
    league_id = request.args.get('league_id')
    season = datetime.datetime.now().year # Usa o ano atual como temporada padrão
    if not league_id: return jsonify({"error": "League ID is required"}), 400

    try:
        params = {'league': league_id, 'season': season}
        response = requests.get(f"{BASE_URL}/teams", headers=HEADERS, params=params)
        response.raise_for_status()
        
        teams = [{"id": item['team']['id'], "name": item['team']['name']} for item in response.json()['response']]
        return jsonify(teams)
    except requests.exceptions.RequestException as e:
        return jsonify({"error": str(e)}), 500

@app.route('/opta/players', methods=['GET'])
def get_players():
    team_id = request.args.get('team_id')
    season = datetime.datetime.now().year
    if not team_id: return jsonify({"error": "Team ID is required"}), 400

    try:
        params = {'team': team_id, 'season': season}
        response = requests.get(f"{BASE_URL}/players", headers=HEADERS, params=params)
        response.raise_for_status()
        
        players = [{"id": item['player']['id'], "name": item['player']['name']} for item in response.json()['response']]
        return jsonify(players)
    except requests.exceptions.RequestException as e:
        return jsonify({"error": str(e)}), 500

@app.route('/opta/analyze', methods=['GET'])
def analyze_player():
    player_id = request.args.get('player_id')
    season = datetime.datetime.now().year
    if not player_id: return jsonify({"error": "Player ID is required"}), 400

    try:
        params = {'id': player_id, 'season': season}
        response = requests.get(f"{BASE_URL}/players", headers=HEADERS, params=params)
        response.raise_for_status()
        
        api_data = response.json()['response']
        if not api_data or not api_data[0]['statistics']:
            return jsonify({"error": "No statistics found for this player in the current season"}), 404

        player_data = api_data[0]
        
        # Extrai os dados do jogador e passa para a nossa função de análise
        player_info = {
            "name": player_data['player']['name'],
            "team": player_data['statistics'][0]['team']['name'],
            "position": player_data['statistics'][0]['games']['position'],
            "age": player_data['player']['age'],
            "photo": player_data['player']['photo']
        }
        
        analysis_result = process_and_analyze_stats(player_data)
        
        final_response = {
            "player_info": player_info,
            **analysis_result
        }
        return jsonify(final_response)
    except requests.exceptions.RequestException as e:
        return jsonify({"error": str(e)}), 500

@app.route('/')
def index():
    return "Servidor Opta IA (v3.0 - Dados Reais) está no ar!"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
