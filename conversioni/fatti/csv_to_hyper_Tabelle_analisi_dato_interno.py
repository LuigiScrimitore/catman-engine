import pantab as pt
from tableauhyperapi import TableName
import pandas as pd



# Dizionario per il cambio nome per WK12_CATMAN -->
rename_colonne_analisi_interno = {
"INSEGNA_COD": "Insegna_COD",
"INSEGNA_DESC": "Insegna",
"REGIONE_COD": "Regione_COD",
"REGIONE_DESC": "Regione",
"MACRO_REPARTO_COD": "Macro reparto_COD",
"MACRO_REPARTO_DESC": "Macro reparto",
"PROVINCIA": "Provincia",
"PDV_COD": "PdV_COD",
"PDV_DESC": "PdV",
"MQ_EFFETTIVI": "Mq Effettivi",
"MICRO_REPARTO_PDV_COD": "Micro Reparto_COD",
"MICRO_REPARTO_PDV_DESC": "Micro Reparto",
"CATEG_MERC_PDV_COD": "Categoria Merceologica_COD",
"CATEG_MERC_PDV_DESC": "Categoria Merceologica",
"REPARTO_COD": "Reparto_COD",
"REPARTO_DESC": "Reparto",
"SETTORE_COD": "Settore merceologico_COD",
"SETTORE_DESC": "Settore merceologico",
"PRODOTTO_MERCATO_COD": "PRODOTTO_MERCATO_COD",
"PRODOTTO_MERCATO_DESC": "PRODOTTO_MERCATO_DESC",
"SEGMENTO_COD": "Segmento merceologico_COD",
"SEGMENTO_DESC": "Segmento merceologico",
"ART_RADICE_COD": "Articolo Radice_COD",
"ART_RADICE_DESC": "Articolo Radice",
"ART_STATO_DESC": "ART_STATO_DESC",
"FORNITORE_PRINCIPALE_COD": "Fornitore Principale_COD",
#"FORNITORE_PRINCIPALE_DESC": "Fornitore Principale",
#"FORNITORE_PRINCIPALE_DESC_MOD": "FORNITORE_PRINCIPALE_DESC_MOD",
"FORNITORE_PRINCIPALE_DESC_MOD": "Fornitore Principale",
"ART_MARCHIO_COD": "Articolo Marchio_COD",
"ART_MARCHIO_DESC": "Articolo Marchio",
"PAM_FLAG": "PAM_FLAG",
#"LA_SUPERMINIMO": "LA_SUPERMINIMO",
#"LA_MINIMO": "LA_MINIMO",
#LA_MEDIO1": "LA_MEDIO1",
#"LA_MEDIO2": "LA_MEDIO2",
#"LA_MASSIMO": "LA_MASSIMO",
#"LA_IPER": "LA_IPER",
#"LA_SUPERMASSIMO": "LA_SUPERMASSIMO",
#"LA_NON_DEFINITO": "LA_NON_DEFINITO",
"LA_URBAN": "Urban",
"ACAP": "Anno Mobile",
#"SELLOUT_QTA": "SELLOUT_QTA",
#"SELLOUT_QTA_PROMO": "SELLOUT_QTA_PROMO",
"SELLOUT_IMPORTO": "Importo Sellout",
"SELLOUT_IMPORTO_PROMO": "Importo Sellout Promo",
"MRG_COSTO_NETT": "Margine Costo Netto",
"MRG_VENDUTO": "Margine Venduto",
"MRG_LUNGHISSIMO": "Margine Lunghissimo",
"MRG_COSTO_NETT_PROMO": "Margine Costo Netto Promo",
"MRG_VENDUTO_PROMO": "Margine Venduto Promo",
"MRG_LUNGHISSIMO_PROMO": "Margine Lunghissimo Promo",
"SELLOUT_IMPORTO_ULTIMO_MESE": "Importo Sellout ultimo mese",
"MESE_ID": "MESE_ID",
"EAN": "EAN",
#"LA_MULTIPLI": "LA_MULTIPLI",
"CLUSTER_NAME": "Cluster",
"CAP": "CAP",
"NUM_SKU_TRATTAZIONE": "Numeriche SKU_Trattazione",
"NUM_SKU_PDV_TRATTAZIONE": "Numeriche SKU per PDV_Trattazione",
"CONTRIBUTI_FORNITORE": "Contributi Fornitore",
"SOMMA_RCC_TOT_ORD_CONS": "Totale Ordini Considerati",
"SOMMA_RCC_NUM_CONS_DATA_CONF": "Totale Ordini Ricevuti entro data richiesta",
"ART_COD": "ART_COD",

"DOMANDA_SETT_PZ_SITO_SECCHI_CIVITAVECCHIA_RM": "Domanda sett. PZ_Sito SECCHI CIVITAVECCHIA (RM)",
"DOMANDA_SETT_PZ_SITO_SECCHI_MONASTIR_CA": "Domanda sett. PZ_Sito SECCHI MONASTIR (CA)",
"DOMANDA_SETT_PZ_SITO_FRESCHI_MONASTIR_CA": "Domanda sett. PZ_Sito FRESCHI MONASTIR (CA)",
"DOMANDA_SETT_PZ_SITO_FRESCHI_E_SURG_TARQUINIA": "Domanda sett. PZ Sito FRESCHI E. SURG. TARQUINIA",
"DOMANDA_SETT_PZ_SITO_C_DEP_SURG_SERRAVALLE_PT": "Domanda sett. PZ_Sito C.DEP. SURG. SERRAVALLE (PT)",
"DOMANDA_SETT_PZ_SITO_SECCHI_MONTOPOLI_PI": "Domanda sett. PZ_Sito SECCHI MONTOPOLI (PI)",
"DOMANDA_SETT_PZ_SITO_A_R_CIVITAVECCHIA_RM": "Domanda sett. PZ_Sito A,R CIVITAVECCHIA (RM)",
"DOMANDA_SETT_PZ_SITO_C_DEP_SURG_MACCHIAREDDU_CA": "Domanda sett. PZ Sito C.DEP. SURG. MACCHIAREDDU (CA)",
"DOMANDA_SETT_PZ_SITO_FRESCHI_SASSARI_SS": "Domanda sett. PZ_Sito FRESCHI SASSARI (SS)",
"DOMANDA_SETT_PZ_SITO_SECCHI_SASSARI_SS": "Domanda sett. PZ_Sito SECCHI  SASSARI (SS)",
"DOMANDA_SETT_PZ_SITO_C_DEP_SURG_RIVALTA_AL": "Domanda sett. PZ_Sito C.DEP. SURG. RIVALTA (AL)",
"DOMANDA_SETT_PZ_SITO_SECCHI_ANZOLA_BO": "Domanda sett. PZ_Sito SECCHI ANZOLA (BO)",
"DOMANDA_SETT_PZ_SITO_SECCHI_SAN_MINIATO_PI": "Domanda sett. PZ_Sito SECCHI SAN MINIATO  (PI)",
"DOMANDA_SETT_PZ_SITO_SALUMI_MODENA_MO": "Domanda sett. PZ_Sito SALUMI MODENA (MO)",
"DOMANDA_SETT_PZ_SITO_SECCHI_QUILIANO_SV": "Domanda sett. PZ_Sito SECCHI QUILIANO (SV)",
"DOMANDA_SETT_PZ_SITO_FRESCHI_QUILIANO_SV": "Domanda sett. PZ_Sito FRESCHI QUILIANO (SV)",
"DOMANDA_SETT_PZ_SITO_FRESCHI_MONTOPOLI_PI": "Domanda sett. PZ_Sito FRESCHI MONTOPOLI (PI)",
"DOMANDA_SETT_PZ_SITO_ORTOFRUTTA_MODENA": "Domanda sett. PZ_Sito ORTOFRUTTA MODENA",
"DOMANDA_SETT_PZ_SITO_DISMESSO": "Domanda sett. PZ_Sito DISMESSO",
"DOMANDA_SETT_PZ_SITO_EXTRA_SELVATELLE": "Domanda sett. PZ_Sito EXTRA SELVATELLE",
"DOMANDA_SETT_PZ_SITO_SECCHI_NICHELINO": "Domanda sett. PZ_Sito SECCHI NICHELINO",
"DOMANDA_SETT_PZ_SITO_SECCHI_VILLACIDRO": "Domanda sett. PZ_Sito SECCHI VILLACIDRO",
"DOMANDA_SETT_PZ_SITO_CONTO_DEPOSITO_CORTEOLONA": "Domandasett. PZ_Sito CONTO DEPOSITO CORTEOLONA",
"DOMANDA_SETT_PZ_SITO_ORTOFRUTTA_QUILIANO": "Domanda sett. PZ_Sito ORTOFRUTTA QUILIANO",
"DOMANDA_SETT_PZ_SITO_FRESCHI_VERCELLI": "Domanda sett. PZ_Sito FRESCHI VERCELLI",
"DOMANDA_SETT_PZ_SITO_VEFA_SITO_FITTIZIO": "Domanda sett. PZ_Sito VEFA SITO FITTIZIO",
"DOMANDA_SETT_PZ_SITO_PIATTAFORMA_RIVALTA_SCRIVIA_PEL_AL": "DOMANDA_SETT_PZ_SITO_PIATTAFORMA_RIVALTA_SCRIVIA_PEL_AL",
"DOMANDA_SETT_PZ_SITO_FRESCHI_CARNI_QUILIANO_SV": "DOMANDA_SETT_PZ_SITO_FRESCHI_CARNI_QUILIANO_SV",
"DOMANDA_SETT_PZ_SITO_SECCHI_CAMPIGLIA_MARITTIMA_LI": "Domanda sett. PZ_SitoSECCHI CAMPIGLIA MARITTIMA (LI)",
"DOMANDA_SETT_PZ_SITO_35": "Avg_35",
#"CATEGORIA_ESPOSITIVA_COD": "CATEGORIA_ESPOSITIVA_COD",
#"CATEGORIA_ESPOSITIVA": "CATEGORIA_ESPOSITIVA",
"OBIETTIVO_NUMERICHE_SKU": "Obiettivo Numeriche SKU",
"MRG_COSTO_NETT_STANDARD": "Margine Costo Netto Standard",
"MRG_VENDUTO_STANDARD": "Margine Venduto Standard"
}




df = pd.read_csv("./CATMAN_1003/WK12_CATMAN.csv",sep=';',low_memory=True,encoding="latin1")

print(df.columns)



# Sostituzione delle intestazioni
nuovi_nomi = rename_colonne_analisi_interno
df.rename(columns=nuovi_nomi, inplace=True)

df['EAN'] = df['EAN'].astype(str)
df['CAP'] = df['CAP'].astype(str)
df['Cluster']=df['Cluster'].astype(str)

#df['KPI 6 Indicatore - Fornitore è Top?'] = df['KPI 6 Indicatore - Fornitore è Top?'].replace({'SI': '1', 'NO': '0'})
#df['KPI 2 Indicatore - Segmento è Top?'] = df['KPI 2 Indicatore - Segmento è Top?'].astype(float)

print('nuove colonne.....................................................')

print(df.columns)

table = TableName("Extract", "Extract")
params = {"default_database_version": "1"}

pt.frame_to_hyper(df, "algoritmo_interno.hyper", table=table, process_params=params)

print('fine..........................')
