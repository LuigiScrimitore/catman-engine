import pantab as pt
from tableauhyperapi import TableName
import pandas as pd



# Dizionario per il cambio nome per FT_CATMAN_OUTPUT_ALGORITMO -->
rename_colonne_Output_algoritmo = {
    "EAN": "EAN",
    "CANALE": "Canale",
    "REGIONE": "Regione",
    "CLUSTER_NAME": "Cluster",
    "SETTORE": "Settore",
    "CATEGORIA": "Categoria",
    "TIPO": "Tipo",
    "VARIETA": "Varieta",
    "PRODOTTO": "Prodotto_Dettaglio",
    "PRODOTTO_DETTAGLIO": "Prodotto",
    "RUOLO": "Ruolo", "MICRO_REPARTO": "Micro Reparto",
"MICRO_REPARTO_COD": "Micro Reparto_COD", "SETTORE_MERCEOLOGICO": "Settore merceologico", "SETTORE_MERCEOLOGICO_COD": "Settore merceologico_COD",
"CATEGORIA_MERCEOLOGICA": "Categoria Merceologica", "CATEGORIA_MERCEOLOGICA_COD": "Categoria Merceologica_COD", "ARTICOLO_RADICE": "Articolo Radice",
"ARTICOLO_RADICE_COD": "Articolo Radice_COD", "ARTICOLO_MARCHIO": "Articolo Marchio", "ARTICOLO_MARCHIO_COD": "Articolo Marchio_COD",
"ANNO_MOBILE": "Anno Mobile", "FORNITORE": "Fornitore", "IMPORTO_SELLOUT": "Importo Sellout",
    "IMPORTO_SELLOUT_PROMO": "Importo Sellout Promo",
"MARCA": "Marca", "MARGINE_COSTO_NETTO": "Margine Costo Netto", "MARGINE_COSTO_NETTO_PROMO": "Margine Costo Netto Promo",
"MARGINE_VENDUTO": "Margine Venduto", "MARGINE_VENDUTO_PROMO": "Margine Venduto Promo", "SEGMENTO_MERCEOLOGICO": "Segmento merceologico",
"SEGMENTO_MERCEOLOGICO_COD": "Segmento merceologico_COD", "SELLOUT_QTA": "SELLOUT_QTA", "SELLOUT_QTA_PROMO": "SELLOUT_QTA_PROMO",
"KPI_1_INDICATORE_TREND_YOY_TIPO_MKT": "KPI 1 Indicatore - Trend YoY% Tipo Mercato", "KPI_1_INDICATORE_TREND_YOY_CAT_MKT": "KPI 1 Indicatore - Trend YoY% Categoria Mercato",
"KPI_1_TREND_SEGMENTO_MERCATO": "KPI 1 Trend del segmento nel mercato", "KPI_2_INDICATORE_SEGMENTO_TOP": "KPI 2 Indicatore - Segmento è Top?",
"KPI_2_IMPORTANZA_SEGMENTO_NEL_MERCATO": "KPI 2 Importanza del segmento nel mercato",
"KPI_3_INDICATORE_FAIRSHARE_N_SKU_CNO_VS_MKT_SETTORE": "KPI 3 Indicatore - Fairshare nr. SKU CNO vs. Mercato Settore",
"KPI_3_INDICATORE_FAIRSHARE_N_SKU_CNO_VS_MKT_TIPO": "KPI 3 Indicatore - Fairshare nr. SKU CNO vs. Mercato Tipo",
"KPI_3_PROFONDITA_MERCATO_VS_CNO": "KPI 3 Profondità mercato vs CNO",
"KPI_4_INDICATORE_PREZZO_MEDIO_SKU_CATEGORIA_MERCATO": "KPI 4 Indicatore - Prezzo medio SKU su Categoria Mercato",
"KPI_4_INDICATORE_FAIR_SHARE_FASCIA_PREZZO": "KPI 4 Indicatore - Fairshare fascia prezzo CNO vs. Mercato",
"KPI_4_FASCIA_PREZZO_SEGMENTO_MKT_VS_CNO": "KPI 4 Fascia Prezzo nel segmento nel mercato vs CNO",
"KPI_5_INDICATORE_TREND_YOY_MARCA": "KPI 5 Indicatore - Trend YoY% Marca",
"KPI_5_INDICATORE_TREND_YOY_CATEGORIA_IRI_TERRITORIO": "KPI 5 Indicatore - Trend YoY% Categoria Mercato",
"KPI_5_TREND_MARCA_SU_MERCATO": "KPI 5 Trend Marca sul mercato", "KPI_6_INDICATORE_FAIR_SHARE": "KPI 6 Indicatore - Fairshare",
"KPI_6_INDICATORE_FORNITORE_TOP": "KPI 6 Indicatore - Fornitore è Top?",
"KPI_6_QUOTA_FORNITORE_SEGMENTO_CNO_VS_MKT": "KPI 6 Quota fornitore nel segmento CNO vs mercato",
"KPI_7_INDICATORE_TREND_YOY_TIPO_IRI_TERRITORIO": "KPI 7 Indicatore - Trend YoY% Tipo Mercato",
"KPI_7_INDICATORE_TREND_YOY_SKU_TERRITORIO": "KPI 7 Indicatore - Trend YoY% SKU Mercato", "KPI_7_TREND_SKU_MERCATO": "KPI 7 Trend SKU nel mercato",
"KPI_8_INDICATORE_QUOTA_SKU_SU_CATEGORIA": "KPI 8 Indicatore - Quota SKU su Categoria",
"KPI_8_DIMENSIONE_SKU_MERCATO": "KPI 8 Dimensione SKU nel mercato", "KPI_9_INDICATORE_TREND_YOY_TIPO_CNO": "KPI 9 Indicatore - Trend YoY% Tipo in CNO",
"KPI_9_INDICATORE_TREND_YOY_SKU_CNO": "KPI 9 Indicatore - Trend YoY% SKU in CNO", "KPI_9_TREND_SKU_CNO": "KPI 9 Trend SKU in CNO",
"KPI_10_INDICATORE_MARGINE_SEGMENTO_PERC": "KPI 10 Indicatore - Margine Segmento %",
"KPI_10_INDICATORE_MARGINE_SKU_PERC": "KPI 10 Indicatore - Margine SKU %", "KPI_10_MARGINALITA": "KPI 10 Marginalità SKU in CNO",
"PRIORITA_ASSORTIMENTO_PONDERATO_NON_ROUNDED": "PRIORITA' ASSORTIMENTO PONDERATO NON ROUNDED", "PRIORITA_ASSORTIMENTO_COMPLESSIVO": "PRIORITA' ASSORTIMENTO COMPLESSIVO",
"ART_STATO_DESC": "ART_STATO_DESC", "MARGINE_COSTO_NETTO_STANDARD": "Margine Costo Netto Standard", "MARGINE_VENDUTO_STANDARD": "Margine Venduto Standard",
"FORMATO": "Formato", "VEN_VAL_ALL_AC_CNO": "CNO_AC_Vendite in Valore", "VEN_VAL_ALL_AC_MKT": "MKT_AC_Vendite in Valore",
"VEN_VOL_ALL_AC_CNO": "CNO_AC_Vendite in Volume", "VEN_VOL_ALL_AC_MKT": "MKT_AC_Vendite in Volume", "VEN_UNI_ALL_AC_CNO": "CNO_AC_Vendite in Unita",
"VEN_UNI_ALL_AC_MKT": "MKT_AC_Vendite in Unita", "DISTRI_POND_AC_CNO": "CNO_AC_Distribuzione Ponderata",
"DISTRI_POND_AC_MKT": "MKT_AC_Distribuzione Ponderata", "VEN_VAL_RID_AC_CNO": "CNO_AC_Vendite in Valore  Ogni Riduzione Prezzo",
"VEN_VAL_RID_AC_MKT": "MKT_AC_Vendite in Valore  Ogni Riduzione Prezzo", "VEN_VAL_NOR_AC_CNO": "CNO_AC_Vendite in Valore  Senza Riduzione Prezzo",
"VEN_VAL_NOR_AC_MKT": "MKT_AC_Vendite in Valore  Senza Riduzione Prezzo", "VEN_VAL_ALL_AP_CNO": "CNO_AP_Vendite in Valore",
"VEN_VAL_ALL_AP_MKT": "MKT_AP_Vendite in Valore", "VEN_VOL_ALL_AP_CNO": "CNO_AP_Vendite in Volume", "VEN_VOL_ALL_AP_MKT": "MKT_AP_Vendite in Volume",
"VEN_UNI_ALL_AP_CNO": "CNO_AP_Vendite in Unita", "VEN_UNI_ALL_AP_MKT": "MKT_AP_Vendite in Unita",
"DISTRI_POND_AP_CNO": "CNO_AP_Distribuzione Ponderata", "DISTRI_POND_AP_MKT": "MKT_AP_Distribuzione Ponderata",
"VEN_VAL_RID_AP_CNO": "CNO_AP_Vendite in Valore  Ogni Riduzione Prezzo", "VEN_VAL_RID_AP_MKT": "MKT_AP_Vendite in Valore  Ogni Riduzione Prezzo",
"VEN_VAL_NOR_AP_CNO": "CNO_AP_Vendite in Valore  Senza Riduzione Prezzo", "VEN_VAL_NOR_AP_MKT": "MKT_AP_Vendite in Valore  Senza Riduzione Prezzo"
}




