from tableauhyperapi import HyperProcess, Telemetry, Connection, TableName

# Percorso del file hyper
file_path = './Output algoritmo_gennaio.hyper'
schema_name = 'Extract'
table_name = 'Extract'
# Avvia il processo Hyper
with HyperProcess(telemetry=Telemetry.SEND_USAGE_DATA_TO_TABLEAU) as hyper:
    # Crea una connessione al file .hyper
    with Connection(endpoint=hyper.endpoint, database=file_path) as connection:
        # Ottieni i nomi delle colonne della tabella
        table_definition = connection.catalog.get_table_definition(TableName(schema_name,table_name))
        columns_name = [column.name for column in table_definition.columns]
        # Esegui una query per ottenere tutti i dati della tabella "Extract"."Extract"
        query = 'SELECT  * FROM "Extract"."Extract"'
        rows = connection.execute_list_query(query=query)

import pandas as pd
df = pd.DataFrame(rows, columns= columns_name)

df.to_csv('./Output algoritmo_gennaio.csv',sep=';')
