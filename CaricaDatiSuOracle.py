import pandas as pd
import oracledb
import csv
import sys
import numpy as np


# Configurazione
BATCH_SIZE = 100000


# ==========================================
# CONFIGURAZIONI DATABASE
# ==========================================
DB_SRC = {
    "user": "CDT_DM_VENDITE",
    "password": "CDT_DM_VENDITE",
    "dsn": "exa01-scan1.conaddeltirreno.it:1521/cdtdw"
}

DB_TGT = {
    "user": "intowner",
    "password": "ikb2013",
    "dsn": "clucndpdb-scan.conaddeltirreno.it:1521/SEDE2PRD"  # host:port/service_name
}

TABELLA_ORIGINE = "ET_PIUME_ECR_2425"
TABELLA_DESTINAZIONE = "ET_PIUME_ECR_2425"
FILE_CSV = "ET_PIUME_ECR_2425_pulito.csv"


# ==========================================

def oracle_to_csv():
    print("1. Inizio estrazione dati da Oracle (Origine)...")
    try:
        conn = oracledb.connect(**DB_SRC)
        cursor = conn.cursor()

        cursor.execute(f"SELECT * FROM {TABELLA_ORIGINE}")

        # Recuperiamo i nomi delle colonne dinamicamente
        col_names = [col[0] for col in cursor.description]

        # Apriamo il file CSV in scrittura usando il PIPE (|) come separatore
        with open(FILE_CSV, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f, delimiter='|', quoting=csv.QUOTE_MINIMAL)
            writer.writerow(col_names)

            # Scarichiamo e scriviamo i dati a blocchi (batch) per non saturare la RAM
            righe_estratte = 0
            while True:
                rows = cursor.fetchmany(5000)
                if not rows:
                    break
                writer.writerows(rows)
                righe_estratte += len(rows)

        print(f"--> Estrazione completata: {righe_estratte} righe salvate in '{FILE_CSV}'.")

    except Exception as e:
        print(f"Errore bloccante durante l'estrazione: {e}")
        raise  # Ferma lo script se l'estrazione fallisce
    finally:
        if 'conn' in locals():
            conn.close()


def csv_to_oracle():
    print("\n2. Inizio caricamento dati in Oracle (Destinazione)...")
    try:
        conn = oracledb.connect(**DB_TGT)
        cursor = conn.cursor()

        with open(FILE_CSV, mode='r', encoding='utf-8') as f:
            reader = csv.reader(f, delimiter='|')
            colonne = next(reader)  # Leggiamo l'intestazione

            placeholders = [f":{i + 1}" for i in range(len(colonne))]
            sql = f"INSERT INTO {TABELLA_DESTINAZIONE} ({', '.join(colonne)}) VALUES ({', '.join(placeholders)})"

            batch = []
            righe_inserite = 0

            for row in reader:
                # Convertiamo le stringhe vuote del CSV in None (che Oracle interpreta come NULL)
                clean_row = [val if val != '' else None for val in row]
                batch.append(tuple(clean_row))

                # Inseriamo ogni 1000 righe
                if len(batch) >= 1000:
                    cursor.executemany(sql, batch, batcherrors=True)
                    for error in cursor.getbatcherrors():
                        print(f"Errore riga: {error.message}")
                    righe_inserite += len(batch)
                    batch = []

            # Inseriamo l'ultimo blocco residuo
            if batch:
                cursor.executemany(sql, batch, batcherrors=True)
                for error in cursor.getbatcherrors():
                    print(f"Errore riga: {error.message}")
                righe_inserite += len(batch)

        conn.commit()
        print(f"--> Caricamento completato: {righe_inserite} righe inserite con successo.")

    except Exception as e:
        print(f"Errore bloccante durante il caricamento: {e}")
    finally:
        if 'conn' in locals():
            conn.close()


if __name__ == "__main__":
    print("=== AVVIO PROCEDURA DI SINCRONIZZAZIONE ===")
    oracle_to_csv()
    csv_to_oracle()
    print("\n=== PROCEDURA TERMINATA ===")