#df = pd.read_csv("./WK0_MERCATO_CATMAN.csv",sep=';',low_memory=False,encoding="latin1")
#df = pd.read_csv("./FT_CATMAN_OUTPUT_ALGORITMO.csv",sep=';',low_memory=False,encoding="latin1")
df = pd.read_csv("./CATMAN_1003/FT_CATMAN_OUTPUT_ALGORITMO.csv",sep=';',low_memory=False,encoding="latin1")

#print(df.columns)


nuovi_nomi = rename_colonne_Output_algoritmo

# Sostituzione delle intestazioni
df.rename(columns=nuovi_nomi, inplace=True)

df['KPI 2 Indicatore - Segmento è Top?'] = df['KPI 2 Indicatore - Segmento è Top?'].replace({'SI': '1', 'NO': '0'})
df['KPI 6 Indicatore - Fornitore è Top?'] = df['KPI 6 Indicatore - Fornitore è Top?'].replace({'SI': '1', 'NO': '0'})

df['KPI 2 Indicatore - Segmento è Top?'] = df['KPI 2 Indicatore - Segmento è Top?'].astype(float)
df['KPI 6 Indicatore - Fornitore è Top?'] = df['KPI 6 Indicatore - Fornitore è Top?'].astype(float)

df['KPI 6 Indicatore - Fairshare'] = df['KPI 6 Indicatore - Fairshare'].astype(float)
df['Importo Sellout Promo'] = df['Importo Sellout Promo'].astype(float)
df['Margine Venduto Standard'] = df['Margine Venduto Standard'].astype(float)

print('nuove colonne.....................................................')

print(df.columns)

table = TableName("Extract", "Extract")
pt.frame_to_hyper(df, "./CATMAN_1003/output_algoritmo.hyper", table=table)

#df.to_csv('./Output algoritmo_gennaio.csv',sep=';')
