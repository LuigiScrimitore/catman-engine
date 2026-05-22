import os
import re
from sqlalchemy import create_engine, text
import pandas as pd
import utils as utl
import time
import numpy as np
import oracledb


# ==========================================
# FUNZIONI DI SUPPORTO E CONNESSIONE
# ==========================================

def _get_engine(schema=None):
    """Crea e restituisce l'engine SQLAlchemy per la connessione."""
    # IMPORTANTE: utl.get_DB_Config() restituisce GIA' il dizionario dei parametri!
    db_config = utl.get_DB_Config()

    # Se non viene passato uno schema specifico, usa quello di default
    user = schema if schema else db_config['user']
    password = schema if schema else db_config['password']

    connection_uri = (
        f"oracle+oracledb://{user}:{password}@"
        f"{db_config['host']}:{db_config['port']}/?service_name={db_config['service_name']}"
    )
    return create_engine(connection_uri, arraysize=db_config.get('array_size', 100000))


# ==========================================
# FUNZIONI DI SCRITTURA (CON MAPPING)
# ==========================================
def write_dataframe_to_oracle(df, table_config, schema=None):
    """
    Scrive un singolo DataFrame in una tabella Oracle pre-esistente,
    applicando il mapping delle colonne e pulendo i dati spuri.
    """
    engine = _get_engine(schema)

    table_name = table_config.get('table_name')
    column_mapping = table_config.get('column_mapping')

    if not table_name or not column_mapping:
        print(f"❌ Configurazione tabella o mapping mancante.")
        return

    # 1. Rinomina le colonne e filtra solo quelle da mantenere
    df_mapped = df.rename(columns=column_mapping)
    cols_to_keep = list(column_mapping.values())
    valid_cols = [col for col in cols_to_keep if col in df_mapped.columns]
    df_mapped = df_mapped[valid_cols]

    # ========================================================
    # 2. DATA CLEANING ROBUSTO PER ORACLE (Previene DPY-4004)
    # ========================================================
    print(f"\t-> Pulizia dati per compatibilità Oracle in corso...")

    # A) Sostituiamo gli infiniti matematici con NaN
    df_mapped = df_mapped.replace([np.inf, -np.inf], np.nan)

    # B) Cerchiamo finti nulli (stringhe) e li forziamo a NaN
    for col in df_mapped.columns:
        if df_mapped[col].dtype == object:
            df_mapped[col] = df_mapped[col].apply(
                lambda x: np.nan if isinstance(x, str) and x.strip().lower() in ['', 'nan', 'n/a', 'none',
                                                                                 'null'] else x
            )

    # C) Passaggio magico: trasforma tutti i NaN/NaT di Pandas in None nativi di Python.
    # SQLAlchemy capisce che None significa "inserisci NULL nel database".
    df_mapped = df_mapped.where(pd.notnull(df_mapped), None)
    # ========================================================

    try:
        start_time = time.time()
        print(f"\t-> Svuotamento tabella {table_name}...")

        with engine.begin() as conn:
            conn.execute(text(f"TRUNCATE TABLE {table_name}"))

        print(f"\t-> Inserimento di {len(df_mapped)} righe in {table_name}...")

        schema_name = table_name.split('.')[0] if '.' in table_name else None
        table_name_only = table_name.split('.')[-1].lower()

        df_mapped.to_sql(
            name=table_name_only,
            schema=schema_name,
            con=engine,
            if_exists='append',
            index=False,
            chunksize=50000
        )

        print("\t✅ Tabella %s scritta in %.1f secondi." % (table_name, time.time() - start_time))
    except Exception as e:
        print(f"\t❌ Errore durante la scrittura della tabella {table_name}: {e}")

