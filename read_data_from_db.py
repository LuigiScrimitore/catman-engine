import os

from sqlalchemy import create_engine
import pandas as pd
import utils as utl
import time
import oracledb

def getAllDataFromTable(tabella:str, schema:str):
    sql_query = f"SELECT * FROM {tabella}"
    #sql_query = sql_query + " where rownum<1000000 " #inserito per test rapidi
    # print (sql_query)
    return getDataFromQuery(sql_query, schema)

def getDataFromQuery(sql_query:str, schema:str):
    db_config = utl.get_DB_Config()
    try:
        # Creazione della URI di connessione per SQLAlchemy
        # La stringa ha un formato: dialect+driver://username:password@host:port/service_name
        connection_uri = (
            # f"oracle+oracledb://{db_config['user']}:{db_config['password']}@"
            f"oracle+oracledb://{schema}:{schema}@"
            f"{db_config['host']}:{db_config['port']}/?service_name={db_config['service_name']}"
        )
        #print("connection_uri:", connection_uri)

        # print (connection_uri)

        # Creazione dell'engine di SQLAlchemy
        #print(f"Creazione dell'engine SQLAlchemy per Oracle...",connection_uri)
        engine = create_engine(connection_uri, arraysize=db_config['array_size'])

        #print(f"Esecuzione della query e caricamento nel DataFrame...", sql_query)
        df = pd.read_sql_query(sql_query, engine)

        # # Questo ciclo legge i dati da Oracle a blocchi
        # for chunk in pd.read_sql(sql_query, engine, chunksize=chunk_size):
        #     if first_chunk:
        #         # Il primo blocco crea il file e scrive l'intestazione (i nomi delle colonne)
        #         chunk.to_csv(output_file, index=False, mode='w', header=True)
        #         first_chunk = False
        #     else:
        #         # I blocchi successivi vengono aggiunti (append) allo stesso file, senza intestazione
        #         chunk.to_csv(output_file, index=False, mode='a', header=False)
        #
        #     print(f"Scritto un blocco di {len(chunk)} righe...")

        # print("\nDataFrame creato con successo!")
        return df

    except Exception as e:
        print(f"❌ Si è verificato un errore: {e}")

def getTableCount(nomeTabella:str, schema:str):
    sql_query = 'SELECT COUNT(*) AS NUM_RIGHE FROM '+nomeTabella
    return getDataFromQuery(sql_query, schema)

def getTableIntoCsv_by_Chunk(tableName:str, schema:str, output_file:str):

    db_config = utl.get_DB_Config()
    try:
        # Creazione della URI di connessione per SQLAlchemy
        # La stringa ha un formato: dialect+driver://username:password@host:port/service_name
        connection_uri = (
            # f"oracle+oracledb://{db_config['user']}:{db_config['password']}@"
            f"oracle+oracledb://{schema}:{schema}@"
            f"{db_config['host']}:{db_config['port']}/?service_name={db_config['service_name']}"
        )

        # print (connection_uri)

        # Creazione dell'engine di SQLAlchemy
        #print(f"Creazione dell'engine SQLAlchemy per Oracle...",connection_uri)
        engine = create_engine(connection_uri, arraysize=db_config['array_size'])

        sql_query = 'select * from '+tableName

        first_chunk = True
        cnt = 1
        for chunk in pd.read_sql(sql_query, engine, chunksize=db_config['chunk_size']):
            if first_chunk:
                # Il primo blocco crea il file e scrive l'intestazione (i nomi delle colonne)
                chunk.columns = chunk.columns.str.upper()
                chunk.to_csv(output_file, index=False, sep=';', decimal='.', encoding='latin-1', header=True)
                first_chunk = False
            else:
                # I blocchi successivi vengono aggiunti (append) allo stesso file, senza intestazione
                chunk.to_csv(output_file, index=False, sep=';', decimal='.', encoding='latin-1', mode='a', header=False)

            print(f"Scritto un blocco numero {cnt} di {len(chunk)} righe...")
            cnt= cnt+1

    except Exception as e:
        print(f"❌ Si è verificato un errore: {e}")

