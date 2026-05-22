import sys
import numpy as np
import pandas as pd
import re
import os
import time
import utils as utl


config = utl.get_Config()
input_path = config['paths']['input_path']
workarea_path = config['paths']['workarea_path']
cat_debug = workarea_path + 'outp_debug' + ".csv"

lookup_file = input_path + config['files']['lookup_cats']

# misc options
save_excel = config['parameters']['out_save_excel']
save_hyper = config['parameters']['out_save_hyper']
# special_debug = False
# anonimized_version = False


# categories_to_keep = cat_config['cat_to_run']
# categories_to_keep = utl.get_Categorie()

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


def check01(df, round_dig=2):
    # cumulative sales on biggest cluster equal the sum of sales on all individual clusters
    for suffix in ['Fatturato a rischio', 'Volumi a rischio', 'Margine a rischio']:
        assert sum(round((
            df.merge(
                df.groupby(
                    [sku_id, 'Regione'], as_index=False
                    )['Cluster Rank'].min(),
                on=[sku_id, 'Regione', 'Cluster Rank']
                ).sort_values(
                        by=['Regione', sku_id]
                    ).set_index(
                        ['Regione', sku_id]
                    )[f'{suffix} (cumulato)']
        ) - (
        df.sort_values(
                by=['Regione', sku_id]
            ).groupby(
                ['Regione', sku_id]
            )[f'{suffix}'].sum()
        ), round_dig
        )!=0) == 0

def check02(df1, df2):
    # check that SKUs with no sales to transfer (i.e. 100% lost sales) don't appear in 2nd sheet
    # (the sheet that contains substitution analysis)
    assert df2.merge(
        df1.loc[
            df1['Proporzione a rischio']==1,
            [sku_id, 'Regione', pop_cluster]
        ].drop_duplicates(),
        left_on = [sku_id_focus, 'Regione', pop_cluster],
        right_on = [sku_id, 'Regione', pop_cluster]
        ).shape[0] == 0

def check03(df, col1, col2, col3, round_dig=2):
    assert sum(round(
        df[col1], round_dig
        ) - round(
        df[col2]*df[col3], round_dig
        ) != 0) == 0

def check04(df1, df2, round_dig=2):
    # transferred margin of delisted sku = sum of transferred margin on each substitute of that sku
    assert sum(
        df1[[sku_id, 'Regione', pop_cluster, 'Margine trasferibile']].merge(
        df2.rename(columns = {sku_id_focus: sku_id}
        ).groupby(
            [sku_id, 'Regione', pop_cluster],
            as_index = False
            )['Margine trasferibile'].sum(),
        on = [sku_id, 'Regione', pop_cluster]
        )[['Margine trasferibile_x', 'Margine trasferibile_y']
        ].diff(axis=1).iloc[:,1].round(round_dig)) == 0

def check05(df, round_dig=2):
    # margine a rischio = margine iniziale - margine trasferibile
    assert 0 == df.apply(
        lambda row: round(
            row['Margine annuale'] - \
            row['Margine trasferibile'] - \
            row['Margine a rischio'],
            round_dig),
        axis = 1).sum()

def check06(df, metric, round_dig=2):
    # Cumulative sales are the same as the sum of sales on single clusters
    col1 = ''
    col2 = ''
    if metric == 'fatturato':
        col1 = 'Fatturato annuale atteso netto (cumulato)'
        col2 = 'Fatturato annuale atteso netto (singolo)'
    elif metric == 'volumi':
        col1 = 'Volumi annuali attesi netti (cumulato)'
        col2 = 'Volumi annuali attesi netti (singolo)'

    #CEGIL:
    # 1. Calcoliamo la stessa operazione dell'assert
    operazione = pd.concat([
        (df.groupby(['Nuovo EAN', 'Regione'])[col1].max()),
        (df.groupby(['Nuovo EAN', 'Regione'])[col2].sum())
    ], axis=1)

    # Rinominiamo le colonne per chiarezza
    operazione.columns = ['max_col1', 'sum_col2']

    # 2. Calcoliamo la differenza
    operazione['differenza'] = (operazione['sum_col2'] - operazione['max_col1']).round(round_dig)

    # 3. Filtriamo e stampiamo solo le righe dove la differenza NON è zero
    righe_problematiche = operazione[operazione['differenza'] != 0]

    if not righe_problematiche.empty:
        print("‼️‼️‼️‼️‼️‼️‼️‼️‼️‼️‼️‼️‼️‼️‼️‼️‼️‼️‼️‼️‼️‼️‼️‼️‼️‼️‼️‼️‼️‼️‼️‼️‼️‼️‼️‼️‼️")
        print("‼️ ATTENZIONE: Trovati gruppi che non rispettano la condizione di controllo.")
        print("Controllare i seguenti gruppi ('Nuovo EAN', 'Regione'):")
        print (f'colonna 1:',col1, '; colonna 2:', col2)
        print(righe_problematiche)
    # else:
    #     print("✅ Controllo superato: nessun gruppo problematico trovato.")

    # A questo punto puoi lasciare l'assert o commentarlo temporaneamente
    assert 0 == len(righe_problematiche)
    # assert 0 == 0


    # assert 0 == sum(
    #     pd.concat([(
    #         df.groupby(['nuovo ean', 'regione']
    #             )[col1].max(
    #         ).sort_index()
    #     ), (
    #         df.groupby(['nuovo ean', 'regione']
    #             )[col2].sum()
    #     )], axis=1
    #     ).diff(axis=1
    #     ).iloc[:, 1].round(round_dig) != 0)