def write_all_results_to_db(res_dict):
    """
    Prende in input il dizionario 'res' (Key=NomeFoglio, Value=DataFrame)
    e lo scrive nel DB usando il mapping presente in db_config.yaml.
    """
    mapping_config = utl.get_DB_Mapping()

    if not mapping_config:
        print("⚠️ Nessun 'output_mapping' trovato nel db_config.yaml. Scrittura su DB saltata.")
        return

    print(f"✅ Inizio scrittura su Database (trovati {len(mapping_config)} mapping)...")

    for sheet_name, df in res_dict.items():
        if sheet_name in mapping_config:
            table_config = mapping_config[sheet_name]
            print(f" Elaborazione output: '{sheet_name}'")
            write_dataframe_to_oracle(df, table_config)
        else:
            print(f"⚠️ Nessun mapping DB trovato per il foglio '{sheet_name}'. Salto l'inserimento.")


# ==========================================
# FUNZIONI DI LETTURA (LE TUE ORIGINALI)
# ==========================================
def getAllDataFromTable(tabella: str, schema: str):
    sql_query = f"SELECT * FROM {tabella}"
    return getDataFromQuery(sql_query, schema)


def getDataFromQuery(sql_query: str, schema: str):
    try:
        engine = _get_engine(schema)
        df = pd.read_sql_query(sql_query, engine)
        return df
    except Exception as e:
        print(f"❌ Si è verificato un errore in lettura: {e}")


def getTableCount(nomeTabella: str, schema: str):
    sql_query = 'SELECT COUNT(*) AS NUM_RIGHE FROM ' + nomeTabella
    return getDataFromQuery(sql_query, schema)


def getTableIntoCsv_by_Chunk(tableName: str, schema: str, output_file: str):
    db_config = utl.get_DB_Config()
    try:
        engine = _get_engine(schema)
        sql_query = 'select * from ' + tableName

        first_chunk = True
        cnt = 1
        for chunk in pd.read_sql(sql_query, engine, chunksize=db_config['chunk_size']):
            if first_chunk:
                chunk.columns = chunk.columns.str.upper()
                chunk.to_csv(output_file, index=False, sep=';', decimal='.', encoding='latin-1', header=True)
                first_chunk = False
            else:
                chunk.to_csv(output_file, index=False, sep=';', decimal='.', encoding='latin-1', mode='a', header=False)
            print(f"Scritto un blocco numero {cnt} di {len(chunk)} righe...")
            cnt = cnt + 1
    except Exception as e:
        print(f"❌ Si è verificato un errore nel chunking: {e}")


def getDBTableIntoCSV(nomeTabella: str, schema: str):
    print("\t" + nomeTabella + ":")
    db_config = utl.get_DB_Config()
    nomeFile = db_config['output_path'] + nomeTabella + '.csv'

    dfCount = getTableCount(nomeTabella, schema)
    numRighe = dfCount['num_righe'][0]

    if numRighe < 7000000:
        df = getAllDataFromTable(nomeTabella, schema)
        if not df.shape:
            print("\t\t" + "tabella vuota.")
        else:
            print("\t\t" + "righe totali lette:", df.shape)

        df.columns = df.columns.str.upper()
        df.to_csv(nomeFile, index=False, sep=';', decimal='.', encoding='latin-1')
    else:
        print(f"BIG TABLE! Contiene {numRighe} righe!")
        getTableIntoCsv_by_Chunk(nomeTabella, schema, nomeFile)


def downloadDataFromDB():
    elenco_tabelle = utl.get_DB_tabelle()
    print(f"Trovate", len(elenco_tabelle), "tabelle da scaricare.")
    for i, tabella in enumerate(elenco_tabelle, 1):
        start = time.time()
        nome_tabella = tabella.split(".")
        schema = nome_tabella[0]
        tab = nome_tabella[1]
        getDBTableIntoCSV(tab, schema)
        print("\t\t" + "✅ Tabella estratta in %.1f secondi." % (time.time() - start))
        print()


if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("▶️  inizio download dati dal db")
    print("=" * 50)
    startDownload = time.time()
    downloadDataFromDB()
    print('Fine download dati dal db in %.1f minuti.' % ((time.time() - startDownload) / 60))
    print("=" * 50)