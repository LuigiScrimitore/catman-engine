import pandas as pd

#pd.read_parquet("../scripts/New_dataZipped/scont_l2y_015.parquet").to_csv('./scontrinato_015.csv',sep=';')
 #df = pd.read_csv("./scontrinato_050.csv",sep=';',low_memory=True,encoding="latin1")


#df=pd.read_csv("./scontrinato_050.csv", chunksize=100, sep=";")

df = pd.read_csv("./scontrinato_050.csv",sep=';',low_memory=False,encoding="latin1", chunksize=100).get_chunk()

#print(df.columns)


dimensione_blocco = 20000000
i = 1
for blocco in pd.read_csv("./scontrinato_050.csv", chunksize=dimensione_blocco, sep=";"):
    # Ora puoi lavorare con ogni 'blocco' che è un DataFrame
    # Ad esempio, stampa le prime righe di ogni blocco
    print(f"Processing a block of {len(blocco)} records.")
    blocco= blocco[blocco["CUSTOMER_ID"] != -1]
    blocco = blocco[(blocco["QUANTITA"] > 0) & (blocco["IMPORTO"] > 0)]
#    if i==1:
#        df=blocco
#    else:
#        df = pd.concat([df, blocco], ignore_index=True)
#    print(blocco.head())
    print("record del blocco:", i, "dimensione:", blocco.shape, ' TOTALE:', df.shape)
    nome_file = "SALES_2Y_CAT_050_GRP." + str(i).zfill(3) + ".csv"
    print("NOME FILE:", nome_file)
    blocco.to_csv(nome_file, sep=';')
    print("-" * 30)
    i=i+1


#print("FINE ELABORAZIONE:", df.shape)
#print("lista colonne",df.columns)


#df.to_parquet('./scontrinato_050_clean.parquet')
#df.to_csv('./scontrinato_050_clean.csv',sep=';')
print("fine")