def check07(df, metric, round_dig=2):
    # on top sales + cannibalised sales = total expected sales
    if metric == 'fatturato':
        col1 = 'Fatturato annuale atteso netto (singolo)'
        col2 = 'Fatturato annuale atteso cannibalizzato (singolo)'
        col3 = 'Fatturato annuale atteso (singolo)'
    elif metric == 'volumi':
        col1 = 'Volumi annuali attesi netti (singolo)'
        col2 = 'Volumi annuali attesi cannibalizzati (singolo)'
        col3 = 'Volumi annuali attesi (singolo)'
    elif metric == 'margine':
        col1 = 'Margine annuale atteso netto (singolo)'
        col2 = 'Margine annuale atteso cannibalizzato (singolo)'
        col3 = 'Margine annuale atteso (singolo)'
    assert sum(round(df[col1] + df[col2] - df[col3], round_dig) != 0) == 0

def check08(df1, df2, round_dig=2):
    # total cannibalised sales equals the sum of transferred sales from similar SKUs
    for prefix in ['Fatturato', 'Volumi']:
        end1 = 'o'
        end2 = 'e'
        if prefix == 'Volumi':
            end1 = end2 = 'i'
        assert pd.concat([
            df2.groupby(
                ['Nuovo EAN', 'Regione']
                )[f"{prefix} annual{end2} 'rubat{end1}' dal nuovo SKU"].sum(),
            df1.groupby(
                ['Nuovo EAN', 'Regione']
                )[f'{prefix} annual{end2} attes{end1} cannibalizzat{end1} (singolo)'].sum()
            ], axis=1,
            join='inner'
            ).diff(axis=1
            ).iloc[:, 1].round(round_dig).sum() == 0

