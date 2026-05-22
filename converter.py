# -*- coding: utf-8 -*-
import time
import pandas as pd
from tableauhyperapi import TableName
import pantab as pt
import utils as utl

def trasformazioniDiColonna(df, config):
    # applica delle funzioni lambda di trasformazione per le colonne:
    # trasformazioni_colonne
    transforms = config.get('trasformazioni', [])
    if transforms:
        for regola in transforms:
            colonna = regola['colonna']
            funzione_str = regola['funzione']
            if colonna in df.columns:
                print(f"Applico la funzione sulla colonna '{colonna}': {funzione_str}")
                # Usa eval() per convertire la stringa in una funzione eseguibile
                funzione_lambda = eval(funzione_str)
                df[colonna] = df[colonna].apply(funzione_lambda)
            else:
                print(f"Attenzione: colonna '{colonna}' non trovata.")

def renameColonne(df, config):
    print("rename to be implemented")

# funzione che esporta da csv in csv
def csvToCsv(nomeFile:str):
    conf = utl.get_Conversioni()[nomeFile]

    nomeFileInput = conf.get('input_file')
    print("\t\t" + "lettura file di input:"+conf.get('input_file'))
    df = pd.read_csv(nomeFileInput,sep=';',low_memory=False,encoding="latin1")

    # # Sostituzione delle intestazioni
    rename_map = conf.get('rename_colonne', {})  # Default a dizionario vuoto
    if rename_map:
        # print (f"remap:",rename_map)
        df.rename(columns=rename_map, inplace=True)
    # print(df.shape)

    # # Elimino le colonne inutili
    drop_cols = conf.get('colonne_da_togliere', [])
    # print (f"colonne da togliere:",drop_cols)
    if drop_cols:
        #df.drop(drop_cols, axis=1, inplace=True)
        df.drop(columns=drop_cols, inplace=True, errors='ignore')
    # print(df.shape)

    # # correzione tipi di alcune colonne
    type_map = conf.get('tipi_colonne', {})
    # print(f"cambio tipo:",type_map)
    if type_map:
        for col, dtype in type_map.items():
            try:
                df[col] = df[col].astype(dtype)
            except Exception as e:
                print(f"  - Impossibile convertire la colonna '{col}' a '{dtype}': {e}")

    trasformazioniDiColonna(df, conf)

    nomeFileOutput = conf.get('output_file')
    df.to_csv(nomeFileOutput, sep=';', index=False)
    print("\t\t"+"file di output generato:"+ nomeFileOutput)

def csvToHyper(nomeFile:str):
    conf = utl.get_Conversioni()[nomeFile]

    nomeFileInput = conf.get('input_file')
    print("\t\t"+f"lettura file di input:",nomeFileInput)
    df = pd.read_csv(nomeFileInput, sep=';', low_memory=True, encoding="latin1")

    # # Sostituzione delle intestazioni
    rename_map = conf.get('rename_colonne', {})
    df.rename(columns=rename_map, inplace=True)
    # print(df.shape)

    # # Elimino le colonne inutili
    drop_cols = conf.get('colonne_da_togliere', [])
    #print (f"colonne da togliere:",drop_cols)
    if drop_cols:
        #df.drop(drop_cols, axis=1, inplace=True)
        df.drop(columns=drop_cols, inplace=True, errors='ignore')
    # print(df.shape)

    trasformazioniDiColonna(df, conf)

    # # correzione tipi di alcune colonne
    type_map = conf.get('tipi_colonne', {})
    # print(f"cambio tipo:",type_map)
    if type_map:
        for col, dtype in type_map.items():
            try:
                df[col] = df[col].astype(dtype)
            except Exception as e:
                print(f"  - Impossibile convertire la colonna '{col}' a '{dtype}': {e}")

    nomeFileOutput = conf.get('output_file')
    table = TableName("Extract", "Extract")
    params = {"default_database_version": "1"}
    # encodings = {"default_database_version": "1"}
    pt.frame_to_hyper(df, nomeFileOutput, table=table, process_params=params)
    print("\t\t"+"file di output generato:"+ nomeFileOutput)

    # Processo di creazione del file Hyper
    # with HyperProcess(telemetry=Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU) as hyper:
    #     with Connection(endpoint=hyper.endpoint, database=output_file, create_mode='create_and_replace') as connection:
    #         table_name = TableName("data")
    #
    #         # Crea la definizione della tabella Hyper a partire dal DataFrame
    #         table_definition = TableDefinition(
    #             table_name,
    #             # Converte i tipi di colonna di pandas in tipi SQL di Hyper
    #             [TableDefinition.Column(col, SqlType.text()) for col in df.columns]
    #         )
    #
    #         connection.catalog.create_table(table_definition)
    #
    #         # Inserisci i dati
    #         with Inserter(connection, table_definition) as inserter:
    #             # Converte il DataFrame in una lista di tuple per l'inserimento
    #             data_to_insert = [tuple(row) for row in df.itertuples(index=False, name=None)]
    #             inserter.add_rows(data_to_insert)
    #             inserter.execute()

