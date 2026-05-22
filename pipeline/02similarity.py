import gc
import os
import re
import sys
import pandas as pd
import numpy as np
import psutil
import yaml
import time
from itertools import combinations
import utils as utl

# config_file = "./config/configurazioni.yaml"
# with open(config_file, "r") as f:
#     config = yaml.safe_load(f)
config = utl.get_Config()

# files to process
input_path= config['paths']['input_path']
sales_path = config['paths']['sales_path']
workarea_path= config['paths']['workarea_path']
# data_path = config['paths']['aux_path']
# sales_path = config['paths']['data_path']
# outp_path = config['paths']['workarea_path']
anag_file = input_path + config['files']['pdv']
clus_file = input_path + config['files']['clusters']
meta_file = input_path + config['files']['metadata']
lookup_file = input_path + config['files']['lookup_cats']

# Define column names
lista_colonne = utl.get_Config_Colonne()
group_key = lista_colonne['group_key']
category = lista_colonne['category']
category_meta = lista_colonne['category_meta']
category_iri = lista_colonne['category_iri']
sku_score = lista_colonne['sku_score']
segment = lista_colonne['segment']
sku_id = lista_colonne['sku_id']
sku_desc = lista_colonne['sku_desc']
cust_id = lista_colonne['cust_id']
pdv_id = lista_colonne['pdv_id']
tx_id = lista_colonne['tx_id']
tx_date = lista_colonne['tx_date']
sku_status = lista_colonne['sku_status']
amount = lista_colonne['amount']
qty = lista_colonne['qty']
fidelity = lista_colonne['fidelity']
promo = lista_colonne['promo']
sku_group = lista_colonne['sku_group']
pop_cluster = lista_colonne['pop_cluster']

sku_id_focus = lista_colonne['sku_id_focus']
sku_id_sub = lista_colonne['sku_id_sub']
sku_desc_focus = lista_colonne['sku_desc_focus']
sku_desc_sub = lista_colonne['sku_desc_sub']
sku_status_focus = lista_colonne['sku_status_focus']
sku_status_sub = lista_colonne['sku_status_sub']
sku_sold_focus = lista_colonne['sku_sold_focus']
sku_sold_sub = lista_colonne['sku_sold_sub']
sku_cust_focus = lista_colonne['sku_cust_focus']
sku_cust_sub = lista_colonne['sku_cust_sub']
sku_catcno_focus = lista_colonne['sku_catcno_focus']
sku_catcno_sub = lista_colonne['sku_catcno_sub']
sku_catiri_focus = lista_colonne['sku_catiri_focus']
sku_catiri_sub = lista_colonne['sku_catiri_sub']
sku_seciri_focus = lista_colonne['sku_seciri_focus']
sku_seciri_sub = lista_colonne['sku_seciri_sub']
sku_gkey_focus = lista_colonne['sku_gkey_focus']
sku_gkey_sub = lista_colonne['sku_gkey_sub']
sku_subscore = lista_colonne['sku_subscore']

sku_filt_file = config['files']['sku_filter'] #sku_pdv_meta.csv

empty_cat = []
nosales_cat = []
noassort_cat = []
promo_cat = []
review_cat = []
nosales_grp = []


output_cols = [
   sku_id_focus, sku_desc_focus, sku_status_focus,
   sku_sold_focus, sku_cust_focus, sku_catcno_focus,
   sku_catiri_focus, sku_seciri_focus, sku_gkey_focus,
   sku_id_sub, sku_desc_sub, sku_status_sub,
   sku_sold_sub, sku_cust_sub, sku_catcno_sub,
   sku_catiri_sub, sku_seciri_sub, sku_gkey_sub,
   sku_subscore
#   , "sku_both_customer", "sku_left_no_right_customer", "sku_right_no_left_customer", "sku_neither_customer"
#   , "sku_both_transaction", "sku_left_no_right_transaction", "sku_right_no_left_transaction", "sku_neither_transaction"
]

def get_memory_usage(round_dig=1):
    mem_used = round(psutil.Process().memory_info().rss / (1024 * 1024), round_dig)
    print(f"Memory used: {mem_used} MB")


def get_obj_size(obj, round_dig=1):
    size = sys.getsizeof(obj) / (1024 * 1024)
    print(f"Object size: {round(size, round_dig)} MB")