def getDBTableIntoCSV(nomeTabella:str, schema:str):
    # print('estrazione dati da tabella:'+nomeTabella)
    print("\t" + nomeTabella + ":")
    nomeFile = utl.get_DB_Config()['output_path'] + nomeTabella + '.csv'

    dfCount = getTableCount(nomeTabella, schema)
    numRighe = dfCount['num_righe'][0]

    if numRighe < 7000000:
        df = getAllDataFromTable(nomeTabella, schema)
        if not df.shape:
            print("\t\t"+"tabella vuota.")
        else:
            print("\t\t"+"righe totali lette:", df.shape)

        df.columns = df.columns.str.upper()
        df.to_csv(nomeFile, index=False, sep=';', decimal='.', encoding='latin-1')
    else:
        print(f"BIG TABLE! Contiene {numRighe} righe!" )
        getTableIntoCsv_by_Chunk(nomeTabella, schema, nomeFile)

def downloadSales(tableName:str, schema:str):
    db_config = utl.get_DB_Config()

    # estrazione lista delle cat_merc disponibili
    sql_query = (f"select distinct CATEG_MERC_PDV_COD as CATEGORIE, ANNO_MESE "
                 f"from {tableName} "
                 f"where CATEG_MERC_PDV_COD<='099' "
                 f"order by 1")
    df = getDataFromQuery(sql_query, schema)
    # print(categorie)
    categorie = df['categorie'].unique()

    for cat in categorie:
        # print(cat)
        salesCatPath = db_config['sales_path']
        # salesCatPath = db_config['sales_path']+"/"+cat
        # if not os.path.exists(salesCatPath):
        #     os.makedirs(salesCatPath)
        #     print(f"Creata cartella {salesCatPath} per la categoria: {cat}")

        # Ottieni i mesi unici per questa categoria
        mesi = df[df['categorie'] == cat]['anno_mese'].sort_values(ascending=False).unique()

        for mese in mesi:
            # print(mese)
            # salesFileNameCsv = salesCatPath+"/SALES_"+str(cat)+"_"+str(mese)+".csv"
            salesFileNamePqt = salesCatPath+"/SALES_"+str(cat)+"_"+str(mese)+".parquet"
            print(salesFileNamePqt)

            sql_query = (f"select * "
                         f"from {tableName} "
                         f"WHERE CATEG_MERC_PDV_COD='{cat}'"
                         f" AND ANNO_MESE = '{mese}'"
                         f"order by 1")
            res = getDataFromQuery(sql_query, schema)
            # res.to_csv(salesFileNameCsv, index=False, sep=';', decimal='.', encoding='latin-1')
            res.to_parquet(salesFileNamePqt, index=False)

def downloadDataFromDB():

    elenco_tabelle = utl.get_DB_tabelle()
    print(f"Trovate", len(elenco_tabelle), "tabelle da scaricare." )

    for i, tabella in enumerate(elenco_tabelle, 1):
        #
        start = time.time()
        nome_tabella = tabella.split(".")
        schema = nome_tabella[0]
        tab = nome_tabella[1]

        # print("schema "+ schema+": tabella da scaricare: " + tab )
        getDBTableIntoCSV(tab, schema)
        print("\t\t"+"✅ Tabella estratta in %.1f secondi." % (time.time() - start))
        print()


if __name__ == "__main__":

    print("\n" + "=" * 50)
    print("▶️  inizio download dati dal db")
    print("=" * 50)

    startDownload = time.time()
    downloadDataFromDB()
    # downloadSales('V_FT_SALES_CATMAN', 'CDT_DWH_EDW')

    print('Fine download dati dal db in %.1f minuti.'  % ((time.time() - startDownload)/60))
    print("=" * 50)

    # tabella = 'ODS_DMV_BAIN_LU_PDV_CATMAN'
    # getDBTableIntoCSV(tabella)


