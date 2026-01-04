# consolidar_dados.py

import csv
import os

def consolidar_csvs_de_personas(arquivos_de_entrada: dict, arquivo_de_saida: str):
    """
    Junta múltiplos arquivos CSV de playlists em um único arquivo,
    adicionando uma coluna 'persona' para identificar a origem de cada linha.
    """
    print("--- Iniciando a consolidação dos arquivos CSV ---")
    
    dados_consolidados = []
    
    for persona, nome_arquivo in arquivos_de_entrada.items():
        print(f"Processando o arquivo da persona '{persona}': {nome_arquivo}")
        
        if not os.path.exists(nome_arquivo):
            print(f"  AVISO: O arquivo '{nome_arquivo}' não foi encontrado. Pulando...")
            continue
            
        try:
            with open(nome_arquivo, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                # 'headers' serão as colunas do primeiro arquivo lido
                if not dados_consolidados:
                    headers = reader.fieldnames
                
                for linha in reader:
                    linha['persona'] = persona
                    dados_consolidados.append(linha)
            
            print(f"  Sucesso! Arquivo processado.")
            
        except Exception as e:
            print(f"  ERRO ao processar o arquivo '{nome_arquivo}': {e}")

    if not dados_consolidados:
        print("Nenhum dado foi coletado. O arquivo consolidado não será criado.")
        return
        
    # Garante que a coluna 'persona' seja a primeira
    cabecalhos = ['persona'] + [h for h in headers if h != 'persona']

    print(f"\nSalvando um total de {len(dados_consolidados)} registros no arquivo '{arquivo_de_saida}'...")
    try:
        with open(arquivo_de_saida, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=cabecalhos)
            writer.writeheader()
            writer.writerows(dados_consolidados)
        
        print(f"\n--- SUCESSO! Arquivo '{arquivo_de_saida}' criado com todos os dados consolidados. ---")
        
    except Exception as e:
        print(f"  ERRO ao salvar o arquivo consolidado: {e}")

# --- SEÇÃO PRINCIPAL PARA EXECUTAR O SCRIPT ---
if __name__ == '__main__':
    # --- CONFIGURE AQUI ---
    # Mapeia o nome da persona para o CAMINHO COMPLETO e NOME EXATO do arquivo CSV.
    ARQUIVOS_DAS_PERSONAS = {
        'beatriz': 'beatriz/analise_Beatriz_playlist.csv',
        'daniel': 'daniel/analise_Daniel_playlist.csv',
        'ricardo': 'ricardo/analise_Ricardo_playlist.csv',
        'sofia': 'sofia/analise_Sofia_playlist.csv'
    }
    
    # Nome do arquivo final que será gerado.
    ARQUIVO_FINAL = "analise_consolidada_input.csv"
    
    # Roda a função principal
    consolidar_csvs_de_personas(ARQUIVOS_DAS_PERSONAS, ARQUIVO_FINAL)