def data_optimize(df, object_option=False):
    """Reduce the size of the input dataframe
    Parameters
    ----------
    df: pd.DataFrame
        input DataFrame
    object_option : bool, default=False
        if true, try to convert object to category
    Returns
    -------
    df: pd.DataFrame
        data type optimized output dataframe
    """
    print("ottimizzo i dati")
    # loop columns in the dataframe to downcast the dtype
    for col in df.columns:
        # process the int columns
        if df[col].dtype == 'int':
            col_min = df[col].min()
            col_max = df[col].max()
            # if all are non-negative, change to uint
            if col_min >= 0:
                if col_max < np.iinfo(np.uint8).max:
                    df[col] = df[col].astype(np.uint8)
                elif col_max < np.iinfo(np.uint16).max:
                    df[col] = df[col].astype(np.uint16)
                elif col_max < np.iinfo(np.uint32).max:
                    df[col] = df[col].astype(np.uint32)
                else:
                    df[col] = df[col]
            else:
                # if it has negative values, downcast based on the min and max
                if col_max < np.iinfo(np.int8).max and col_min > np.iinfo(np.int8).min:
                    df[col] = df[col].astype(np.int8)
                elif col_max < np.iinfo(np.int16).max and col_min > np.iinfo(np.int16).min:
                    df[col] = df[col].astype(np.int16)
                elif col_max < np.iinfo(np.int32).max and col_min > np.iinfo(np.int32).min:
                    df[col] = df[col].astype(np.int32)
                else:
                    df[col] = df[col]
        # process the float columns
        elif df[col].dtype == 'float':
            col_min = df[col].min()
            col_max = df[col].max()
            # downcast based on the min and max
            if col_min > np.finfo(np.float32).min and col_max < np.finfo(np.float32).max:
                df[col] = df[col].astype(np.float32)
            else:
                df[col] = df[col]
        if object_option:
            if df[col].dtype == 'object':
                if len(df[col].value_counts()) < 0.5 * df.shape[0]:
                    df[col] = df[col].astype('category')
    return df

# load_filtered_sales_parquet e smart_load_to_pd sono state centralizzate
# in utils/sales_loader.py e sono accessibili tramite utl.smart_load_to_pd
smart_load_to_pd = utl.smart_load_to_pd

cat_lookup = smart_load_to_pd(fname=lookup_file, sep=",", decimal=".", encoding="latin-1")
cat_lookup = cat_lookup[cat_lookup["sales_2y"] > 0]  # elimina categorie. Da 290 a 144
cat_lookup = cat_lookup.sort_values(by="sales_2y")

#-----------------------------------------------------------------
#CEGIL
#-----------------------------------------------------------------
def reduce_mem_usage(df, verbose=True):
    numerics = ['int16', 'int32', 'int64', 'float16', 'float32', 'float64']
    start_mem = df.memory_usage().sum() / 1024**2
    for col in df.columns:
        col_type = df[col].dtypes
        if col_type in numerics:
            c_min = df[col].min()
            c_max = df[col].max()
            if str(col_type)[:3] == 'int':
                if c_min > np.iinfo(np.int8).min and c_max < np.iinfo(np.int8).max:
                    df[col] = df[col].astype(np.int8)
                elif c_min > np.iinfo(np.int16).min and c_max < np.iinfo(np.int16).max:
                    df[col] = df[col].astype(np.int16)
                elif c_min > np.iinfo(np.int32).min and c_max < np.iinfo(np.int32).max:
                    df[col] = df[col].astype(np.int32)
                elif c_min > np.iinfo(np.int64).min and c_max < np.iinfo(np.int64).max:
                    df[col] = df[col].astype(np.int64)
            else:
                if c_min > np.finfo(np.float32).min and c_max < np.finfo(np.float32).max:
                    df[col] = df[col].astype(np.float32)
                else:
                    df[col] = df[col].astype(np.float64)
    end_mem = df.memory_usage().sum() / 1024**2
    if verbose: print('Mem. usage decreased to {:5.2f} Mb ({:.1f}% reduction)'.format(end_mem, 100 * (start_mem - end_mem) / start_mem))
    return df

#-----------------------------------------------------------------
#CEGIL FINE
#-----------------------------------------------------------------

