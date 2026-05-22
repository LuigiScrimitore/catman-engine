import pantab as pt
from tableauhyperapi import TableName
import pandas as pd



# Dizionario per il cambio nome per WRK_CATMAN_NEG_20 -->
rename_colonne_Output_algoritmo = {
"SETTORE": "Settore",
"FORNITORE_PRINCIPALE_DESC": "Fornitore Principale",
"PRODUTTORE": "Produttore",
"SELLOUT_IMPORTO": "Importo Sellout",
"SELLOUT_IMPORTO_PROMO": "Importo Sellout Promo",
"SELLOUT_QTA": "Quantità Sellout",
"SELLOUT_QTA_PROMO": "Quantità Sellout Promo",
"MRG_COSTO_NETT": "Margine Costo Netto",
"MRG_VENDUTO": "Margine Venduto",
"MRG_LUNGHISSIMO_PROMO": "Margine Lunghissimo Promo",
"MRG_VENDUTO_PROMO": "Margine Venduto Promo",
"MRG_COSTO_NETT_PROMO": "Margine Costo Netto Promo",
"MRG_COSTO_NETT_STANDARD": "Margine Costo Netto Standard",
"MRG_VENDUTO_STANDARD": "Margine Venduto Standard",
"SELLOUT_LIVELLO_FEDELTA": "Fedeltà per fornitore in CNO",
"CIFRE_FISSE": "Cifre Fisse",
"ACQUISTATO_2022": "Acquistato fornitore 2022",
"MRG_VENDUTO_SUM_FORN": "Sum_Margine Venduto_FORN",
"MRG_COSTO_NETT_SUM_FORN": "Sum_Margine Costo Netto_FORN",
"ACQUISTATO_2022_FORN_PER_CAT": "Acquistato fornitore 2022 per fornitore per cat",
"MRG_VENDUTO_SUM_CAT": "Sum_Margine Venduto_CAT",
"MRG_COSTO_NETT_SUM_CAT": "Sum_Margine Costo Netto_CAT",
"CIFRE_FISSE_CAT": "Cifre Fisse per cat",
"ACQUISTATO_2022_CAT": "Acquistato fornitore 2022 per cat",
"LIVELLO_FEDELTA_MEDIA_CAT": "Fedeltà media di categoria in CNO",
"MARGINE_FORN_PERC": "Margine per fornitore in CNO (%)",
"MARGINE_MEDIO_CAT_PERC": "Margine medio di categoria in CNO (%)",
"CIFRE_FISSE_ACQ_FORN": "Cifre fisse su acquistato per fornitore",
"CIFRE_FISSE_MEDIA_ACQ_CAT": "Media cifre fisse su acquistato per categoria",
"KPI_3A": "KPI 3A",
"KPI_4A": "KPI 4A",
"KPI_5A": "KPI 5A",
"SELLOUT_IMPORTO_CAT": "CAT_Importo Sellout",
"SELLOUT_IMPORTO_PROMO_CAT": "CAT_Importo Sellout Promo",
"SELLOUT_QTA_CAT": "CAT_Quantità Sellout",
"SELLOUT_QTA_PROMO_CAT": "CAT_Quantità Sellout Promo",
"MRG_COSTO_NETT_CAT": "CAT_Margine Costo Netto",
"MRG_VENDUTO_CAT": "CAT_Margine Venduto",
"MRG_LUNGHISSIMO_PROMO_CAT": "CAT_Margine Lunghissimo Promo",
"MRG_VENDUTO_PROMO_CAT": "CAT_Margine Venduto Promo",
"MRG_COSTO_NETT_PROMO_CAT": "CAT_Margine Costo Netto Promo",
"MRG_COSTO_NETT_STANDARD_CAT": "CAT_Margine Costo Netto Standard",
"MRG_VENDUTO_STANDARD_CAT": "CAT_Margine Venduto Standard",
"SELLOUT_IMPORTO_SUM": "Sum_Sum_Importo Sellout",
"VEN_VAL_ALL_AC_CNO_SUM": "Sum_Sum_CNO_AC_Vendite in Valore",
"VEN_VAL_ALL_AC_MKT_SUM": "Sum_Sum_MKT_AC_Vendite in Valore",
"VEN_VAL_ALL_AC_CNO": "CNO_AC_Vendite in Valore",
"VEN_VAL_ALL_AC_MKT": "MKT_AC_Vendite in Valore",
"VEN_VOL_ALL_AC_CNO": "CNO_AC_Vendite in Volume",
"VEN_VOL_ALL_AC_MKT": "MKT_AC_Vendite in Volume",
"VEN_UNI_ALL_AC_CNO": "CNO_AC_Vendite in Unita",
"VEN_UNI_ALL_AC_MKT": "MKT_AC_Vendite in Unita",
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
"VEN_VAL_ALL_AC_CNO_SUM_CAT": "CAT_CNO_AC_Vendite in Valore",
"VEN_VAL_ALL_AP_CNO_SUM_CAT": "CAT_CNO_AP_Vendite in Valore",
"VEN_VAL_ALL_AC_MKT_SUM_CAT": "CAT_MKT_AC_Vendite in Valore",
"VEN_VAL_ALL_AP_MKT_SUM_CAT": "CAT_MKT_AP_Vendite in Valore",
"TOT_FATTURATO_FORNITORE": "Totale fatturato fornitore (CNO Vendite a Valore)",
"TOT_FATTURATO_CATEGORIA": "Totale fatturato categoria (CNO Vendite a Valore)",
"QUOTA_FORNITORE_CNO": "Quota Fornitore in CNO (%)",
"MEDIA_QUOTA_FORNITORE_CNO": "Media_Quota Fornitore in CNO",
"KPI_1A": "KPI 1A",
"VEN_VAL_ALL_AC_CNO_SUM_FORN": "Right_Sum_CNO_AC_Vendite in Valore_FORN",
"VEN_VAL_ALL_AP_CNO_SUM_FORN": "Right_Sum_CNO_AP_Vendite in Valore_FORN",
"VEN_VAL_ALL_AC_CNO_SUM_CAT_3": "Right_Sum_CNO_AC_Vendite in Valore_CAT2",
"VEN_VAL_ALL_AC_CNO_SUM_CAT_2": "Right_Sum_CNO_AC_Vendite in Valore_CAT",
"VEN_VAL_ALL_AP_CNO_SUM_CAT_2": "Right_Sum_CNO_AP_Vendite in Valore_CAT",
"CRESCITA_CNO_AC_VS_AP_FORN": "Crescita CNO AC vs AP per fornitore",
"CRESCITA_CNO_AC_VS_AP_FORN_PERC": "Crescita CNO AC vs AP per fornitore %",
"CRESCITA_CNO_AC_VS_AP_CAT": "Crescita CNO AC vs AP per categoria",
"CRESCITA_CNO_AC_VS_AP_CAT_PERC": "Crescita CNO AC vs AP per categoria %",
"CONTR_CRESCITA_FORN_CNO_RICALC": "Contributo Crescita fornitore in CNO (%)",
"MEDIA_CONTR_CRESCITA_FORNITORE_CNO": "Media_Contributo Crescita fornitore in CNO",
"KPI_2A": "KPI 2A",
"TOT_FATTURATO_PER_FORNITORE": "Totale fatturato per fonitore in CNO (CNO Vendite a Valore) ",
"VEN_VAL_ALL_MKT_TOT_FORN": "Totale fatturato fornitore nel MKT (MKT Vendite a Valore)",
"QUOTA_FATTUR_FORN_MKT": "Totale quota fornitore in CNO su MKT (%)",
"VEN_VAL_ALL_AC_MKT_SUM_CAT_2": "Sum_MKT_AC_Vendite in Valore_CAT",
"QUOTA_VEND_FORN_MKT_CAT": "Quota Vendite fornitore CNO su foritore MKT CAT",
"KPI_3B": "KPI 3B",
"VEN_VAL_ALL_AC_MKT_SUM_FORN": "Sum_MKT_AC_Vendite in Valore_FORN",
"VEN_VAL_ALL_AP_MKT_SUM_FORN": "Sum_MKT_AP_Vendite in Valore_FORN",
"VEN_VAL_ALL_AP_MKT_SUM_CAT_2": "Sum_MKT_AP_Vendite in Valore_CAT",
"VEN_VAL_ALL_AC_MKT_SUM_CAT_3": "Right_Sum_MKT_AC_Vendite in Valore_CAT",
"CRESCITA_FORN_CNO": "Crescita del fornitore in CNO",
"CRESCITA_FORN_PERC": "Crescita del fornitore in CNO %",
"CRESCITA_MKT_AC_VS_AP_FORN": "Crescita del fornitore nel MKT",
"CRESCITA_MKT_AC_VS_AP_FORN_PERC": "Crescita del fornitore nel MKT %",
"CONTR_CRESCITA_FORN_MKT_RICALC": "Contributo fornitore in CNO su crescita fornitore nel MKT",
"CONTR_CNO_MKT_CAT": "Contributo Categoria CNO su Mercato",
"KPI_4B": "KPI 4B",
"IMP_STRATEG_CNO_SCORE": "A_Score Importanza Strategica per CNO",
"POTERE_NEG": "B_Potere negoziale CNO vs fornitore",
"RN":"RN"
}