def csvToExcel(nomeFile:str):
    print('to be implemented')

def csvToParquet(nomeFile:str):
    # print('to be implemented')
    # pd.read_parquet("../scripts/New_dataZipped/scont_l2y_015.parquet").to_csv('./scontrinato_015.csv', sep=';')
    conf = utl.get_Conversioni()[nomeFile]

    nomeFileInput = conf.get('input_file')
    print("\t\t" + "lettura file di input:"+conf.get('input_file'))
    df = pd.read_csv(nomeFileInput,sep=';',low_memory=False,encoding="latin1")

    # # Sostituzione delle intestazioni
    rename_map = conf.get('rename_colonne', {})  # Default a dizionario vuoto
    if rename_map:
        # print (f"remap:",rename_map)
        df.rename(columns=rename_map, inplace=True)
    # print(df.shape)

    # # Elimino le colonne inutili
    drop_cols = conf.get('colonne_da_togliere', [])
    # print (f"colonne da togliere:",drop_cols)
    if drop_cols:
        #df.drop(drop_cols, axis=1, inplace=True)
        df.drop(columns=drop_cols, inplace=True, errors='ignore')
    # print(df.shape)

    # # correzione tipi di alcune colonne
    type_map = conf.get('tipi_colonne', {})
    # print(f"cambio tipo:",type_map)
    if type_map:
        for col, dtype in type_map.items():
            try:
                df[col] = df[col].astype(dtype)
            except Exception as e:
                print(f"  - Impossibile convertire la colonna '{col}' a '{dtype}': {e}")

    trasformazioniDiColonna(df, conf)

    nomeFileOutput = conf.get('output_file')
    df.to_parquet(nomeFileOutput, index=False)
    print("\t\t"+"file di output generato:"+ nomeFileOutput)




def convertAllData():
    conf = utl.get_Conversioni()
    conversioni_attive = conf['conversioni_attive']
    print(f"Trovati",len(conversioni_attive),"file da convertire.")

    for file in conversioni_attive:
        tipo_output = conf[file]["output_estensione"]
        print("\t"+file, "->", tipo_output)
        match tipo_output:
            case "csv":
                csvToCsv(file)
                #print("csv to csv")
            case "hyper":
                csvToHyper(file)
                #print("csv to hyper")
            case "excel":
                csvToExcel(file)
            case "parquet":
                csvToParquet(file)
            case _:
                csvToCsv(file)
        print()

def convert_lookup_PDV():
    print("corregge l'anagrafica dei pdv")
    paths = utl.get_Config_path()
    input_path = paths

    # df['REGIONE'] = df['REGIONE'].apply(lambda x: str(x).split('.', 1)[1].strip())

if __name__ == "__main__":

    print("\n" + "=" * 50)
    print("▶️  inizio generazione file per Pipeline e Tableau")
    print("=" * 50)

    startConversion = time.time()

    convertAllData()

    print('Fine generazione file in %.1f minuti.'  % ((time.time() - startConversion)/60))
    print("=" * 50)