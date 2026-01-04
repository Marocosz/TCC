# gerar_resumos.py

import pandas as pd
import os
from collections import Counter

def formatar_duracao(segundos):
    """Converte segundos para um formato legível 'min:seg'."""
    if pd.isna(segundos):
        return "N/A"
    minutos = int(segundos // 60)
    segundos_restantes = int(segundos % 60)
    return f"{minutos}:{segundos_restantes:02}"

def main():
    """
    Função principal que carrega os dados de cada persona, calcula estatísticas
    e salva um resumo em um arquivo .txt em suas respectivas pastas.
    """
    # --- 1. PAINEL DE CONTROLE (CONFIGURAÇÕES) ---
    print("--- Iniciando a geração de resumos textuais por persona ---")
    
    ARQUIVOS_DAS_PERSONAS = {
        'beatriz': {
            'csv_path': 'beatriz/analise_Beatriz_playlist.csv',
            'output_folder': 'beatriz/'
        },
        'daniel': {
            'csv_path': 'daniel/analise_Daniel_playlist.csv',
            'output_folder': 'daniel/'
        },
        'ricardo': {
            'csv_path': 'ricardo/analise_Ricardo_playlist.csv',
            'output_folder': 'ricardo/'
        },
        'sofia': {
            'csv_path': 'sofia/analise_Sofia_playlist.csv',
            'output_folder': 'sofia/'
        }
    }

    # --- 2. LOOP DE GERAÇÃO DE RESUMOS PARA CADA PERSONA ---
    for persona, info in ARQUIVOS_DAS_PERSONAS.items():
        print(f"\n{'='*20} GERANDO RESUMO PARA: {persona.upper()} {'='*20}")
        
        csv_path = info['csv_path']
        output_folder = info['output_folder']
        output_path = os.path.join(output_folder, 'resumo_playlist.txt')

        os.makedirs(output_folder, exist_ok=True)

        try:
            df = pd.read_csv(csv_path)
            
            # --- Limpeza e preparação dos dados ---
            df['album_release_year'] = pd.to_datetime(df['album_release_date'], errors='coerce').dt.year
            df['track_popularity'] = pd.to_numeric(df['track_popularity'], errors='coerce')
            df['artist_popularity'] = pd.to_numeric(df['artist_popularity'], errors='coerce')
            df['duration_sec'] = pd.to_numeric(df.get('duration_ms'), errors='coerce') / 1000
            print(f"Arquivo '{csv_path}' carregado com sucesso.")
        except FileNotFoundError:
            print(f"ERRO: Arquivo '{csv_path}' não encontrado. Pulando esta persona.")
            continue

        # --- CÁLCULO DAS ESTATÍSTICAS ---
        
        total_musicas = len(df)
        artistas_unicos = df['primary_artist_name'].nunique()
        contagem_artistas = df['primary_artist_name'].value_counts()

        # MUDANÇA AQUI: Coleta TODOS os gêneros
        generos_validos = df['artist_genres'].dropna().astype(str)
        lista_de_todos_os_generos = [genre.strip() for item in generos_validos for genre in item.split(';') if genre.strip()]
        # A função .most_common() sem argumento retorna todos, já ordenados
        todos_os_generos_ordenados = Counter(lista_de_todos_os_generos).most_common()

        media_pop_musica = df['track_popularity'].mean()
        media_pop_artista = df['artist_popularity'].mean()
        ano_medio = df['album_release_year'].mean()
        ano_min = df['album_release_year'].min()
        ano_max = df['album_release_year'].max()
        duracao_media_seg = df['duration_sec'].mean()
        duracao_media_formatada = formatar_duracao(duracao_media_seg)

        # --- ESCRITA DO ARQUIVO .TXT ---
        print(f"  - Salvando resumo em '{output_path}'...")
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(f"=============== RESUMO DA PLAYLIST: {persona.upper()} ===============\n\n")
            f.write("--- MÉTRICAS GERAIS ---\n")
            f.write(f"Total de Músicas: {total_musicas}\n")
            f.write(f"Total de Artistas Únicos: {artistas_unicos}\n\n")
            f.write("--- MÉTRICAS DE POPULARIDADE ---\n")
            f.write(f"Popularidade Média das Músicas: {media_pop_musica:.2f} / 100\n")
            f.write(f"Popularidade Média dos Artistas: {media_pop_artista:.2f} / 100\n\n")
            f.write("--- MÉTRICAS TEMPORAIS (ERA MUSICAL) ---\n")
            f.write(f"Ano Médio de Lançamento: {ano_medio:.0f}\n")
            f.write(f"Música Mais Antiga (ano): {int(ano_min)}\n")
            f.write(f"Música Mais Nova (ano): {int(ano_max)}\n\n")
            f.write("--- MÉTRICAS ESTRUTURAIS ---\n")
            f.write(f"Duração Média das Músicas: {duracao_media_formatada}\n\n")

            # MUDANÇA AQUI: Título e loop para todos os gêneros
            f.write("--- LISTA COMPLETA DE GÊNEROS (por frequência) ---\n")
            for i, (genero, contagem) in enumerate(todos_os_generos_ordenados):
                # Adiciona '(s)' para lidar com o plural
                ocorrencia_str = "ocorrência" if contagem == 1 else "ocorrências"
                f.write(f"  {i+1}. {genero} ({contagem} {ocorrencia_str})\n")
            f.write("\n")

            f.write("--- CONCENTRAÇÃO DE ARTISTAS (Nº de Músicas por Artista) ---\n")
            for artista, contagem in contagem_artistas.items():
                f.write(f"  - {artista}: {contagem} música(s)\n")
        
        print(f"  -> Resumo para {persona.upper()} salvo com sucesso.")

    print(f"\n{'='*20} PROCESSO FINALIZADO {'='*20}")

if __name__ == "__main__":
    main()