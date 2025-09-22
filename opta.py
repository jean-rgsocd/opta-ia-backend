from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
import random
import os # Adicionado para compatibilidade com Render

# --- Configuração do Servidor Flask ---
app = Flask(__name__)
CORS(app) 

# --- CONFIGURAÇÃO DA API DE ESPORTES (Substituir em produção) ---
API_KEY = "7baa5e00c8ae57d0e6240f790c6840dd" 
API_HOST = "v3.football.api-sports.io"
API_URL = f"https://{API_HOST}"

# --- FUNÇÃO DE SIMULAÇÃO DE DADOS (ATUALIZADA E COMPLETA) ---
# Esta função agora simula TODAS as estatísticas que você pediu.

def simulate_player_stats(player_id):
    random.seed(player_id)
    games_played = random.randint(15, 30)
    
    # Previne divisão por zero se o jogador não tiver jogado
    if games_played == 0:
        games_played = 1

    return {
        "player_info": {
            "name": f"Jogador Exemplo {player_id}",
            "team": "Time Simulado FC",
            "position": random.choice(["Attacker", "Midfielder", "Defender", "Goalkeeper"]),
            "age": random.randint(18, 35),
            "photo": f"https://media.api-sports.io/football/players/{player_id}.png"
        },
        "stats": {
            # Jogos
            "games": {
                "appearences": games_played,
                "lineups": int(games_played * random.uniform(0.8, 1.0)),
                "minutes": games_played * random.randint(65, 90),
                "rating": f"{random.uniform(6.5, 8.5):.2f}"
            },
            # Chutes
            "shots": {
                "total": int(games_played * random.uniform(0.5, 4.5)),
                "on": int(games_played * random.uniform(0.2, 2.5))
            },
            # Gols
            "goals": {
                "total": int(games_played * random.uniform(0.1, 0.9)),
                "assists": int(games_played * random.uniform(0.05, 0.4))
            },
            # Passes
            "passes": {
                "total": int(games_played * random.uniform(15, 70)),
                "key": int(games_played * random.uniform(0.3, 2.0)),
                "accuracy": random.randint(70, 95)
            },
            # Defesa
            "tackles": {
                "total": int(games_played * random.uniform(0.5, 3.5)),
                "interceptions": int(games_played * random.uniform(0.4, 2.5))
            },
            # Duelos
            "duels": {
                "total": int(games_played * random.uniform(5, 15)),
                "won": int(games_played * random.uniform(3, 10))
            },
            # Dribles
            "dribbles": {
                "attempts": int(games_played * random.uniform(1, 5)),
                "success": int(games_played * random.uniform(0.5, 3))
            },
            # Faltas
            "fouls": {
                "drawn": int(games_played * random.uniform(0.5, 3.0)),
                "committed": int(games_played * random.uniform(0.5, 2.5))
            },
            # Cartões
            "cards": {
                "yellow": random.randint(0, 12),
                "red": random.randint(0, 2)
            }
        }
    }

# --- FUNÇÃO DE ANÁLISE (O NOVO CÉREBRO DO TIPSTER - ATUALIZADA E COMPLETA) ---

