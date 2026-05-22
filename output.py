# # Merge all output together

import pickle

import numpy as np
import pandas as pd
import pantab
import re
import yaml
import os
import time
from datetime import datetime
import argparse
import utils as utl
import db_manager as dbm

config = utl.get_Config()
input_path = config['paths']['input_path']
workarea_path = config['paths']['workarea_path']
outp_path = config['paths']['output_path']
# cat_debug = workarea_path + 'outp_debug' + ".csv"

lookup_file = input_path + config['files']['lookup_cats']

# log_file = config['files'].get('logging_file')
# if log_file is None:
#     log_file = "log_Modulo3.txt"

# run_cfg = config['files']['cat_config']
# run_cfg = utl.read_Categorie()

# misc options
# save_excel = config['parameters']['out_save_excel']
save_hyper = config['parameters']['out_save_hyper']
save_csv = config['parameters']['out_save_csv']
save_db = config['parameters']['out_save_db']
special_debug = False
anonimized_version = False

# with open(run_cfg, "r") as f:
#     cat_config = yaml.safe_load(f)

# categories_to_keep = cat_config['cat_to_run']
categories_to_keep = utl.get_Categorie()
# Define column names
sku_id = 'Articolo Radice COD'
sku_desc = 'Prodotto'
sku_id_focus = 'Articolo Radice COD (Focus)'
sku_id_sub = 'Articolo Radice COD (Sostituto)'
pop_cluster = config['colnames']['pop_cluster']

# Columns to keep in output in the right order
cols2keep_delist1 = [
    'Categoria CNO',
    'Categoria IRI',
    'Settore',
    'Articolo Radice COD',
    'Prodotto',
    'Tipo-Varietà',
    'Tipo',
    'Varietà',
    'Regione',
    'Cluster',
    'Cluster Rank',
    'Fornitore',
    'Marca',
    'Priorità assortimento',
    'Proporzione a rischio',
    'Fatturato annuale',
    'Fatturato a rischio (cumulato)',
    'Volumi annuali',
    'Volumi a rischio (cumulato)',
    'Margine annuale',
    'Margine annuale pct',
    'Margine trasferibile',
    'Margine a rischio',
    'Margine a rischio (cumulato)'
]
cols2keep_delist2 = [
    'Categoria CNO',
    'Categoria IRI',
    'Settore',
    'Articolo Radice COD (Focus)',
    'Prodotto (Focus)',
    'Tipo-Varietà',
    'Tipo',
    'Varietà',
    'Regione',
    'Cluster',
    'Cluster Rank',
    'Articolo Radice COD (Sostituto)',
    'Prodotto (Sostituto)',
    'Proporzione trasferita al sostituto',
    'Fatturato annuale (Sostituto)',
    'Fatturato annuale per regione (Sostituto)',
    'Fatturato trasferibile',
    'Fatturato trasferibile (cumulato)',
    'Volumi annuali (Sostituto)',
    'Volumi trasferibili (cumulato)',
    'Margine annuale (Sostituto)',
    'Margine pct annuale (Sostituto)',
    'Margine trasferibile',
    'Margine trasferibile (cumulato)',
]
cols2keep_aumento1 = [
    'Categoria CNO',
    'Categoria IRI',
    'Settore',
    'EAN',
    'Articolo Radice COD',
    'Prodotto',
    'Tipo-Varietà',
    'Tipo',
    'Varietà',
    'Regione',
    'Cluster',
    'Cluster Rank',
    'Fornitore',
    'Marca',
    'Priorità assortimento (media per regione)',
    'Tasso di cannibalizzazione',
    'Fatturato annuale',
    'Fatturato annuale atteso (singolo)',
    'Fatturato annuale atteso netto (cumulato)',
    'Volumi annuali',
    'Volumi annuali attesi (singolo)',
    'Volumi annuali attesi netti (cumulato)',
    'Margine annuale',
    'Margine annuale atteso (singolo)',
    'Margine annuale atteso cannibalizzato (singolo)',
    'Margine annuale atteso netto (cumulato)',
    'Margine annuale pct',
    'Margine pct annuale atteso (singolo)'
]
cols2keep_aumento2 = [
    'Categoria CNO',
    'Categoria IRI',
    'Settore',
    'EAN',
    'Articolo Radice COD',
    'Prodotto',
    'Tipo-Varietà',
    'Regione',
    'Cluster',
    'Articolo Radice COD (Cannibalizzato)',
    'Prodotto cannibalizzato',
    "Proporzione 'rubata'",
    "Proporzione 'rubata' (cumulato)",
    'Fatturato annuale (Cannibalizzato)',
    'Fatturato annuale per regione',
    "Fatturato annuale 'rubato' dal nuovo SKU",
    "Fatturato annuale 'rubato' dal nuovo SKU (cumulato)",
    'Volumi annuali (Cannibalizzato)',
    "Volumi annuali 'rubati' dal nuovo SKU (cumulato)",
    'Margine annuale (Cannibalizzato)',
    'Margine pct annuale (Cannibalizzato)',
    "Margine annuale 'rubato' dal nuovo SKU",
    "Margine annuale 'rubato' dal nuovo SKU (cumulato)"
]
cols2keep_list1 = [
    'Categoria CNO',
    'Categoria IRI',
    'Settore',
    'Nuovo EAN',
    'Nuovo prodotto',
    'Tipo-Varieta',
    'Tipo',
    'Varietà',
    'Regione',
    'Cluster',
    'Fornitore',
    'Marca',
    'Priorità assortimento',
    'Tasso di cannibalizzazione',
    'Fatturato annuale atteso (singolo)',
    'Fatturato annuale atteso netto (cumulato)',
    'Volumi annuali attesi (singolo)',
    'Volumi annuali attesi netti (singolo)',
    'Volumi annuali attesi netti (cumulato)',
    'Margine annuale atteso (singolo)',
    'Margine annuale atteso cannibalizzato (singolo)',
    'Margine annuale atteso netto (cumulato)',
    'Margine pct annuale atteso (singolo)',
]
cols2keep_list2 = [
    'Categoria CNO',
    'Categoria IRI',
    'Settore',
    'Nuovo EAN',
    'Nuovo prodotto',
    'Tipo-Varieta',
    'Regione',
    'Cluster',
    'Priorità assortimento',
    'Articolo Radice COD (Cannibalizzato)',
    'Prodotto cannibalizzato',
    "Proporzione 'rubata'",
    "Proporzione 'rubata' (cumulato)",
    'Fatturato annuale (Cannibalizzato)',
    "Fatturato annuale per regione",
    "Fatturato annuale 'rubato' dal nuovo SKU",
    "Fatturato annuale 'rubato' dal nuovo SKU (cumulato)",
    'Volumi annuali (Cannibalizzato)',
    'Volumi annuali per regione',
    "Volumi annuali 'rubati' dal nuovo SKU (cumulato)",
    'Margine annuale (Cannibalizzato)',
    'Margine pct annuale (Cannibalizzato)',
    "Margine annuale 'rubato' dal nuovo SKU",
    "Margine annuale 'rubato' dal nuovo SKU (cumulato)"
]
cols2keep_totals = [
    'Categoria CNO',
    'Categoria IRI',
    'Settore',
    'Regione',
    'Fatturato totale',
    'Volumi totali',
    'Margine totale',
    'Margine pct'
]
cols2keep_map = {
    'Prodotti per delisting': cols2keep_delist1,
    'Sostituti dei delistati': cols2keep_delist2,
    'Prodotti per aumento': cols2keep_aumento1,
    'Cannibalizzati da aumento': cols2keep_aumento2,
    'Prodotti per listing': cols2keep_list1,
    'Cannibalizzati dai listati': cols2keep_list2,
    'Totali per regione': cols2keep_totals
    }

