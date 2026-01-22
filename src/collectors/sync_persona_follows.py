"""
================================================================================
ARQUITETURA DO TCC: SINCRONIZADOR DE FEEDBACK EXPLÍCITO (FOLLOW LOGIC)
================================================================================
Ideia Central:
Este script varre a biblioteca de "Músicas Curtidas" (Liked Songs) da conta 
autenticada e segue automaticamente o artista principal de cada faixa.

Diferenciais Técnicos:
1. Foco no Artista Principal: Segue apenas o artista primário da faixa para 
   garantir a pureza do nicho da Persona e evitar ruídos de "feats".
2. Paginação Automática: Lida com bibliotecas de qualquer tamanho (50 em 50).
3. Batch Processing: Otimiza as chamadas de API seguindo artistas em blocos de 50.
4. Identidade de Persona: Garante que o algoritmo de IA do Spotify receba 
   sinais claros de preferência para estabilizar o perfil da Persona.

Escopos Necessários: 
- user-library-read
- user-follow-modify
================================================================================
"""
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import time
import os
from dotenv import load_dotenv

# Carrega as variáveis do arquivo .env
load_dotenv()

# Escopos necessários para ler a biblioteca e modificar seguidores
SCOPE = "user-library-read user-follow-modify"

def sync_follows_from_liked_songs():
    """
    Recupera todas as músicas curtidas e segue o artista principal de cada uma.
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

        while True:
            results = sp.current_user_saved_tracks(limit=limit, offset=offset)
            items = results['items']
            
            if not items:
                break

            for item in items:
                track = item['track']
                # Pega apenas o primeiro artista da lista (o principal)
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