# def run_analysis_customer(df, lvl, is_notass=False):
#     if df[lvl].nunique() == 1:
#         # Get the ID, name, desciption of the unique SKU in the demand group
#         sku_ls = df[lvl].iloc[0]
#         empty_out = empty_result([sku_ls], df[tx_id].nunique())
#         empty_out['total_count'] = df[cust_id].nunique()
#         # print("(!) ONLY ONE SKU IN THE DEMAND GROUP - NO SUBSTITUTES POSSIBLE SAVING ONE LINE OUTPUT - EXITING")
#         return empty_out.rename(columns={
#             'sku_intersect_count': 'overlap_customer_level',
#             'total_count': 'total_count_customers'})
#     # Prepare pairs of SKUs bought by each customer
#     aggregated = df[[lvl, cust_id]].drop_duplicates()
#     split_factor = 8 if is_notass else 1
#     split_hlpr = aggregated.groupby([lvl]).ngroup()
#     aggregated["split"] = split_hlpr // ((split_hlpr.max() + 1) / split_factor)
#     # print("hh", aggregated["split"].value_counts())
#     yule_res = []
#     for ii in range(split_factor):
#         cross_skus = (aggregated[aggregated["split"] == ii]
#                       .merge(aggregated.add_prefix('right_'), left_on=[
#             cust_id], right_on=['right_' + cust_id]))
#         # Create number of customers that bought each SKU
#         cross_skus['nunique_customer_id'] = cross_skus.groupby([lvl])[cust_id].transform(pd.Series.nunique)
#         # Keep SKUs bought by more than 10 customers
#         # This comes from the Alteryx workflow, and is retained here to match the Alteryx outputs
#         # cross_skus = cross_skus[cross_skus.nunique_customer_id >= 10]
#         #
#         # Create intersection
#         intersect = (cross_skus
#                      .groupby([lvl, 'right_' + lvl])
#                      .size()
#                      .reset_index()
#                      .rename(columns={0: 'sku_intersect_count'})
#                      )
#         # If the items never intersect in the baskets: print error, save with no substitutes and exit
#         if (intersect[intersect[lvl] != intersect['right_' + lvl]][lvl].nunique() == 0):
#             sku_ls = df[lvl].unique()
#             empty_out = empty_result(sku_ls, df[tx_id].nunique())
#             empty_out['total_count'] = df[cust_id].nunique()
#             # print("(!) NO INTERSECTION BETWEEN ITEMS IN THIS DEMAND GROUP - SUBSTITUTION IS 0 - SAVING EMPTY FILE")
#             return empty_out.rename(columns={
#                 'sku_intersect_count': 'overlap_customer_level',
#                 'total_count': 'total_count_customers'})
#         # Else we can compute the Yule's Q for each pair of SKUs
#         yule_res.append(compute_yule_household(intersect, cross_skus, lvl))
#         del intersect
#         del cross_skus
#     yule_cust = pd.concat(yule_res)
#     return yule_cust


