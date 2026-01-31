# TIPO DE ARQUIVO: RECEBE CSV

"""
================================================================================
ARQUITETURA DO TCC: SINCRONIZADOR DE FEEDBACK EXPLÍCITO (FOLLOW LOGIC)
================================================================================

Objetivo do Arquivo:
    Transformar o "comportamento implícito" (curtir música) em "sinal explícito"
    (seguir artista). Isso maximiza a personalização do algoritmo do Spotify.

Parte do Sistema:
    Collectors (Pós-Processamento de Persona).

Responsabilidades:
    1. Leitura: Varrer a biblioteca de "Músicas Curtidas" do usuário.
    2. Identificação: Extrair o Artista Principal (Main Artist) de cada faixa.
    3. Ação: Seguir automaticamente todos esses artistas.
    4. Performance: Processar em lotes (Batch) para evitar Rate Limit.

Comunicação:
    - Entrada: Biblioteca do Usuário autenticado.
    - Saída: Ação "Follow" na conta do Spotify.

Uso:
    python src/collectors/sync_persona_follows.py
"""
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import time
import os
import sys
from dotenv import load_dotenv

user_path = os.path.expanduser('~')
sys.path.append(os.path.join(user_path, 'OneDrive', 'Documentos', 'Pessoal', 'Projetos', 'TCC', 'src'))

# Carrega as variáveis do arquivo .env
load_dotenv()

# Escopos necessários para ler a biblioteca e modificar seguidores
SCOPE = "user-library-read user-follow-modify"

def sync_follows_from_liked_songs():
    """
    Função Principal.

    Lógica:
        1. Pagina por TODAS as músicas curtidas da conta.
        2. Acumula os IDs dos artistas em um conjunto (Set) para deduplicar.
        3. Envia comandos de follow em lotes de 50.
    """
    
    # Validação inicial de credenciais
    if not os.getenv("SPOTIPY_CLIENT_ID") or not os.getenv("SPOTIPY_CLIENT_SECRET"):
        print("\n[!] ERRO: Credenciais não encontradas.")
        print("Certifique-se de que o arquivo .env existe e contém as chaves.")
        return

    try:
        # Inicializa o cliente com OAuth
        sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=SCOPE))
        
        # Teste de conexão/usuário
        user = sp.current_user()
        print(f"\n{'='*60}")
        print(f"CONTA AUTENTICADA: {user['display_name']}")
        print(f"INICIANDO SINCRONIZAÇÃO DE SEGUIDORES")
        print(f"{'='*60}")

        artist_ids_to_follow = set()
        offset = 0
        limit = 50

        print("[1/2] Mapeando artistas principais das músicas curtidas...")

        # Loop de Paginação (Leitura)
        while True:
            results = sp.current_user_saved_tracks(limit=limit, offset=offset)
            items = results['items']
            
            if not items:
                break

            for item in items:
                track = item['track']
                # Pega apenas o primeiro artista da lista (o principal)
                # Ignora feats secundários para manter o foco do perfil
                if track['artists']:
                    main_artist_id = track['artists'][0]['id']
                    artist_ids_to_follow.add(main_artist_id)
            
            print(f" -> Processadas {offset + len(items)} músicas...")
            offset += limit
            
            if not results['next']:
                break

        if not artist_ids_to_follow:
            print("[-] Nenhuma música curtida encontrada.")
            return

        ids_list = list(artist_ids_to_follow)
        print(f"\n[2/2] Seguindo {len(ids_list)} artistas únicos no Spotify...")

        # Loop de Escrita (Follow em Lote)
        # Segue em blocos de 50 (limite da API)
        for i in range(0, len(ids_list), 50):
            batch = ids_list[i:i+50]
            sp.user_follow_artists(ids=batch)
            print(f" -> Lote {i//50 + 1}: OK")
            time.sleep(0.3)

        print(f"\n✅ SUCESSO: Sincronização concluída.")
        print(f"{'='*60}\n")

    except Exception as e:
        print(f"\n[!] OCORREU UM ERRO DURANTE A EXECUÇÃO:")
        print(f"Detalhes: {e}")

if __name__ == "__main__":
    sync_follows_from_liked_songs()