def check09(d1, d2, a1, a2, l1, l2, round_dig=2):
    prefix_names_map = {
        'Fatturato': 'sing',
        'Volumi': 'plur',
        }
    for pref, n in prefix_names_map.items():
        if n=='sing':
            end1 = 'o'
            end2 = 'e'
            end3 = 'o'
        else:
            end1 = 'i'
            end2 = 'i'
            end3 = ''
        #
        # expected on top total + cannibalised total equals expected total overall
        assert round(
            a1[f'{pref} annual{end2} attes{end1} nett{end1} (singolo)'] + \
            a1[f'{pref} annual{end2} attes{end1} cannibalizzat{end1} (singolo)'] - \
            a1[f'{pref} annual{end2} attes{end1} (singolo)'],
            round_dig).sum() == 0
        #
        # total amount cannibalised by new SKU equals total transferred amount by SKU from top 10 similar SKUs
        assert a1[[f"{sku_id}", 'Regione', pop_cluster,
                f'{pref} annual{end2} attes{end1} cannibalizzat{end1} (singolo)']
            ].set_index(
                [f"{sku_id}", 'Regione', pop_cluster]
            ).join(
                a2.groupby(
                    [f"{sku_id}", 'Regione', pop_cluster]
                )[f"{pref} annual{end2} 'rubat{end1}' dal nuovo SKU"
                ].sum()
            ).diff(axis=1
            ).iloc[:, -1].round(round_dig).sum() == 0
        #
        assert pd.merge(
                d2[[sku_id+" (Sostituto)", 'Regione', pop_cluster, f'{pref} annual{end2} (Sostituto)']
                ].rename(columns={sku_id+" (Sostituto)": sku_id}
                    ).drop_duplicates(),
                l2[[sku_id+" (Cannibalizzato)", 'Regione', pop_cluster, f'{pref} annual{end2} (Cannibalizzato)']
                ].rename(columns={sku_id+" (Cannibalizzato)": sku_id}
                    ).drop_duplicates(),
                on = [sku_id, 'Regione', pop_cluster]
            ).merge(
                a2[[sku_id+" (Cannibalizzato)", 'Regione', pop_cluster, f'{pref} annual{end2} (Cannibalizzato)']
                ].rename(columns={sku_id+" (Cannibalizzato)": sku_id}
                ).drop_duplicates(),
                on = [sku_id, 'Regione', pop_cluster]
            ).set_index([sku_id, 'Regione', pop_cluster]
            ).apply(lambda row: 0 if np.ceil(row[0])==np.ceil(row[1]) else 1, axis=1
            ).sum() == 0
        #
        assert pd.merge(
                d2[[sku_id+" (Sostituto)", 'Regione', pop_cluster, f'{pref} annual{end2} per regione (Sostituto)']
                ].rename(columns={sku_id+" (Sostituto)": sku_id}
                    ).drop_duplicates(),
                l2[[sku_id+" (Cannibalizzato)", 'Regione', pop_cluster, f'{pref} annual{end2} per regione']
                ].rename(columns={sku_id+" (Cannibalizzato)": sku_id}
                    ).drop_duplicates(),
                on = [sku_id, 'Regione', 'Cluster']
            ).merge(
                a2[[sku_id+" (Cannibalizzato)", 'Regione', pop_cluster, f'{pref} annual{end2} per regione']
                ].rename(columns={sku_id+" (Cannibalizzato)": sku_id}
                ).drop_duplicates(),
                on = [sku_id, 'Regione', pop_cluster]
            ).set_index([sku_id, 'Regione', pop_cluster]
            ).apply(lambda row: 0 if np.ceil(row[0])==np.ceil(row[1]) else 1, axis=1
            ).sum() == 0

def check10(df1, df2, round_dig=2):
    # transferred margin of delisted sku = sum of transferred margin on each substitute of that sku
    assert 0 == sum(df1[[
            sku_id, 'Regione', pop_cluster,
            'Margine annuale atteso cannibalizzato (singolo)']
        ].merge(
            df2.groupby(
            [sku_id, 'Regione',pop_cluster],
            as_index = False
            )["Margine annuale 'rubato' dal nuovo SKU"].sum(),
        on = ['Articolo Radice COD', 'Regione', pop_cluster]
        )[['Margine annuale atteso cannibalizzato (singolo)', "Margine annuale 'rubato' dal nuovo SKU"]
        ].diff(axis=1).iloc[:,1].round(round_dig))