def run_analysis_customer(df, lvl, is_notass=False):
    """
    Calcola la sostituibilità tra SKU a livello cliente in modo ottimizzato
    """
    # --- 1. Gestione dei casi limite (invariato) ---
    if df[lvl].nunique() <= 1:
        sku_ls = df[lvl].unique()
        # Se non ci sono SKU, restituisci un DataFrame vuoto con le colonne corrette
        if len(sku_ls) == 0:
            return pd.DataFrame(columns=[
                lvl, 'right_' + lvl, 'overlap_customer_level',
                'left_sku_count', 'right_sku_count', 'total_count_customers',
                'yulesQ'
            ])

        empty_out = empty_result([sku_ls[0]], df[tx_id].nunique())
        empty_out['total_count'] = df[cust_id].nunique()
        return empty_out.rename(columns={
            'sku_intersect_count': 'overlap_customer_level',
            'total_count': 'total_count_customers'})

    # --- 2. Preparazione dati e generazione efficiente delle coppie ---
    aggregated = df[[lvl, cust_id]].drop_duplicates()

    # Raggruppa per cliente e crea una lista di SKU acquistati da ciascuno
    sku_per_customer = aggregated.groupby(cust_id)[lvl].apply(list)

    # Filtra solo i clienti che hanno acquistato almeno 2 prodotti diversi
    sku_per_customer = sku_per_customer[sku_per_customer.str.len() >= 2]

    # Se nessun cliente ha comprato più di un prodotto, non ci sono coppie da analizzare
    if sku_per_customer.empty:
        sku_ls = df[lvl].unique()
        empty_out = empty_result(sku_ls, df[tx_id].nunique())
        empty_out['total_count'] = df[cust_id].nunique()
        return empty_out.rename(columns={
            'sku_intersect_count': 'overlap_customer_level',
            'total_count': 'total_count_customers'})

    # Usa `itertools.combinations` per generare tutte le coppie uniche di SKU per ogni cliente
    # `sorted(x)` assicura che la coppia (A, B) sia uguale a (B, A)
    pairs_list = sku_per_customer.apply(lambda x: list(combinations(sorted(x), 2)))

    # "Esplodi" la lista di coppie in righe, creando un DataFrame di tutte le coppie esistenti
    all_pairs = pairs_list.explode().dropna()
    pairs_df = pd.DataFrame(all_pairs.tolist(), index=all_pairs.index, columns=[lvl, 'right_' + lvl])

    # --- 3. Calcolo delle metriche necessarie ---

    # Calcola l'intersezione: quante volte ogni coppia è stata acquistata (da clienti diversi)
    intersect = pairs_df.groupby([lvl, 'right_' + lvl]).size().reset_index(name='sku_intersect_count')

    # Calcola il numero di clienti unici per ogni singolo SKU
    customers_per_sku = aggregated.groupby(lvl)[cust_id].nunique().reset_index(name='sku_count')

    # Numero totale di clienti unici nel gruppo di domanda
    total_customers = aggregated[cust_id].nunique()

    # --- 4. Unione dei dati e calcolo finale di Yule's Q ---

    # Unisci i dati dell'intersezione con i conteggi per SKU "A" (left)
    yule_cust = intersect.merge(
        customers_per_sku.rename(columns={'sku_count': 'left_sku_count'}),
        on=lvl
    )

    # Unisci i dati con i conteggi per SKU "B" (right)
    yule_cust = yule_cust.merge(
        customers_per_sku.rename(columns={lvl: 'right_' + lvl, 'sku_count': 'right_sku_count'}),
        on='right_' + lvl
    )

    # Aggiungi il conteggio totale dei clienti
    yule_cust['total_count'] = total_customers

    # Usa la funzione helper esistente per calcolare le metriche di Yule
    yule_cust = add_yule_columns(yule_cust)

    # Rinomina le colonne per corrispondere all'output atteso
    yule_cust = yule_cust.rename(columns={
        'sku_intersect_count': 'overlap_customer_level',
        'total_count': 'total_count_customers'
    })

    # Pulisci i risultati nulli
    yule_cust = yule_cust.dropna(subset=['yulesQ'])

    return yule_cust

def compute_yule_household(intersection, x_skus, level):
    # Create the left (SKU A) summary: number of customers that bought A
    left_cust_per_sku = (x_skus
                     .groupby([level])
                     .agg({cust_id: pd.Series.nunique})
                     .rename(columns={cust_id: 'left_sku_count'})
                     )
    # Create the left (SKU B) summary: number of customers that bought B
    right_cust_per_sku = (x_skus
                      .groupby(['right_'+level])
                      .agg({cust_id: pd.Series.nunique})
                      .rename(columns={cust_id: 'right_sku_count'})
                      )
    # Merge the data from SKU A, SKU B, and totals
    yule_customer = (intersection
                 .merge(left_cust_per_sku, on=[level])
                 .merge(right_cust_per_sku, on=['right_'+level])
                 )
    # Total number of customers
    yule_customer['total_count'] = x_skus[cust_id].nunique()
    # Calculate yule values and odd ratios from the metrics at customer level for each pair of SKUs
    yule_customer = add_yule_columns(yule_customer)
    yule_customer = yule_customer.rename(columns={'sku_intersect_count': 'overlap_customer_level',
                            'total_count': 'total_count_customers'})
    # Drop NAs in the output
    yule_customer = yule_customer.dropna(subset=['yulesQ'])
    return yule_customer


def empty_result(ids, qtys=None):
    out_len = len(ids)
    sold_qty = [0] * out_len if qtys is None else qtys
    # Create output with no substitutes
    empty_out = pd.DataFrame({sku_id: ids,
                             'right_'+sku_id: ['N/A'] * out_len,
                             'left_sku_count': sold_qty,
                             'right_sku_count': [0] * out_len,
                             'sku_intersect_count': sold_qty,
                             'l_odds': [0] * out_len,
                             'r_odds': [0] * out_len,
                             'odds_ratio': [0] * out_len,
                             'yulesQ': [0] * out_len,
                             'lift': [0] * out_len,
                             'substitution': [0] * out_len
                             })
    empty_out[sku_id] = empty_out[sku_id].astype(str)
    empty_out['right_'+sku_id] = empty_out['right_'+sku_id].astype(str) # else with len(ids)=0 becomes float64!
    return empty_out

