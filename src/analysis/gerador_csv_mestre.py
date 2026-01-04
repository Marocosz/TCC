"""
Script Mestre para gerar relatórios de artistas por Persona.
Uso: 
    python gerador_csv_mestre.py beatriz
    python gerador_csv_mestre.py todas
"""

import sys
from src.functions import (
    extract_spotify_playlist_id,
    get_artists_from_playlist,
    get_full_artist_profiles,
    save_artists_to_csv
)

# --- CONFIGURAÇÃO DAS PERSONAS ---
# Aqui centralizamos todos os dados que antes estavam espalhados
PERSONAS = {
    "beatriz": {
        "urls": ["https://open.spotify.com/playlist/75hnyqmFAZHYN1cRdJY4aT?si=4e9ffb455e86415b"],
        "output": "beatriz/artistas_topbrasil_dados.csv"
    },
    "daniel": {
        "urls": [
            "https://open.spotify.com/playlist/30i868DlcfieGBVL4Mrb91?si=8023222c13ef44bc",
            "https://open.spotify.com/playlist/0S6kXHQLzzBEZjlB40ksXC?si=7b2ed3a17e734615",
            "https://open.spotify.com/playlist/2azWdvU6hhRcSjnAjO85RN?si=90f645a0282e47c3"
        ],
        "output": "daniel/artistas_lofi_dados.csv"
    },
    "ricardo": {
        "urls": [
            "https://open.spotify.com/playlist/5rehXNZUXxbia3eHmlcFz1?si=e1fa21a7534c4db4",
            "https://open.spotify.com/playlist/4uWqwCSd1Gb45U7QDgEPwf?si=baee1efb2a524ff9",
            "https://open.spotify.com/playlist/6hUvrs9p5b5pzQyYYbcTth?si=e9ab3e199edd4a88"
        ],
        "output": "ricardo/artistas_classicos_dados.csv"
    },
    "sofia": {
        "urls": [
            "https://open.spotify.com/playlist/2RxIuqmH1n5QCx0eUmmyCA?si=35f9751c7013485b",
            "https://open.spotify.com/playlist/6XLvNXM2WLHTFspl0KULxN?si=5c775ab067bd4aa2",
            "https://open.spotify.com/playlist/3Q4tfVNqIE3HTxz21W9SLi?si=d0d5fbde896540f1"
        ],
        "output": "sofia/artistas_indie_dados.csv"
    }
}

def executar_coleta(nome_persona):
    """Executa a lógica de coleta para uma persona específica."""
    config = PERSONAS.get(nome_persona.lower())
    
    if not config:
        print(f"ERRO: Persona '{nome_persona}' não encontrada.")
        return

    print(f"\n{'='*60}")
    print(f"INICIANDO COLETA: {nome_persona.upper()}")
    print(f"{'='*60}")

    all_unique_artists = {}

    for i, url in enumerate(config["urls"]):
        print(f"\n--- Processando playlist {i+1} de {len(config['urls'])} ---")
        playlist_id = extract_spotify_playlist_id(url)
        
        if not playlist_id:
            print(f"AVISO: ID inválido para URL: {url}")
            continue
        
        artists = get_artists_from_playlist(playlist_id)
        all_unique_artists.update(artists)
        print(f"Artistas únicos acumulados: {len(all_unique_artists)}")

    if not all_unique_artists:
        print(f"Nenhum artista encontrado para {nome_persona}.")
        return

    print("\nBuscando perfis detalhados e salvando CSV...")
    full_profiles = get_full_artist_profiles(all_unique_artists)
    save_artists_to_csv(full_profiles, config["output"], sort_by='popularity')
    
    print(f"\nSUCESSO: Relatório salvo em '{config['output']}'")

def main():
    # Verifica se o usuário passou algum argumento via terminal
    if len(sys.argv) < 2:
        print("\nUso correto:")
        print("  python gerador_csv_mestre.py [nome_da_persona]")
        print("  Exemplo: python gerador_csv_mestre.py beatriz")
        print("\nPersonas disponíveis:", ", ".join(PERSONAS.keys()))
        print("Ou use 'todas' para rodar o processo completo.")
        return

    escolha = sys.argv[1].lower()

    if escolha == "all":
        for persona in PERSONAS.keys():
            executar_coleta(persona)
    else:
        executar_coleta(escolha)

if __name__ == "__main__":
    main()