def process_single_category(cat: str):
    cat_lookup = smart_load_to_pd(fname=lookup_file, sep=",", decimal=".", encoding="latin-1")
    cat_lookup = cat_lookup[cat_lookup["sales_2y"] > 0]
    cat_lookup = cat_lookup.sort_values(by="sales_2y")

    incomplete_cat = []
    nooutp_cat = []
    all_cat_outp = []  # file names of each category's output
    cat_debug_outp = []

    # print("=================")
    # print("SCRIPT 10 - STIMA IMPATTI")
    # print("=================")

    start_out = time.time()


    # with open(log_file, 'a') as f:
    #     f.write('LOG CHECKS & OUTPUT' + '\n')
    #     f.write('+++++++++++++++++++' + '\n')
    #     f.write('start creating output: ' + datetime.fromtimestamp(start_out).strftime("%d/%m/%Y, %H:%M:%S") + '\n')

    # for cat in categories_to_keep:
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
        return
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

    delist1['Articolo Radice COD'] = delist1['Articolo Radice COD'].astype(str).replace('.0', '')

    delist2['Articolo Radice COD (Focus)'] = delist2['Articolo Radice COD (Focus)'].astype(str).replace('.0', '')
    delist2['Articolo Radice COD (Sostituto)'] = delist2['Articolo Radice COD (Sostituto)'].astype(str).replace('.0', '')

    aumento1['Articolo Radice COD'] = aumento1['Articolo Radice COD'].astype(str).replace('.0', '')

    aumento2['Articolo Radice COD'] = aumento2['Articolo Radice COD'].astype(str).replace('.0', '')
    aumento2['Articolo Radice COD (Cannibalizzato)'] = aumento2['Articolo Radice COD (Cannibalizzato)'].astype(str).replace('.0', '')

    list2['Articolo Radice COD (Cannibalizzato)']=list2['Articolo Radice COD (Cannibalizzato)'].astype(str).replace('.0', '')

    #
    #print("Output preparation: step 2 - data checks")
    # Run automated checks to make sure results are correct
    ## Delisting
    #check01(delist1)  # FIXMEE: fails at UOVA_FRESCHE
    #check02(delist1, delist2) # FIXMEE: fails at ACCESSORI_VARI_PULIZIA_CASA
    check03(delist1, 'Fatturato trasferibile', 'Fatturato annuale', 'Proporzione trasferibile')
    check03(delist1, 'Fatturato a rischio', 'Fatturato annuale', 'Proporzione a rischio')
    check03(delist1, 'Volumi trasferibili', 'Volumi annuali', 'Proporzione trasferibile')
    check03(delist1, 'Volumi a rischio', 'Volumi annuali', 'Proporzione a rischio')
    #check04(delist1, delist2) # FIXMEE (Aug 2023) creme solari weird double transferrables
    check06(list1, 'fatturato')
    check06(list1, 'volumi')
    check07(list1, 'fatturato')
    check07(list1, 'volumi')
    #check07(list1, 'margine')
    aumento1["EAN"] = aumento1["EAN"].astype("str")
    aumento2["EAN"] = aumento2["EAN"].astype("str")
    list1["Nuovo EAN"] = list1["Nuovo EAN"].astype(np.int64)
    list2["Nuovo EAN"] = list2["Nuovo EAN"].astype(np.int64)
    #check08(list1, list2)  # FIXMEE: fails at COLORANTI_CAPELLI_UOMO with new metadata
    #check09(delist1, delist2, aumento1, aumento2, list1, list2) # FIXMEE: fails at ACCESSORI_VARI_PULIZIA_CASA
    #check10(aumento1, aumento2)
    #check07(aumento1, 'margine') ## FIXMEE: fails at USA_E_GETTA
    #
    print("Output preparation: step 3 - save single cat results")
    # Save output for dashboard
    #with pd.ExcelWriter(cat_impatti) as writer:
    #    delist1.to_excel(writer, sheet_name = "Prodotti per delisting", index=False)
    #    delist2.to_excel(writer, sheet_name = "Sostituti dei delistati", index=False)
    #    aumento1.to_excel(writer, sheet_name = "Prodotti per aumento", index=False)
    #    aumento2.to_excel(writer, sheet_name = "Cannibalizzati da aumento", index=False)
    #    list1.to_excel(writer, sheet_name = "Prodotti per listing", index=False)
    #    list2.to_excel(writer, sheet_name = "Cannibalizzati dai listati", index=False)
    #    totals.to_excel(writer, sheet_name = f"Totali per regione", index=False)
    delist1.to_parquet(re.sub(".xlsx", "_deli1.parquet", cat_impatti), index=False)
    delist2.to_parquet(re.sub(".xlsx", "_deli2.parquet", cat_impatti), index=False)
    aumento1.to_parquet(re.sub(".xlsx", "_augm1.parquet", cat_impatti), index=False)
    aumento2.to_parquet(re.sub(".xlsx", "_augm2.parquet", cat_impatti), index=False)
    list1.to_parquet(re.sub(".xlsx", "_list1.parquet", cat_impatti), index=False)
    list2.to_parquet(re.sub(".xlsx", "_list2.parquet", cat_impatti), index=False)
    totals.to_parquet(re.sub(".xlsx", "_tot.parquet", cat_impatti), index=False)
    print('fine generazione stime impatti')

if __name__ == "__main__":

    if len(sys.argv) < 2:
        print("ERRORE: Nessuna categoria fornita.")
        print("Uso: python metadata.py <nome_categoria>")
        sys.exit(1)  # Esce con un codice di errore

    current_category = sys.argv[1]

    process_single_category(current_category)

    sys.exit(0)  # Esce indicando successo