def process_and_analyze_stats(stats_data):
    stats = stats_data["stats"]
    games = stats["games"]["appearences"]

    if games == 0:
        return {"key_stats": {}, "recommendations": []}

    # 1. Calcular médias por jogo para TODAS as estatísticas
    key_stats = {
        "Rating Médio": stats["games"]["rating"],
        "Gols": f"{stats['goals']['total'] / games:.2f}",
        "Assistências": f"{stats['goals']['assists'] / games:.2f}",
        "Chutes": f"{stats['shots']['total'] / games:.2f}",
        "Chutes no Gol": f"{stats['shots']['on'] / games:.2f}",
        "Passes": f"{stats['passes']['total'] / games:.2f}",
        "Passes Chave": f"{stats['passes']['key'] / games:.2f}",
        "Desarmes": f"{stats['tackles']['total'] / games:.2f}",
        "Interceptações": f"{stats['tackles']['interceptions'] / games:.2f}",
        "Duelos Ganhos": f"{stats['duels']['won'] / games:.2f}",
        "Dribles": f"{stats['dribbles']['success'] / games:.2f}",
        "Faltas Sofridas": f"{stats['fouls']['drawn'] / games:.2f}",
        "Faltas Cometidas": f"{stats['fouls']['committed'] / games:.2f}",
    }

    # 2. Gerar Recomendações para TODOS os mercados possíveis
    recommendations = []
    
    # Função auxiliar para criar recomendações de "Acima de" (Over)
    def add_over_recommendation(market, average, lines, margin, reason_stat_name):
        for line in lines:
            if average > line + margin:
                recommendations.append({
                    "market": market,
                    "recommendation": f"Acima de {line}",
                    "confidence": min(0.95, (average - line) / (line * 1.5)),
                    "reason": f"Média de {average:.2f} {reason_stat_name} por jogo."
                })

    # Analisar cada mercado
    add_over_recommendation("Chutes do Jogador", stats['shots']['total'] / games, [0.5, 1.5, 2.5, 3.5], 0.2, "chutes")
    add_over_recommendation("Chutes no Gol", stats['shots']['on'] / games, [0.5, 1.5, 2.5], 0.15, "chutes no gol")
    add_over_recommendation("Desarmes do Jogador", stats['tackles']['total'] / games, [0.5, 1.5, 2.5, 3.5], 0.25, "desarmes")
    add_over_recommendation("Passes do Jogador", stats['passes']['total'] / games, [19.5, 29.5, 39.5, 49.5, 59.5], 5.0, "passes")
    add_over_recommendation("Faltas Cometidas", stats['fouls']['committed'] / games, [0.5, 1.5], 0.2, "faltas cometidas")

    # Mercado: Marcar Gol
    avg_goals = stats['goals']['total'] / games
    if avg_goals > 0.35:
        recommendations.append({
            "market": "Jogador para Marcar", "recommendation": "Sim",
            "confidence": min(0.95, avg_goals / 0.7),
            "reason": f"Média de {avg_goals:.2f} gols por jogo."
        })

    # Mercado: Dar Assistência
    avg_assists = stats['goals']['assists'] / games
    if avg_assists > 0.20:
        recommendations.append({
            "market": "Jogador para dar Assistência", "recommendation": "Sim",
            "confidence": min(0.95, avg_assists / 0.4),
            "reason": f"Média de {avg_assists:.2f} assistências por jogo."
        })

    # Mercado: Receber Cartão
    card_points = (stats['cards']['yellow'] + (stats['cards']['red'] * 2)) / games
    avg_fouls_committed = stats['fouls']['committed'] / games
    if card_points > 0.3 or (card_points > 0.25 and avg_fouls_committed > 1.5):
        recommendations.append({
            "market": "Jogador para receber Cartão", "recommendation": "Sim",
            "confidence": min(0.95, card_points / 0.5),
            "reason": f"Recebe {card_points:.2f} 'pontos de cartão' e comete {avg_fouls_committed:.2f} faltas p/ jogo."
        })

    # Ordena as recomendações pela confiança (da maior para a menor)
    return {
        "key_stats": key_stats, 
        "recommendations": sorted(recommendations, key=lambda x: x['confidence'], reverse=True)
    }


# --- Endpoints da API (NÃO PRECISAM DE MUDANÇA) ---
# O código abaixo permanece o mesmo, pois a lógica de rotas não mudou.

# Funções de simulação de API (usadas pelos endpoints)
def simulate_api_countries():
    return [{"name": "Brazil", "code": "BR"}, {"name": "England", "code": "GB"}, {"name": "Spain", "code": "ES"}]
def simulate_api_leagues(country_code):
    return {"BR": [{"id": 71, "name": "Brasileirão Série A"}], "GB": [{"id": 39, "name": "Premier League"}], "ES": [{"id": 140, "name": "La Liga"}]}.get(country_code, [])
def simulate_api_teams(league_id):
    return {71: [{"id": 127, "name": "Flamengo"}, {"id": 121, "name": "Palmeiras"}], 39: [{"id": 40, "name": "Liverpool"}, {"id": 50, "name": "Manchester City"}], 140: [{"id": 529, "name": "Barcelona"}, {"id": 541, "name": "Real Madrid"}]}.get(league_id, [{"id": 999, "name": "Time Exemplo"}])
def simulate_api_players(team_id):
    return {127: [{"id": 2749, "name": "Gabriel Barbosa"}, {"id": 358, "name": "Giorgian De Arrascaeta"}], 121: [{"id": 2786, "name": "Dudu"}, {"id": 2609, "name": "Raphael Veiga"}], 541: [{"id": 874, "name": "Kylian Mbappé"}, {"id": 154, "name": "Vinícius Júnior"}]}.get(team_id, [{"id": 12345, "name": "Jogador Exemplo"}])

@app.route('/opta/countries', methods=['GET'])
def get_countries():
    return jsonify(simulate_api_countries())

@app.route('/opta/leagues', methods=['GET'])
def get_leagues():
    country_code = request.args.get('country_code')
    if not country_code: return jsonify({"error": "Country code is required"}), 400
    return jsonify(simulate_api_leagues(country_code))

@app.route('/opta/teams', methods=['GET'])
def get_teams():
    league_id = int(request.args.get('league_id'))
    if not league_id: return jsonify({"error": "League ID is required"}), 400
    return jsonify(simulate_api_teams(league_id))

@app.route('/opta/players', methods=['GET'])
def get_players():
    team_id = int(request.args.get('team_id'))
    if not team_id: return jsonify({"error": "Team ID is required"}), 400
    return jsonify(simulate_api_players(team_id))

@app.route('/opta/analyze', methods=['GET'])
def analyze_player():
    player_id = int(request.args.get('player_id'))
    if not player_id: return jsonify({"error": "Player ID is required"}), 400
    
    stats_data = simulate_player_stats(player_id)
    analysis_result = process_and_analyze_stats(stats_data)
    
    final_response = {
        "player_info": stats_data["player_info"],
        **analysis_result
    }
    return jsonify(final_response)

@app.route('/')
def index():
    return "Servidor Opta IA (v2.0 - Análise Completa) está no ar!"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
