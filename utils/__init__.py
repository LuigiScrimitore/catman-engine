import yaml

from utils.sales_loader import (
    load_filtered_sales_parquet,
    smart_load_to_pd,
    get_sales_files,
)

CONFIG_FILE = "./config/configurazioni.yaml"
CATEGORIE_FILE = "./config/categorie.yaml"
DB_FILE = "./config/db_config.yaml"
PIPELINE_FILE = "./config/pipeline.yaml"
CONVERSIONI_FILE = "./config/conversioni.yaml"

def get_config_general(file_path):
    try:
        with open(file_path, "r", encoding='utf-8') as f:
            config = yaml.safe_load(f)
        return config
    except FileNotFoundError:
        print(f"ERRORE: File di configurazione '{file_path}' non trovato.")
        return []

def get_Categorie():
    return get_config_general(CATEGORIE_FILE)['cat_to_run']

def get_Config():
    return get_config_general(CONFIG_FILE)

def get_Config_Colonne():
    return get_config_general(CONFIG_FILE)['colnames']

def get_Config_path():
    return get_config_general(CONFIG_FILE)['paths']

def get_DB_Config():
    return get_config_general(DB_FILE)['params']

def get_DB_tabelle():
    return get_config_general(DB_FILE)['tabelle']


def get_DB_Mapping():
    config_completo = get_config_general(DB_FILE)
    # Usa .get() per evitare errori se la chiave non esiste
    return config_completo.get('output_mapping', {})

def get_PipelineList():
    return get_config_gen