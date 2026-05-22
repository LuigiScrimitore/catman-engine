import pantab as pt
from tableauhyperapi import TableName
import pandas as pd



# Dizionario per il cambio nome per WK0_MERCATO_CATMAN -->
rename_colonne_analisi_mercato = {
    "EAN": "EAN",
    "PRODOTTO": "Prodotto",
    "PRODOTTO_DETTAGLIO": "Prodotto_Dettaglio",
    "PRODUTTORE": "Produttore",
    "MARCA": "Marca",
    "CATEGORIA": "Categoria",
    "SETTORE": "Settore",
    "TIPO": "Tipo",
    "VARIETA": "Varieta",
    "REGIONE": "Regione",
    "FORMATO": "Formato",
    "VEN_VAL_ALL_AC_CNO": "CNO_AC_Vendite in Valore",
    "VEN_VAL_ALL_AC_MKT": "MKT_AC_Vendite in Valore",
    "VEN_VOL_ALL_AC_CNO": "CNO_AC_Vendite in Volume",
    "VEN_VOL_ALL_AC_MKT": "MKT_AC_Vendite in Volume",
    "VEN_UNI_ALL_AC_CNO": "CNO_AC_Vendite in Unita",
    "VEN_UNI_ALL_AC_MKT": "MKT_AC_Vendite in Unita",
    "DISTRI_POND_AC_CNO": "CNO_AC_Distribuzione Ponderata",
    "DISTRI_POND_AC_MKT": "MKT_AC_Distribuzione Ponderata",
    "VEN_VAL_RID_AC_CNO": "CNO_AC_Vendite in Valore  Ogni Riduzione Prezzo",
    "VEN_VAL_RID_AC_MKT": "MKT_AC_Vendite in Valore  Ogni Riduzione Prezzo",
    "VEN_VAL_NOR_AC_CNO": "CNO_AC_Vendite in Valore  Senza Riduzione Prezzo",
    "VEN_VAL_NOR_AC_MKT": "MKT_AC_Vendite in Valore  Senza Riduzione Prezzo",
    "VEN_VAL_ALL_AP_CNO": "CNO_AP_Vendite in Valore",
    "VEN_VAL_ALL_AP_MKT": "MKT_AP_Vendite in Valore",
    "VEN_VOL_ALL_AP_CNO": "CNO_AP_Vendite in Volume",
    "VEN_VOL_ALL_AP_MKT": "MKT_AP_Vendite in Volume",
    "VEN_UNI_ALL_AP_CNO": "CNO_AP_Vendite in Unita",
    "VEN_UNI_ALL_AP_MKT": "MKT_AP_Vendite in Unita",
    "DISTRI_POND_AP_CNO": "CNO_AP_Distribuzione Ponderata",
    "DISTRI_POND_AP_MKT": "MKT_AP_Distribuzione Ponderata",
    "VEN_VAL_RID_AP_CNO": "CNO_AP_Vendite in Valore  Ogni Riduzione Prezzo",
    "VEN_VAL_RID_AP_MKT": "MKT_AP_Vendite in Valore  Ogni Riduzione Prezzo",
    "VEN_VAL_NOR_AP_CNO": "CNO_AP_Vendite in Valore  Senza Riduzione Prezzo",
    "VEN_VAL_NOR_AP_MKT": "MKT_AP_Vendite in Valore  Senza Riduzione Prezzo",
    "VEN_UNI_RID_AC_CNO": "CNO_AC_Vendite in Unita  Ogni Riduzione Prezzo",
    "VEN_UNI_NOR_AC_CNO": "CNO_AC_Vendite in Unita  Senza Riduzione Prezzo",
    "VEN_VOL_RID_AC_CNO": "CNO_AC_Vendite in Volume  Ogni Riduzione Prezzo",
    "VEN_VOL_NOR_AC_CNO": "CNO_AC_Vendite in Volume  Senza Riduzione Prezzo",
    "VEN_UNI_RID_AP_CNO": "CNO_AP_Vendite in Unita  Ogni Riduzione Prezzo",
    "VEN_UNI_NOR_AP_CNO": "CNO_AP_Vendite in Unita  Senza Riduzione Prezzo",
    "VEN_VOL_RID_AP_CNO": "CNO_AP_Vendite in Volume  Ogni Riduzione Prezzo",
    "VEN_VOL_NOR_AP_CNO": "CNO_AP_Vendite in Volume  Senza Riduzione Prezzo",
    "VEN_UNI_RID_AC_MKT": "MKT_AC_Vendite in Unita  Ogni Riduzione Prezzo",
    "VEN_UNI_NOR_AC_MKT": "MKT_AC_Vendite in Unita  Senza Riduzione Prezzo",
    "VEN_VOL_RID_AC_MKT": "MKT_AC_Vendite in Volume  Ogni Riduzione Prezzo",
    "VEN_VOL_NOR_AC_MKT": "MKT_AC_Vendite in Volume  Senza Riduzione Prezzo",
    "VEN_UNI_RID_AP_MKT": "MKT_AP_Vendite in Unita  Ogni Riduzione Prezzo",
    "VEN_UNI_NOR_AP_MKT": "MKT_AP_Vendite in Unita  Senza Riduzione Prezzo",
    "VEN_VOL_RID_AP_MKT": "MKT_AP_Vendite in Volume  Ogni Riduzione Prezzo",
    "VEN_VOL_NOR_AP_MKT": "MKT_AP_Vendite in Volume  Senza Riduzione Prezzo",
    "PRESENZA_CNO": "Presenza in CNO",
    "PRESENZA_MKT": "Presenza su MKT"
}


