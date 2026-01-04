# merge_datasets.py

"""
================================================================================
MÓDULO DE CONSOLIDAÇÃO DE DADOS (MERGE)
================================================================================

OBJETIVO DO ARQUIVO:
    Unificar os datasets individuais de cada Persona em um único arquivo CSV mestre.
    Isso é essencial para permitir análises comparativas e a geração de gráficos
    que cruzam dados de diferentes perfis (ex: Boxplot comparativo).

RESPONSABILIDADES:
    1. Leitura Múltipla: Iterar sobre uma lista de arquivos CSV de entrada.
    2. Normalização: Adicionar uma coluna identificadora ('persona') para rastrear
       a origem de cada linha no arquivo consolidado.
    3. Fusão: Concatenar todos os registros em uma única estrutura tabular.
    4. Persistência: Salvar o resultado como um novo CSV consolidado.

COMUNICAÇÃO:
    - Entrada: Lê múltiplos arquivos 'dataset_NOME.csv' de 'data/processed/'.
    - Saída: Gera 'analise_consolidada_input.csv' na mesma pasta.
    - Consumidor: Este arquivo final é lido pelo script 'gerar_graficos.py'.
================================================================================
"""

import csv
import os

def consolidar_csvs_de_personas(arquivos_de_entrada: dict, arquivo_de_saida: str):
    """
    Processa e funde múltiplos arquivos CSV em um só.

    Lógica de Negócio:
        - O arquivo consolidado DEVE ter uma coluna extra chamada 'persona'.
        - Essa coluna serve como chave categórica (Hue) para os gráficos do Seaborn.
        - Se um arquivo de entrada não existir, o script avisa mas não quebra,
          continuando com os outros (tolerância a falhas parciais).

    Args:
        arquivos_de_entrada (dict): Dicionário { 'nome_persona': 'caminho_arquivo.csv' }.
        arquivo_de_saida (str): Caminho onde o CSV consolidado será salvo.
    """
    print("--- Iniciando a consolidação dos arquivos CSV ---")
    
    dados_consolidados = []
    headers = [] # Armazena o cabeçalho do primeiro arquivo válido encontrado
    
    for persona, nome_arquivo in arquivos_de_entrada.items():
        print(f"Processando o arquivo da persona '{persona}': {nome_arquivo}")
        
        # Validação de existência do arquivo (Evita Crash)
        if not os.path.exists(nome_arquivo):
            print(f"  AVISO: O arquivo '{nome_arquivo}' não foi encontrado. Pulando...")
            continue
            
        try:
            with open(nome_arquivo, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                # Captura os cabeçalhos apenas na primeira iteração bem-sucedida
                if not dados_consolidados and not headers:
                    headers = reader.fieldnames
                
                # Iteração linha a linha para enriquecimento
                for linha in reader:
                    # Regra de Negócio: Injeção da coluna identificadora
                    linha['persona'] = persona
                    dados_consolidados.append(linha)
            
            print(f"  Sucesso! Arquivo processado.")
            
        except Exception as e:
            print(f"  ERRO ao processar o arquivo '{nome_arquivo}': {e}")

    # Verificação de segurança: Não gerar arquivo vazio
    if not dados_consolidados:
        print("Nenhum dado foi coletado. O arquivo consolidado não será criado.")
        return
        
    # Reorganização de colunas: Força 'persona' a ser a primeira coluna (melhor leitura)
    # headers pode ser None se o arquivo estiver vazio, então usamos um fallback
    cols_originais = headers if headers else list(dados_consolidados[0].keys())
    # Remove 'persona' se ela já existir por algum motivo para evitar duplicação
    cols_originais = [h for h in cols_originais if h != 'persona']
    
    cabecalhos_finais = ['persona'] + cols_originais

    print(f"\nSalvando um total de {len(dados_consolidados)} registros no arquivo '{arquivo_de_saida}'...")
    
    try:
        # Garante que a pasta de destino exista
        os.makedirs(os.path.dirname(arquivo_de_saida), exist_ok=True)

        with open(arquivo_de_saida, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=cabecalhos_finais)
            writer.writeheader()
            writer.writerows(dados_consolidados)
        
        print(f"\n--- SUCESSO! Arquivo '{arquivo_de_saida}' criado com todos os dados consolidados. ---")
        
    except Exception as e:
        print(f"  ERRO ao salvar o arquivo consolidado: {e}")

# --- SEÇÃO PRINCIPAL (CONFIGURAÇÃO E EXECUÇÃO) ---
if __name__ == '__main__':
    # Mapeamento de Entrada:
    # Define quais arquivos compõem o estudo.
    # ATUALIZAÇÃO: Caminhos relativos ajustados para a pasta 'src/analysis/'
    ARQUIVOS_DAS_PERSONAS = {
        'beatriz': '../../data/processed/dataset_Beatriz_playlist.csv',
        'daniel': '../../data/processed/dataset_Daniel_playlist.csv',
        'ricardo': '../../data/processed/dataset_Ricardo_playlist.csv',
        'sofia': '../../data/processed/dataset_Sofia_playlist.csv'
    }
    
    # Arquivo de Saída:
    # O arquivo consolidado é salvo na mesma pasta dos processados.
    ARQUIVO_FINAL = "../../data/processed/analise_consolidada_input.csv"
    
    # Execução
    consolidar_csvs_de_personas(ARQUIVOS_DAS_PERSONAS, ARQUIVO_FINAL)