def smart_load_to_pd(fname, sep, decimal, encoding):
    _, file_ext = os.path.splitext(fname)
    if file_ext == "zip":
        return pd.read_csv(fname, compression='zip', sep=sep, decimal=decimal, encoding=encoding)
    else:
        return pd.read_csv(fname, sep=sep, decimal=decimal, encoding=encoding)

def genaraStimaImpattiAll():
    cat_lookup = smart_load_to_pd(fname=lookup_file, sep=",", decimal=".", encoding="latin-1")
    cat_lookup = cat_lookup[cat_lookup["sales_2y"] > 0]
    cat_lookup = cat_lookup.sort_values(by="sales_2y")

    incomplete_cat = []
    nooutp_cat = []
    all_cat_outp = []  # file names of each category's output

    print("=================")
    print("SCRIPT 8 - output")
    print("=================")

    start_out = time.time()

    for cat in categories_to_keep:
        print("Running output preparation for category: " + str(cat))
        cat_code = cat_lookup[cat_lookup["category"] == str(cat)]["cat_code"].values[0]
        tot_outp = workarea_path + re.sub("/", "", str(cat)) + "/" + 'totals' + '_' + str(cat_code).zfill(3) + '.csv'
        delist_outp1 = workarea_path + re.sub("/", "", str(cat)) + "/" + 'delisting' + '_' + str(cat_code).zfill(3) + '_sheet1.parquet'
        delist_outp2 = workarea_path + re.sub("/", "", str(cat)) + "/" + 'delisting' + '_' + str(cat_code).zfill(3) + '_sheet2.parquet'
        aum_outp1 = workarea_path + re.sub("/", "", str(cat)) + "/" + 'aumento' + '_' + str(cat_code).zfill(3) + '_sheet1.parquet'
        aum_outp2 = workarea_path + re.sub("/", "", str(cat)) + "/" + 'aumento' + '_' + str(cat_code).zfill(3) + '_sheet2.parquet'
        list_outp1 = workarea_path + re.sub("/", "", str(cat)) + "/" + 'listing' + '_' + str(cat_code).zfill(3) + '_sheet1.parquet'
        list_outp2 = workarea_path + re.sub("/", "", str(cat)) + "/" + 'listing' + '_' + str(cat_code).zfill(3) + '_sheet2.parquet'
        cat_impatti = workarea_path + re.sub("/", "", str(cat)) + "/" + 'stima_impatti' + '_' + str(cat_code).zfill(3) + ".xlsx"
        if (not os.path.exists(delist_outp1)) or (
            not os.path.exists(aum_outp1)) or (
            not os.path.exists(list_outp1)) or (
            not os.path.exists(delist_outp2)) or (
            not os.path.exists(aum_outp2)) or (
            not os.path.exists(list_outp2)) or (
            not os.path.exists(tot_outp)):
            incomplete_cat.append(cat)
            continue
        #
        #print("Output preparation: step 1 - import")
        # Import results of delisting, aumento and listing analysis and totals
        delist1 = pd.read_parquet(delist_outp1)
        delist2 = pd.read_parquet(delist_outp2)
        aumento1 = pd.read_parquet(aum_outp1)
        aumento2 = pd.read_parquet(aum_outp2)
        list1 = pd.read_parquet(list_outp1)
        list2 = pd.read_parquet(list_outp2)
        totals = pd.read_csv(tot_outp, sep=";", decimal= ",")

        delist1['Articolo Radice COD'] = delist1['Articolo Radice COD'].astype(int).astype(str).replace('.0', '')
        # delist2['Articolo Radice COD (Focus)'] = delist2['Articolo Radice COD (Focus)'].astype(str).replace('.0', '')
        # delist2['Articolo Radice COD (Sostituto)'] = delist2['Articolo Radice COD (Sostituto)'].astype(str).replace('.0', '')
        delist2['Articolo Radice COD (Focus)'] = delist2['Articolo Radice COD (Focus)'].astype(int).astype(str).replace('.0', '')
        delist2['Articolo Radice COD (Sostituto)'] = delist2['Articolo Radice COD (Sostituto)'].astype(int).astype(str).replace('.0', '')

        aumento1['Articolo Radice COD'] = aumento1['Articolo Radice COD'].astype(int).astype(str).replace('.0', '')
        aumento2['Articolo Radice COD'] = aumento2['Articolo Radice COD'].astype(int).astype(str).replace('.0', '')
        aumento2['Articolo Radice COD (Cannibalizzato)'] = aumento2['Articolo Radice COD (Cannibalizzato)'].astype(int).astype(str).replace('.0', '')
        list2['Articolo Radice COD (Cannibalizzato)']=list2['Articolo Radice COD (Cannibalizzato)'].astype(str).replace('.0', '')

        aumento1["EAN"] = aumento1["EAN"].astype("str")
        aumento2["EAN"] = aumento2["EAN"].astype("str")
        list1["Nuovo EAN"] = list1["Nuovo EAN"].astype(np.int64)
        list2["Nuovo EAN"] = list2["Nuovo EAN"].astype(np.int64)

        print("Output preparation: step 3 - save single cat results")

        # delist1.to_parquet(re.sub(".xlsx", "_deli1.parquet", cat_impatti), index=False)
        all_cat_outp.append(re.sub(".xlsx", "_deli1.parquet", cat_impatti))
        # delist2.to_parquet(re.sub(".xlsx", "_deli2.parquet", cat_impatti), index=False)
        all_cat_outp.append(re.sub(".xlsx", "_deli2.parquet", cat_impatti))
        # aumento1.to_parquet(re.sub(".xlsx", "_augm1.parquet", cat_impatti), index=False)
        all_cat_outp.append(re.sub(".xlsx", "_augm1.parquet", cat_impatti))
        # aumento2.to_parquet(re.sub(".xlsx", "_augm2.parquet", cat_impatti), index=False)
        all_cat_outp.append(re.sub(".xlsx", "_augm2.parquet", cat_impatti))
        # list1.to_parquet(re.sub(".xlsx", "_list1.parquet", cat_impatti), index=False)
        all_cat_outp.append(re.sub(".xlsx", "_list1.parquet", cat_impatti))
        # list2.to_parquet(re.sub(".xlsx", "_list2.parquet", cat_impatti), index=False)
        all_cat_outp.append(re.sub(".xlsx", "_list2.parquet", cat_impatti))
        # totals.to_parquet(re.sub(".xlsx", "_tot.parquet", cat_impatti), index=False)
        all_cat_outp.append(re.sub(".xlsx", "_tot.parquet", cat_impatti))

        del delist1
        del delist2
        del aumento1
        del aumento2
        del list1
        del list2
        del totals
        if not os.path.exists(cat_impatti):
            nooutp_cat.append(cat)
            continue
        all_cat_outp.append(cat_impatti)


    print("Output preparation: step 4 - save all cat results")
    # Combine and save output

    all_out = outp_path + 'CAT_stima_impatti_all'
    res = {
        'Prodotti per delisting': [],
        'Sostituti dei delistati': [],
        'Prodotti per aumento': [],
        'Cannibalizzati da aumento': [],
        'Prodotti per listing': [],
        'Cannibalizzati dai listati': [],
        'Totali per regione': []
        }
    sheet_map = {
        'Prodotti per delisting': "deli1",
        'Sostituti dei delistati': "deli2",
        'Prodotti per aumento': "augm1",
        'Cannibalizzati da aumento': "augm2",
        'Prodotti per listing': "list1",
        'Cannibalizzati dai listati': "list2",
        'Totali per regione': "tot",
        }

    if len(all_cat_outp) == 0:
        cat_codes = [cat_lookup[cat_lookup["category"] == str(cat)]["cat_code"].values[0] for cat in categories_to_keep]

        outp_all_path = workarea_path + re.sub("/","",str(cat))
        all_cat_outp = [ff for ff in os.listdir(outp_all_path) if 'stima_impatti' in ff]

    print(all_cat_outp)
    # pd.DataFrame(all_cat_outp).to_csv("./config/stime_impatti.csv", index=False, sep=";", decimal=",")

    for sheet_n in res.keys():
        print('>>> processing sheet: ', sheet_n)
        for cat_filename in all_cat_outp:
            if sheet_map.get(sheet_n) in cat_filename:
                df = pd.read_parquet(cat_filename)
                if set(cols2keep_map[sheet_n]).issubset(df.columns):
                    df = df[cols2keep_map[sheet_n]]
                    res[sheet_n].append(df)
        res[sheet_n] = pd.concat(res[sheet_n])
        #if "EAN" in res[sheet_n].columns:
        #    res[sheet_n]["EAN"] = res[sheet_n]["EAN"].astype(str)

    print ("preparazione res finita.")

    res['Cannibalizzati dai listati']['Articolo Radice COD (Cannibalizzato)'] = res['Cannibalizzati dai listati']['Articolo Radice COD (Cannibalizzato)'].astype(str).replace('.0', '')
    res['Cannibalizzati dai listati']['Nuovo prodotto'] = res['Cannibalizzati dai listati']['Nuovo prodotto'].astype(int).astype(str)
    res['Cannibalizzati da aumento']['Articolo Radice COD (Cannibalizzato)'] = res['Cannibalizzati da aumento']['Articolo Radice COD (Cannibalizzato)'].astype(str).replace('.0', '')
    res['Prodotti per listing']['Nuovo prodotto'] = res['Prodotti per listing']['Nuovo prodotto'].astype(int).astype(str)
    res['Prodotti per aumento']['Articolo Radice COD']=res['Prodotti per aumento']['Articolo Radice COD'].astype(float)
    res['Cannibalizzati da aumento']['Articolo Radice COD']=res['Cannibalizzati da aumento']['Articolo Radice COD'].astype(float)

    if save_hyper:
        pantab.frames_to_hyper(res, all_out + '.hyper')
        # estrazione in fil csv
    if save_csv:
        for nome_foglio, df in res.items():
            # 1. Costruisci il nome del file
            # Aggiungiamo .csv e uniamo il percorso della cartella
            nome_file = f"{nome_foglio}.csv"
            percorso_completo = os.path.join(outp_path , nome_file)

            # 2. Esporta in CSV
            # sep=';' è ideale per Excel in italiano
            # encoding='utf-8-sig' gestisce correttamente gli accenti
            df.to_csv(percorso_completo, index=False, sep=';', encoding='utf-8-sig')

            print(f"-> Salvato: {nome_file} (Righe: {len(df)})")

    if save_db:
        # =======================================================
        # SCRITTURA DATI FINALI DIRETTAMENTE SU ORACLE
        # =======================================================
        print("\n" + "=" * 50)
        print("▶️  Inizio salvataggio risultati finali su DB Oracle")
        print("=" * 50)

        start_db_write = time.time()
        dbm.write_all_results_to_db(res)
        print(f"Fine salvataggio su DB in {(time.time() - start_db_write):.1f} secondi.")
        print("=" * 50)


if __name__ == "__main__":
    genaraStimaImpattiAll()