def add_yule_columns(df):
    df = (df.assign
            (
                # Odds left/right and ratio
                l_odds=lambda x: x.sku_intersect_count / \
                    (x.left_sku_count - x.sku_intersect_count),
                r_odds=lambda x: (x.right_sku_count - x.sku_intersect_count) / (
                     x.total_count - x.left_sku_count - x.right_sku_count + x.sku_intersect_count),
                odds_ratio=lambda x: x.l_odds / x.r_odds,
                # Yules metric
                yulesQ=lambda x: (x.odds_ratio - 1) / (x.odds_ratio+1),
                #yulesQ_std=lambda x: (x.yulesQ + 1) / 2,
                # Lift
                lift=lambda x: (x.sku_intersect_count * x.total_count) / (x.left_sku_count * x.right_sku_count),
                # Debug
                #sku_both=lambda x: x.sku_intersect_count,
                #sku_left_no_right=lambda x: x.left_sku_count - x.sku_intersect_count,
                #sku_right_no_left=lambda x: x.right_sku_count - x.sku_intersect_count,
                #sku_neither=lambda x: x.total_count - x.left_sku_count - x.right_sku_count + x.sku_intersect_count,
            )
        )
    return df


def compute_yule_transaction(intersection, t_skus, level):
    # Count the number of transactions per SKUs
    transactions_per_skus = (t_skus.groupby(
        [level]).agg(
            {tx_id: pd.Series.nunique}
        ).reset_index(
        ).rename(columns={
            tx_id: 'sku_count'
        }))
    #
    # Merge the three data sets to get the numbers needed to compute yule
    yule_transaction = (intersection.merge(
        transactions_per_skus, on=[level], how='inner'
        ).rename(columns={
            'sku_count': 'left_sku_count'
        }).merge(
            transactions_per_skus.rename(columns={
                level: 'right_'+level
                }),
            on=['right_'+level],
            how='inner'
        ).rename(columns={
            'sku_count': 'right_sku_count'
        }))
    yule_transaction = yule_transaction[(
            yule_transaction['right_sku_count'] > .01 * yule_transaction['left_sku_count']
        ) & (
            yule_transaction['right_sku_count'] < 100 * yule_transaction['left_sku_count']
        )]
    # Total number of transactions
    yule_transaction['total_count'] = t_skus[tx_id].nunique()
    # Calculate yule values and odd ratios (same as before)
    yule_transaction = add_yule_columns(yule_transaction)
    #
    if yule_transaction.shape[0] > 0:
        yule_temp = yule_transaction.groupby([level])\
                    .apply(lambda x: pd.Series(
                            {'empty': np.all(x['yulesQ'].isna()),
                            'left_sku_count' : x['left_sku_count'].unique()[0] }), include_groups=False)\
                    .reset_index()
        yule_temp = yule_temp[yule_temp['empty']]
        #
        filtered_skus = empty_result(yule_temp[level], yule_temp['left_sku_count'])
        yule_transaction = yule_transaction.dropna(subset=['yulesQ'])
        yule_transaction = pd.concat([yule_transaction, filtered_skus])
    return yule_transaction


def run_analysis_transaction(df, lvl, is_notass=False):
    # Get the transaction granularity (without the customer granularity)
    trans_skus = df[[tx_id, lvl]].drop_duplicates()
    # Same as before, we create pair of skus(a) right and (b) left with transaction
    # data this time (instead of the customer data used previously)
    split_factor = 8 if is_notass else 1
    split_hlpr = trans_skus.groupby([lvl]).ngroup()
    trans_skus["split"] = split_hlpr // ((split_hlpr.max() + 1) / split_factor)
    # print("tx", trans_skus["split"].value_counts())
    yule_res = []
    for ii in range(split_factor):
        cross_tx = (trans_skus[trans_skus["split"] == ii]
                    .merge(trans_skus.add_prefix('right_'), left_on=[tx_id], right_on=['right_' + tx_id], how='inner')
                    .drop(columns=['right_' + tx_id])
                    )
        # Same as above: count the number of transactions per a pair of SKUs (A) left & (B) right
        intersect = (cross_tx
                     .groupby([sku_id, 'right_' + sku_id])
                     .size()
                     .reset_index()
                     .rename(columns={0: 'sku_intersect_count'})
                     )
        yule_res.append(compute_yule_transaction(intersect, cross_tx, lvl))
        del intersect
        del cross_tx

    # CEGIL 2 righe di codice per eliminare un warning su un concat.
    yule_res_filtrati = [df for df in yule_res if not df.empty]
    yule_trans = pd.concat(yule_res_filtrati)

    # yule_trans = pd.concat(yule_res)

    return yule_trans

