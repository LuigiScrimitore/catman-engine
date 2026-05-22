import pantab as pt
from tableauhyperapi import TableName
import pandas as pd



# Dizionario per il cambio nome per WRK_CATMAN_NEG_17_ANALISI_INTERNO -->
rename_colonne_analisi_interno = {
"INSEGNA_COD": "Insegna_COD",
"INSEGNA_DESC": "Insegna",
"REGIONE_COD": "Regione_COD",
"REGIONE_DESC": "Regione",
"MACRO_REPARTO_COD": "Macro reparto_COD",
"MACRO_REPARTO_DESC": "Macro reparto",
"MICRO_REPARTO_PDV_COD": "Micro Reparto_COD",
"MICRO_REPARTO_PDV_DESC": "Micro Reparto",
"CATEG_MERC_PDV_COD": "Categoria Merceologica_COD",
"CATEG_MERC_PDV_DESC": "Categoria Merceologica",
"REPARTO_COD": "Reparto_COD",
"REPARTO_DESC": "Reparto",
"SETTORE_MERCEOLOGICO_COD": "Settore merceologico_COD",
"SETTORE_MERCEOLOGICO_DESC": "Settore merceologico",
"PRODOTTO_MERCATO_COD": "PRODOTTO_MERCATO_COD",
"PRODOTTO_MERCATO_DESC": "PRODOTTO_MERCATO_DESC",
"SEGMENTO_MERCEOLOGICO_COD": "Segmento merceologico_COD",
"SEGMENTO_MERCEOLOGICO_DESC": "Segmento merceologico",
"ART_RADICE_COD": "Articolo Radice_COD",
"ART_RADICE_DESC": "Articolo Radice",
"ART_STATO_DESC": "ART_STATO_DESC",
"FORNITORE_PRINCIPALE_COD": "Fornitore Principale_COD",
"RIGHT_FORNITORE_PRINCIPALE_COD": "Right_Fornitore Principale_COD",
"FORNITORE_PRINCIPALE_DESC": "Fornitore Principale",
"ART_MARCHIO_COD": "Articolo Marchio_COD",
"ART_MARCHIO_DESC": "Articolo Marchio",
"PAM_FLAG": "PAM_FLAG",
"SELLOUT_QTA": "Quantità Sellout",
"SELLOUT_QTA_PROMO": "Quantità Sellout Promo",
"SELLOUT_IMPORTO": "Importo Sellout",
"SELLOUT_IMPORTO_PROMO": "Importo Sellout Promo",
"MRG_COSTO_NETT": "Margine Costo Netto",
"MRG_VENDUTO": "Margine Venduto",
"MRG_LUNGHISSIMO": "Margine Lunghissimo",
"MRG_COSTO_NETT_PROMO": "Margine Costo Netto Promo",
"MRG_VENDUTO_PROMO": "Margine Venduto Promo",
"MRG_LUNGHISSIMO_PROMO": "Margine Lunghissimo Promo",
"EAN": "EAN",
"CLUSTER_NAME": "Cluster",
"MRG_COSTO_NETT_STANDARD": "Margine Costo Netto Standard",
"MRG_VENDUTO_STANDARD": "Margine Venduto Standard",
"LIVELLO_FEDELTA_CAT": "Livello Fedeltà per categoria",
"SELLOUT_IMPORTO_CAT": "Importo Sellout per categoria",
"SELLOUT_IMPORTO_PROMO_CAT" : "Importo Sellout Promo per categoria",
"ACQUISTATO_2022": "Acquistato fornitore 2022",
"SELLOUT_LIVELLO_FEDELTA": "Livello Fedeltà_Sellout",
"PESO_FATTUR_CAT_SU_FORN": "Peso Categoria su fatturato fornitore",
"CIFRE_FISSE": "Cifre Fisse"
}




df = pd.read_csv("./DB_DATA/WRK_CATMAN_NEG_17_ANALISI_INTERNO.csv",sep=';',low_memory=True,encoding="latin1")

print(df.columns)



# Sostituzione delle intestazioni
nuovi_nomi = rename_colonne_analisi_interno
df.rename(columns=nuovi_nomi, inplace=True)

#df['EAN'] = df['EAN'].astype(str)
#df['CAP'] = df['CAP'].astype(str)
#df['Cluster']=df['Cluster'].astype(str)

#df['KPI 6 Indicatore - Fornitore è Top?'] = df['KPI 6 Indicatore - Fornitore è Top?'].replace({'SI': '1', 'NO': '0'})
#df['KPI 2 Indicatore - Segmento è Top?'] = df['KPI 2 Indicatore - Segmento è Top?'].astype(float)

print('nuove colonne.....................................................')

print(df.columns)

table = TableName("Extract", "Extract")
params = {"default_database_version": "1"}

pt.frame_to_hyper(df, "./CATMAN/Analisi interno.hyper", table=table, process_params=params)

print('fine..........................')