df = pd.read_csv("./DB_DATA/WK0_MERCATO_CATMAN_QUADR.csv",sep=';',low_memory=False,encoding="latin1")

print(df.columns)


nuovi_nomi = rename_colonne_analisi_mercato

# Sostituzione delle intestazioni
df.rename(columns=nuovi_nomi, inplace=True)


# Sostituzione dei valori della colonna con initcap
df['Prodotto'] = df['Prodotto'].str.capitalize()
df['Prodotto_Dettaglio'] = df['Prodotto_Dettaglio'].str.capitalize()
#df['Produttore'] = df['Produttore'].str.capitalize()
#df['Marca'] = df['Marca'].str.capitalize()
#df['Categoria'] = df['Categoria'].str.capitalize()
#df['Settore'] = df['Settore'].str.capitalize()
#df['Tipo'] = df['Tipo'].str.capitalize()
#df['Varieta'] = df['Varieta'].str.capitalize()


#df['KPI 2 Indicatore - Segmento è Top?'] = df['KPI 2 Indicatore - Segmento è Top?'].replace({'SI': '1', 'NO': '0'})
#df['KPI 6 Indicatore - Fornitore è Top?'] = df['KPI 6 Indicatore - Fornitore è Top?'].replace({'SI': '1', 'NO': '0'})

#df['KPI 2 Indicatore - Segmento è Top?'] = df['KPI 2 Indicatore - Segmento è Top?'].astype(float)
#df['KPI 6 Indicatore - Fornitore è Top?'] = df['KPI 6 Indicatore - Fornitore è Top?'].astype(float)

#df['KPI 6 Indicatore - Fairshare'] = df['KPI 6 Indicatore - Fairshare'].astype(float)
#df['Importo Sellout Promo'] = df['Importo Sellout Promo'].astype(float)
#df['Margine Venduto Standard'] = df['Margine Venduto Standard'].astype(float)

print('nuove colonne.....................................................')

print(df.columns)

table = TableName("Extract", "Extract")
params = {"default_database_version": "1"}

pt.frame_to_hyper(df, "./CATMAN/Analisi mercato.hyper", table=table, process_params=params)