def add_sku_metadata(df, desc, key_l, key_r, ren_dict, sku_role):
    #df[key_l] = convert_col_to_str(df[key_l])
    #desc[key_r] = convert_col_to_str(desc[key_r])
    #df[key_l] = df[key_l].astype(float).astype(int).astype(str)
    #desc[key_r] = desc[key_r].astype(str).replace('.0','')

    renames = { k: v+" ("+ sku_role+")" for k,v in ren_dict.items() }
    return df.merge(desc, left_on=[key_l], right_on=[key_r], how='left')\
                .rename(columns=renames)



def process_single_category(cat: str):

    #print("Running similarity for category: " + str(cat))
    cat_out = workarea_path + re.sub("/", "", str(cat))
    if not os.path.exists(cat_out):
        os.makedirs(cat_out)
    cat_out = cat_out + "/"
    cat_code = cat_lookup[cat_lookup["category"] == str(cat)]["cat_code"].values[0]
    sku_filter = workarea_path + re.sub("/", "", str(cat)) + "/" + sku_filt_file #sku_pdv_meta.csv
    cat_sim = cat_out + 'similarity' + '_' + str(cat_code).zfill(3) + ".csv"
    sales_files, multi_sales = utl.get_sales_files(sales_path, cat_code)
    #print(sales_files)
    if len(sales_files) == 0 or not os.path.exists(sku_filter):
        nosales_cat.append(cat)
        print("cat esclusa")
        return
    #
    print("Similarity: step 1")
    # Import helper metadata
    hlpr_cols2use = [
        sku_id, sku_desc, category, category_iri, sku_status,
        group_key, 'Settore', 'Marca', 'Fornitore'
    ]
    sales_cols2keep = [
        sku_id, pdv_id, cust_id, tx_date, qty, amount, promo, fidelity
    ]
    #prefinal_cols2keep = [sku_id, tx_id, cust_id]
    final_cols2keep = [sku_id, tx_id, cust_id]

    meta_dict = {
        sku_id: 'SKU ID',
        sku_desc: 'SKU Name',
        category: 'Cat. Merc. CNO',
        'SETTORE_DESC': 'Settore CNO',
        segment: 'Segmento CNO',
        sku_status: 'Stato CNO',
        'Marca': 'Marca CNO',
        'Fornitore': 'Fornitore CNO',
        category_iri: 'Categoria IRI',
        'Settore': 'Settore IRI',
        group_key: 'Tipo-Varieta IRI',
    }
    #
    print('leggo ',sku_filter)
    sku_flt = pd.read_csv(sku_filter, sep=";", decimal=",") #sku_pdv_meta.csv
    sku_flt = sku_flt.rename(columns={category_meta: category})  # Categoria Merceologica-->CATEG_MERC_PDV_DESC
    sku_flt[sku_id] = sku_flt[sku_id].astype(int).astype(str)
    sku_flt = sku_flt[hlpr_cols2use].drop_duplicates()
    #    sku_flt[sku_id] = sku_flt[sku_id].astype(str)
    # Active filters
    sku_flt = sku_flt[sku_flt[sku_status] == 'Attivo']
    sku_flt = sku_flt[sku_flt[category] == re.sub("_", " ", str(cat))]
    #print("sku_flt shape: ", sku_flt.shape)  # 47
    if (sku_flt[~sku_flt[sku_status].isna()][sku_status] == "Bloccato").all():
        print('tutti articoli in stato bloccato')
        empty_cat.append(cat)
        return
    if (sku_flt[group_key].sort_values() == 'Non in assortimento IRI / Non in assortimento IRI').all():
        print('tutti articoli Non in assortimento IRI')
        noassort_cat.append(cat)
        return
    sku_segments = sku_flt[group_key].sort_values().unique()
    print("groups to process:", ", ".join(sku_segments))
    #
    # Import sales data
    sim_res = []
    for ff in sales_files:
        print("loading " + ff)
        sku_buy = smart_load_to_pd(fname=ff, sep=';', decimal=",", encoding='latin-1')

        # <<< OTTIMIZZAZIONE CHIAVE >>>
        # Riduci la memoria e converti le colonne a bassa cardinalità in 'category'
        #print("sku_buy shape: ", sku_buy.shape)
        sku_buy = reduce_mem_usage(sku_buy)
        #sku_flt = reduce_mem_usage(sku_flt)
        sku_buy[promo] = sku_buy[promo].astype('category')
        sku_buy[fidelity] = sku_buy[fidelity].astype('category')

        # sku_buy = sku_buy[sku_buy[promo] == 0]
        # sku_buy = sku_buy[sku_buy[fidelity] == 1]
        # sku_buy = sku_buy[sku_buy[cust_id] != -1]
        #if filter_promo:

        # sku_buy = sku_buy[sales_cols2keep]
        #print("sku_buy shape: ", sku_buy.shape)  # 63,989,094
        if (sku_buy[~sku_buy[promo].isna()][promo] == 1).all():
            promo_cat.append(cat)
            continue
        sku_buy[qty] = sku_buy[qty].astype(float)
        sku_buy[amount] = sku_buy[amount].astype(float)
        #print("sku_buy shape (2): ", sku_buy.shape)  # 63,989,094
        # # Compute similarity
        print("Similarity: step 2")
        for grp in sku_segments:
            sku_grp = sku_flt[sku_flt[group_key] == grp]
            start = time.time()
            # it enters here if there is no transaction for this group in this transaction file
            # CEGIL: if ~sku_grp[sku_id].isin(sku_buy[sku_id].drop_duplicates()).any():
            if ~sku_grp[sku_id].isin(sku_buy[sku_id]).any():
                # if there is only a single transaction file, something went wrong...
                if not multi_sales:
                    nosales_grp.append(
                        pd.DataFrame({'category': cat, 'cat_code': cat_code,
                                      'group': grp}, index=[str(cat_code) + "_" + grp])
                    )
                continue
            print('running ' + str(grp) + ":")
            df_mrg = sku_buy.merge(sku_grp[[sku_id]].drop_duplicates(), how='inner', on=sku_id)
            # print('df_mrg shape -> init: ', df_mrg.shape)

            #            df_mrg = df_mrg.drop_duplicates()
            #            print('df_mrg shape -> duplicate ', df_mrg.shape)

            # Clean transactions data
            df_mrg = df_mrg[df_mrg[cust_id] != -1]
            # print('df_mrg shape -> customer_id: ', df_mrg.shape)

            # df_mrg = clean_tx_data(df_mrg)
            df_mrg = df_mrg[(df_mrg[qty] > 0) &
                            (df_mrg[amount] > 0) &
                            (df_mrg[fidelity] == 1)  # customers with fidelity
                            ]
            # print('df_mrg shape -> qty>0 ', df_mrg.shape)

            prefinal_cols2keep = [sku_id, cust_id, pdv_id, tx_date]
            df_mrg = df_mrg[prefinal_cols2keep].astype({sku_id: str, cust_id: str, pdv_id: str, tx_date: str})
            # print('df_mrg shape -> reduce cols: ', df_mrg.shape)

            # df_mrg[tx_id] = df_mrg[cust_id] + "_" + df_mrg[pdv_id] + "_" + df_mrg[tx_date]
            df_mrg[tx_id] = pd.factorize(
                df_mrg[cust_id].astype(str) + '_' + df_mrg[pdv_id].astype(str) + '_' + df_mrg[tx_date].astype(str))[0]
            # print('clean_tx_data -> tx_id: ', df_mrg.shape)

            # print('clean_tx_data step 1: convert in str')
            # df_mrg[tx_date] = pd.to_datetime(df_mrg[tx_date], format='%Y%m%d')

            df_mrg = df_mrg[final_cols2keep].astype({sku_id: str})
            # print('df_mrg shape -> final step ', df_mrg.shape)

            if df_mrg.shape[0] == 0:
                nosales_grp.append(
                    pd.DataFrame({'category': cat, 'cat_code': cat_code,
                                  'group': grp}, index=[str(cat_code) + "_" + grp])
                )
                continue
            # print("tx data shape: ", df_mrg.shape)
            if df_mrg[[tx_id, sku_id]].drop_duplicates().shape[0] != df_mrg.shape[0]:
                review_cat.append(
                    pd.DataFrame({'category': cat, 'cat_code': cat_code,
                                  'group': grp, 'tx_len': df_mrg.shape[0],
                                  'tx_unique': df_mrg[[tx_id, sku_id]].drop_duplicates().shape[0]
                                  }, index=[str(cat_code) + "_" + grp])
                )
                # continue
            df_mrg = df_mrg.drop_duplicates()
            #print("Sales loaded in %.1f minutes" % ((time.time() - start) / 60))
            #
            start = time.time()
            # Actual analysis
            # --------------------------------------------------------------------#
            #                 STEP 1 YULE'S Q AT HOUSEHOLD LEVEL                  #
            # --------------------------------------------------------------------#
            # print("STEP 1: Computing Yule's Q at customer level")
            yule_customer = run_analysis_customer(df_mrg, sku_id, "Non in assortimento" in grp)
            # --------------------------------------------------------------------#
            #                STEP 2 YULE'S Q AT TRANSACTION LEVEL                 #
            # --------------------------------------------------------------------#
            # print("STEP 2: Computing Yule's Q at transaction level")
            yule_transaction = run_analysis_transaction(df_mrg, sku_id, "Non in assortimento" in grp)
            # --------------------------------------------------------------------#
            #         STEP 3 MERGE HOUSEHOLD, TRANSACTION & SKU INFO              #
            # --------------------------------------------------------------------#
            # print("STEP 3: Join the Yule's Q tables and add SKU info")
            # Merge transaction yule with customer yule results
            # we use left merge because we have filtered a few pairs if sales were too different
            yule_customer[sku_id] = yule_customer[sku_id].astype(str).replace('.0', '')
            yule_customer['right_' + sku_id] = yule_customer['right_' + sku_id].astype(str).replace('.0', '')
            yule_transaction[sku_id] = yule_transaction[sku_id].astype(str).replace('.0', '')
            yule_transaction['right_' + sku_id] = yule_transaction['right_' + sku_id].astype(str).replace('.0', '')
            #

            yule_res = yule_transaction.merge(yule_customer,
                                              on=[sku_id, 'right_' + sku_id],
                                              how='left',
                                              suffixes=('_transaction', '_customer'))
            # Fill NAs with -1
            yule_res.yulesQ_transaction = yule_res.yulesQ_transaction.fillna(-1)
            # Compute substitution score & its normalized version
            # yule_res['substitution'] = yule_res.apply(
            #     lambda x: (
            #             x.yulesQ_customer - x.yulesQ_transaction) if (x.yulesQ_customer >= x.yulesQ_transaction) else 0,
            #     axis=1)
            yule_res['substitution'] = np.where(
                yule_res['yulesQ_customer'] >= yule_res['yulesQ_transaction'],
                yule_res['yulesQ_customer'] - yule_res['yulesQ_transaction'],
                0
            )
            # Add SKU metadata (product description, category, etc.)
            yule_res = add_sku_metadata(yule_res, sku_grp, sku_id, sku_id, meta_dict, 'Focus')
            yule_res = add_sku_metadata(yule_res, sku_grp, 'right_' + sku_id, sku_id, meta_dict, 'Substitute')
            yule_res = yule_res.drop(columns=['right_' + sku_id])
            yule_res = yule_res.drop_duplicates()
            #
            yule_res = yule_res.rename(columns={
                'left_sku_count_transaction': sku_sold_focus,
                'right_sku_count_transaction': sku_sold_sub,
                'left_sku_count_customer': sku_cust_focus,
                'right_sku_count_customer': sku_cust_sub
            })
            #
            yule_res[group_key] = str(grp)
            sim_res.append(yule_res)
            del sku_grp
            del df_mrg
            del yule_customer
            del yule_transaction
            del yule_res
            gc.collect()
            #print("Analysis finished in %.1f minutes" % ((time.time() - start) / 60))
        #
        del sku_buy
        gc.collect()
    del sku_flt
    if len(sim_res):
        sim_res = pd.concat(sim_res)
        sim_res = sim_res.sort_values(
            by=[group_key, sku_id_focus, sku_subscore],
            axis=0,
            ascending=(True, True, False))
        #if write_out:
        sim_res[output_cols].to_csv(cat_sim, index=False, sep=";", decimal=",")

    del sim_res
    #gc.collect()

    #print(f"prepare metadata per '{category}' completato.")


if __name__ == "__main__":
    # Il programma ora si aspetta un argomento dalla riga di comando.
    # sys.argv è una lista che contiene gli argomenti:
    # sys.argv[0] è il nome dello script ("prefiltering.py")
    # sys.argv[1] è il primo argomento (la nostra categoria)

    if len(sys.argv) < 2:
        print("ERRORE: Nessuna categoria fornita.")
        sys.exit(1)  # Esce con un codice di errore

    # Prende la categoria dal primo argomento passato
    current_category = sys.argv[1]

    # Lancia l'elaborazione solo per quella categoria
    process_single_category(current_category)

    # Quando lo script termina, il processo viene distrutto e la memoria liberata.
    sys.exit(0)  # Esce indicando successo
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                