#df = pd.read_csv("./WK0_MERCATO_CATMAN.csv",sep=';',low_memory=False,encoding="latin1")
#df = pd.read_csv("./FT_CATMAN_OUTPUT_ALGORITMO.csv",sep=';',low_memory=False,encoding="latin1")
df = pd.read_csv("./DB_DATA/WRK_CATMAN_NEG_20.csv",sep=';',low_memory=False,encoding="latin1")

#print(df.columns)


nuovi_nomi = rename_colonne_Output_algoritmo

# Sostituzione delle intestazioni
df.rename(columns=nuovi_nomi, inplace=True)

#df['KPI 2 Indicatore - Segmento è Top?'] = df['KPI 2 Indicatore - Segmento è Top?'].replace({'SI': '1', 'NO': '0'})
#df['KPI 6 Indicatore - Fornitore è Top?'] = df['KPI 6 Indicatore - Fornitore è Top?'].replace({'SI': '1', 'NO': '0'})

#df['KPI 2 Indicatore - Segmento è Top?'] = df['KPI 2 Indicatore - Segmento è Top?'].astype(float)#
#df['KPI 6 Indicatore - Fornitore è Top?'] = df['KPI 6 Indicatore - Fornitore è Top?'].astype(float)

#df['KPI 6 Indicatore - Fairshare'] = df['KPI 6 Indicatore - Fairshare'].astype(float)
#df['Importo Sellout Promo'] = df['Importo Sellout Promo'].astype(float)
#df['Margine Venduto Standard'] = df['Margine Venduto Standard'].astype(float)

print('nuove colonne.....................................................')

print(df.columns)

table = TableName("Extract", "Extract")
pt.frame_to_hyper(df, "./CATMAN/input_tableau.hyper", table=table)

df.to_csv('./CATMAN/input_tableau.csv',sep=';')
