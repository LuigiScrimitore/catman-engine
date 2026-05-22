import gc

import numpy as np
import pandas as pd
import re
import sys
import os
import psutil
import time
import utils as utl

# config_file = "./config/configurazioni.yaml"
# with open(config_file, "r") as f:
#     config = yaml.safe_load(f)
config = utl.get_Config()

input_path= config['paths']['input_path']
sales_path = config['paths']['sales_path']
workarea_path= config['paths']['workarea_path']
# meta_path = config['paths']['meta_path']
# outp_path = config['paths']['aux_path']

# files to process
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
sku_id = lista_colonne['sku_id']
sku_desc = lista_colonne['sku_desc']
cust_id = lista_colonne['cust_id']
pdv_id = lista_colonne['pdv_id']
tx_id = lista_colonne['tx_id']
tx_date = lista_colonne['tx_date']
amount = lista_colonne['amount']
qty = lista_colonne['qty']
fidelity = lista_colonne['fidelity']
promo = lista_colonne['promo']
sku_status = lista_colonne['sku_status']
margin_cost = lista_colonne['margin_cost']
margin_sold = lista_colonne['margin_sold']

## TODO: these shall be configurable as well...
cluster2rank_map = {
    'SUPERMINIMO': 7,
    'MINIMO': 6,
    'MEDIO1': 5,
    'MEDIO2': 4,
    'MASSIMO': 3,
    'SUPERMASSIMO': 2,
    'SPAZIO': 1
}

insegna2formato_map = {
    '1.Spazio Conad': 'Iper',
    '3.SuperStore': 'Super',
    '4.CONAD Ins.': 'Super',
    '5.CONAD City': 'Super',
    '6.Sapori & Dintorni': 'Super',
    '7.Margherita': 'Super',
    'Spazio Conad': 'Iper',
    'SuperStore': 'Super',
    'CONAD Ins.': 'Super',
    'CONAD City': 'Super',
    'Sapori & Dintorni': 'Super',
    'Margherita': 'Super',
}

insegna2canale_map = {
    '1.Spazio Conad': 'Spazio',
    '3.SuperStore': 'Sstore',
    '4.CONAD Ins.': 'Super',
    '5.CONAD City': 'City',
    '6.Sapori & Dintorni': 'Super',
    '7.Margherita': 'Super',

    'Spazio Conad': 'Spazio',
    'SuperStore': 'Sstore',
    'CONAD Ins.': 'Super',
    'CONAD City': 'City',
    'Sapori & Dintorni': 'Super',
    'Margherita': 'Super',
}


# ## Check current memory usage of whole process (include objects and installed packages, ...)
# def get_memory_usage(round_dig=1):
#     mem_used = round(psutil.Process().memory_info().rss / (1024 * 1024), round_dig)
#     print(f"Memory used: {mem_used} MB")


# def get_obj_size(obj, round_dig=1):
#     size = sys.getsizeof(obj) / (1024 * 1024)
#     print(f"Object size: {round(size, round_dig)} MB")


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
    #print("ottimizzo i dati")
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


def add_missing_clusters(df, lvl_of_detail_cols, sorted_clusters_map, fillna=True):
    mux_values_all = [
        df[col].unique() if col != 'Cluster' else list(sorted_clusters_map.keys())
        for col in lvl_of_detail_cols
    ]
    # create complete multi-index
    mux = pd.MultiIndex.from_product(
        mux_values_all,
        names=lvl_of_detail_cols
    )
    if fillna:
        return df.set_index(
            lvl_of_detail_cols
        ).reindex(
            mux, fill_value=0
        ).reset_index(
        )
    else:
        return df.set_index(
            lvl_of_detail_cols
        ).reindex(
            mux
        ).reset_index(
        )


def clean_tx_data(df_tx):
    # Clean data
    # df_tx[sku_id] = df_tx[sku_id].astype(str)
    df = df_tx.copy()
    df[tx_id] = df[cust_id].astype(str) + "_" + df[pdv_id].astype(str) + "_" + df[tx_date].astype(str)
    df[tx_date] = pd.to_datetime(df[tx_date].astype(str), format='%Y-%m-%d')
    # Filter invalid transactions
    df = df[df[cust_id] != -1]
    df['has_fide'] = df.groupby(cust_id)[fidelity].transform('max')
    df[qty] = df[qty].astype(float)
    df[amount] = df[amount].astype(float)
    df = df[(df[qty] > 0) &
                  (df[amount] > 0) &
                  (df['has_fide'] == 1)]
    df = df.drop('has_fide', axis=1)
    return df


# # 1. Import data

# ## 1.1 Import anagrafica pdv
def process_anagrafica_pdv(file, optimize_flag=True):
    print("carico anagrafica pdv")
    pdv_anag = smart_load_to_pd(fname=file, sep=';', decimal=',', encoding='latin-1')
    pdv_anag = pdv_anag.loc[
        ~pdv_anag['INSEGNA'].str.contains('Pet Store Conad', case=0)
    ].rename(columns={
        'REGIONE': 'Regione'
    })
    #pdv_anag['Regione'] = pdv_anag['Regione'].apply(lambda x: re.sub(r"^\d\.", "", x))
    pdv_anag['Regione'].str.replace(r"^\d\.", "", regex=True)
    #pdv_anag['INSEGNA'] = pdv_anag['INSEGNA'].apply(lambda x: re.sub(r"^\d\.", "", x))
    pdv_anag['INSEGNA'].str.replace(r"^\d\.", "", regex=True)

    pdv_anag['Formato'] = pdv_anag['INSEGNA'].map(pd.Series(insegna2formato_map))
    pdv_anag['Canale'] = pdv_anag['INSEGNA'].map(pd.Series(insegna2canale_map))
    pdv_cols2keep = ['Formato', 'Canale', 'Regione', 'PDV_COD']
    pdv_anag = pdv_anag[pdv_cols2keep].sort_values(
        by=pdv_cols2keep
    ).astype({
        pdv_id: float
    })
    if optimize_flag:
        optimize_flag = False
    return pdv_anag


# ## 1.2 Import anagrafica clusters

def process_anagrafica_clusters(file, optimize_flag=True):
    print("carico anagrafica cluster")
    clusters_anag = smart_load_to_pd(fname=file, sep=';', decimal=",", encoding='latin-1')
    # Assign SKU-PDV pairs to smallest cluster available (if assigned to multiple clusters)
    clusters_anag = clusters_anag.rename(columns={
        'IPER': 'SPAZIO'
    })
    clusters_anag['Cluster'] = clusters_anag[
        [
            'SPAZIO',
            'SUPERMASSIMO',
            'MASSIMO',
            'MEDIO2',
            'MEDIO1',
            'MINIMO',
            'SUPERMINIMO',
            'NON_DEFINITO'
        ]
    ].idxmax(axis=1)
    clusters_anag = clusters_anag.astype({
        sku_id: str,
        pdv_id: float
    })[[sku_id, pdv_id, 'Cluster']]
    if optimize_flag:
        clusters_anag = data_optimize(clusters_anag)
    return clusters_anag


# ## 1.3 Import metadata

# # CEGIL: FUNZIONE NON PIU' UTILIZZATA
# def filter_metadata(df, cat2keep):
#     # print("filtro i metadati")
#     # restrict to few categories (including listing candidates)
#     iri_categs = df[df[category_meta].isin(cat2keep)][category_iri].drop_duplicates()
#     # the above contains a few errors due to mismatch in EAN, but we need to live with it
#     df = df[(df[category_iri].isin(iri_categs)) &
#             (df[category_meta].isin(cat2keep + ['Mancato Riscontro', 'Non in assortimento CNO']))]
#     return df

# # CEGIL: FUNZIONE NON PIU' UTILIZZATA
# def fix_non_valid_eans_in_metadata(sku_meta):
#     #print("fix ean")
#     # print('Metadata shape (current): ', sku_meta.shape)
#     # Identify non valid EANs
#     check_eans = sku_meta.groupby(
#         ['Articolo Radice_COD', 'Formato', 'Canale', 'Regione', 'Cluster']
#     )['EAN'].nunique(
#     ).reset_index(
#     ).rename(columns={'EAN': 'n_EANs'})
#     # Save the list of non valid EANs
#     unknown_eans = sku_meta.merge(
#         check_eans[check_eans["n_EANs"] > 1],
#         on=['Articolo Radice_COD', 'Formato', 'Canale', 'Regione', 'Cluster']
#     )['EAN'].unique().tolist()
#     # print('Metadata shape for non valid EANs (current): ',
#     sku_meta['Articolo Radice_COD'] = sku_meta['Articolo Radice_COD'].astype(str)
#     sku_meta_fixed_eans = sku_meta.loc[
#         sku_meta['EAN'].isin(unknown_eans)
#     ].groupby(
#         ['Articolo Radice_COD', 'Formato', 'Canale', 'Regione', 'Cluster'],
#         as_index=False
#     ).agg({
#         'EAN': "min",
#         'Articolo Radice': "min",
#         'Prodotto': "min",
#         sku_status: "min",
#         'Categoria': "min",
#         'Categoria Merceologica': "min",
#         'Settore': "min",
#         'Settore merceologico': "min",
#         'Tipo': "min",
#         'Varieta': "min",
#         'Marca': "min",
#         'Fornitore': "min",
#         'CNO_AC_Vendite in Valore': "min",
#         'CNO_AC_Vendite in Volume': "min",
#         'MKT_AC_Vendite in Valore': "min",
#         'MKT_AC_Vendite in Volume': "min",
#         'Margine Costo Netto': "mean",
#         'Margine Venduto': "mean",
#         'Sellout Importo': "min",
#         'Sellout Quantita': "min",
#         sku_score: "min",
#         group_key: "min",
#         'CNO_Margine': "mean",
#         'CNO_Margine_pct': "mean"
#     })
#     #      sku_meta.loc[sku_meta['EAN'].isin(unknown_eans)].shape)
#     # Create the meta subset for the non valid EANs, aggregating EAN and margin
#     # print('Metadata shape for non valid EANs (fixed, aggregated): ',
#     #      sku_meta_fixed_eans.shape)
#     # Merge back together
#     sku_meta = pd.concat(
#         [sku_meta.loc[~sku_meta['EAN'].isin(unknown_eans)],
#          sku_meta_fixed_eans])
#     # print('Final metadata shape: ', sku_meta.shape)
#     return sku_meta


def process_metadata(file, cat2keep, optimize_flag=True, rename=False):
    print(f"carico il file ",file)
    sku_meta = smart_load_to_pd(fname=file, sep=';', decimal='.', encoding='latin-1',
                                spec_types={'EAN': object, 'Micro Reparto_COD': object,
                                            'Articolo Marchio': object, 'Anno Mobile': object,
                                            'ART_STATO_DESC': object})
    # CEGIL fix temporaneo per i non in assortimento cno
    # sku_meta.loc[
    #    (sku_meta['Categoria Merceologica'] == 'BIRRE') &
    #    (sku_meta["CNO_AC_Vendite in Valore"] < 1), 'Categoria Merceologica'
    # ] = 'Non in assortimento CNO'

    # sku_meta.loc[
    #     ~(sku_meta[category_meta].isin(['Mancato Riscontro', 'Non in assortimento CNO'])) &
    #     (sku_meta["CNO_AC_Vendite in Valore"] < 1) &
    #     (sku_meta["Cluster"] == 'NO_CLUSTER'),
    #     'Categoria Merceologica'
    # ] = 'Non in assortimento CNO'

    # sku_meta = data_optimize(sku_meta)

    # sku_meta = filter_metadata(sku_meta, [re.sub("_", " ", x) for x in cat2keep])

    # sku_meta = fix_non_valid_eans_in_metadata(sku_meta)
    return sku_meta


# ## 1.4 Import transactions data

# Import SCONTRINATO

# def load_n_clean_sales(file, optimize_flag=True):
#     tx_cols2keep = [cust_id, pdv_id, sku_id, tx_date, fidelity, promo, qty, amount]
#     sku_buy = smart_load_to_pd(fname=file, sep=';', decimal=",", encoding='latin-1')
#     sku_buy = sku_buy[tx_cols2keep]
#     sku_buy = sku_buy.astype({
#         sku_id: str,
#         pdv_id: float
#     })
#
#     print("start load_n_clean_sales")
#
#     if optimize_flag:
#         sku_buy = data_optimize(sku_buy)
#     # Clean transactions data
#     print('Sales data shape before cleaning: ', sku_buy.shape)  # 55,762,373
#     print('Unique SKUs before cleaning:', sku_buy[sku_id].nunique())  # 1408
#     sku_buy = clean_tx_data(sku_buy)
#     print('Sales data shape after cleaning: ', sku_buy.shape)  # 46,270,623
#     print('Unique SKUs after cleaning: ', sku_buy[sku_id].nunique())  # 1400
#     #
#     # Separate volumes impact coming from products not in promo
#     sku_buy[amount + '_promo'] = sku_buy[amount] * sku_buy[promo]
#     sku_buy[qty + '_promo'] = sku_buy[qty] * sku_buy[promo]
#     return sku_buy

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



def load_sales(file, optimize_flag=False):
    tx_cols2keep = [cust_id, pdv_id, sku_id, tx_date, fidelity, promo, qty, amount]
    sku_buy = smart_load_to_pd(fname=file, sep=';', decimal=",", encoding='latin-1')

    # _, file_ext = os.path.splitext(fname)
    # if spec_types is None:
    #     spec_types = {}
    # if file_ext == ".zip":
    #     return pd.read_csv(fname, compression='zip', sep=sep, decimal=decimal, encoding=encoding, dtype=spec_types)
    # elif file_ext == ".parquet":
    #     #df = pd.read_parquet(fname)
    #     if fname=='./input/NEW_dataZipped/scont_l2y_050.parquet':
    #         min_data = '2024-05-04'
    #         df = load_filtered_sales_parquet(fname, min_data)
    #     else:
    #         df = pd.read_parquet(fname)
    #
    #     return df
    # else:
    #     return pd.read_csv(fname, sep=sep, decimal=decimal, encoding=encoding, dtype=spec_types, low_memory=True)


    sku_buy = sku_buy.astype({
        sku_id: str,
        pdv_id: float
    })
    sku_buy = reduce_mem_usage(sku_buy)
    sku_buy = sku_buy[tx_cols2keep]
    if optimize_flag:
        sku_buy = data_optimize(sku_buy)
    return sku_buy


def clean_sales(tx_df):
    # Clean transactions data
    #print("start clean_sales")
    #print('Sales data shape before cleaning: ', tx_df.shape)  # 55,762,373
    #print('Unique SKUs before cleaning:', tx_df[sku_id].nunique())  # 1408
    tx_df = clean_tx_data(tx_df)
    #print('Sales data shape after cleaning: ', tx_df.shape)  # 46,270,623
    #print('Unique SKUs after cleaning: ', tx_df[sku_id].nunique())  # 1400
    #
    # Separate volumes impact coming from products not in promo
    tx_df[amount + '_promo'] = tx_df[amount] * tx_df[promo]
    tx_df[qty + '_promo'] = tx_df[qty] * tx_df[promo]
    return tx_df


# # 2. Filter and merge imported files

# ## 2.1 Merge: PDV anagrafica + clusters anagrafica + metadata

def create_metadata_helper(pdv, clusters, metadata, optimize_flag=True):
    ## Merge PDV anagrafica with clusters anagrafica
    sku_pdv_clus = clusters.merge(
        pdv,
        on=pdv_id,
        how='inner'
    )
    #print('sku_pdv_clus shape', sku_pdv_clus.shape)  # 7,761,966
    ## Merge with metadata
    sku_pdv_clus['ART_RADICE_COD'] = sku_pdv_clus['ART_RADICE_COD'].astype(float).astype(int).astype(str)
    # metadata['Articolo Radice_COD']=metadata['Articolo Radice_COD'].fillna(0).astype(float).astype(int).astype(str)
    # metadata['Articolo Radice_COD'] = pd.to_numeric(
    #     metadata['Articolo Radice_COD'], errors='coerce').fillna(0).astype(int).astype(str)
    hlpr_meta = metadata[
        ['Articolo Radice_COD', 'Articolo Radice', sku_status,
         'Cluster', 'Formato', 'Canale', 'Regione',
         category_meta, category_iri, group_key,
         'Settore', 'Marca', 'Fornitore', sku_score,
         'Sellout Importo', 'Sellout Quantita',
         "Margine Costo Netto", "Margine Venduto", 'CNO_Margine', 'CNO_Margine_pct'
         ]].drop_duplicates(
    ).rename(columns={
        'Articolo Radice_COD': sku_id,
        'Articolo Radice': sku_desc
    }).merge(
        sku_pdv_clus,
        on=[sku_id, 'Formato', 'Canale', 'Regione', 'Cluster'],
        how='inner'
    )
    if optimize_flag:
        hlpr_meta = data_optimize(hlpr_meta)
    # print(hlpr_meta.shape)  # 355,056
    return hlpr_meta


# ## 2.2 Merge: scontrinato + all helpers (anagrafica & metadata)

def create_sales_plus_meta(sales, meta_helper):
    # Merge scontrinato with metadati
    meta_cols2keep = [sku_id, pdv_id, 'Cluster', 'Regione', 'Categoria Merceologica', group_key]
    sku_buy = sales.merge(
        meta_helper[meta_cols2keep],
        how='inner',
        on=[sku_id, pdv_id]
    )
    return sku_buy


# ## 2.3 Aggregations for metadata
# ### 2.3.1 Metadata at the desired level of detail: SKU-cluster-regione

# # moved below...

# ### 2.3.2 Margins at SKU-cluster-region level
# Used in listing to add margins data for the top 10 susbtitutes and in totals to estimate the total margins at regional level.

def get_totals_by_LOD(df, grouping_cols):
    # Aggregate sellout from metadata
    totals_by_sku = df.groupby(
        grouping_cols
    ).agg({
        'Sellout Importo': 'sum',
        'Sellout Quantita': 'sum'
    })
    # Aggregate margins from metadata
    # margin is already shown as yearly figure and it's aggregated
    # from metadata at level of sku, regione, cluster + formato, canale
    margin_by_sku = df.groupby(
        grouping_cols + ['Canale', 'Formato']
    ).agg({
        margin_cost: 'max',
        margin_sold: 'max'
    }).reset_index()
    margin_by_sku = margin_by_sku.groupby(
        grouping_cols
    ).agg({
        margin_cost: 'sum',
        margin_sold: 'sum'
    })
    margin_by_sku = margin_by_sku.fillna(0)
    margin_by_sku['avg_monthly_margin_cost'] = margin_by_sku[margin_cost] / 12
    margin_by_sku['avg_monthly_margin_sold'] = margin_by_sku[margin_sold] / 12
    # Merge results
    totals_by_sku = totals_by_sku.join(
        margin_by_sku,
        how='outer'
    ).reset_index(
    ).rename(columns={
        'Categoria': 'Categoria IRI',
        margin_cost: 'total_margin_cost',
        margin_sold: 'total_margin_sold',
        'Sellout Importo': 'total_sellout_revenues',
        'Sellout Quantita': 'total_sellout_volume'
    })
    return totals_by_sku


# # 3. Create helper files for next steps
#

# ## 3.1 CNO vs market sales by category

def get_mkt_vs_cno(df, grouping_cols):
    mk_vs_cno = df.groupby(grouping_cols
                           ).agg(
        items=('Articolo Radice_COD', 'size'),
        market_revenue=('MKT_AC_Vendite in Valore', 'sum'),
        market_volume=('MKT_AC_Vendite in Volume', 'sum'),
        cno_revenue=('CNO_AC_Vendite in Valore', 'sum'),
        cno_volume=('CNO_AC_Vendite in Volume', 'sum'),
        avg_cno_margin_cost=('Margine Costo Netto', "mean"),
        avg_cno_margin_sold=('Margine Venduto', "mean")
    ).reset_index()
    mk_vs_cno['perc_revenue'] = mk_vs_cno['cno_revenue'] / mk_vs_cno['market_revenue']
    mk_vs_cno['perc_volume'] = mk_vs_cno['cno_volume'] / mk_vs_cno['market_volume']
    # save the actual file we need for listing
    mk_vs_cno.loc[mk_vs_cno['perc_revenue'] > 1, 'perc_revenue'] = 1
    mk_vs_cno.loc[mk_vs_cno['perc_volume'] > 1, 'perc_volume'] = 1
    mk_vs_cno = mk_vs_cno.sort_values(
        by='items',
        ascending=False
    )
    return mk_vs_cno


# ## 3.2 CNO Sales by cluster and by cluster-region
# #### (From metadata)

def get_cumulative_perc(
        df,
        col2agg,
        sortby_cols,
        grouping_cols,
        category_col=category_iri,
        asc=True
):
    if asc:
        ascending_param = False
    else:
        ascending_param = True
    return df.sort_values(
        by=sortby_cols,
        ascending=ascending_param
    ).groupby(grouping_cols
              )[col2agg].cumsum()


def get_cno_sales_agg(df_meta, grouping_cols, sorted_clusters_map):
    grp_cols_no_cluster = [c for c in grouping_cols if c not in 'Cluster']
    # Keep SKUs in CNO and valid clusters
    sales_agg = df_meta.loc[(
                                ~df_meta['Articolo Radice_COD'].isna()) & (
                                ~df_meta['Sellout Importo'].isna()) & (
                                df_meta['Cluster'].isin(cluster2rank_map.keys())
                            )].groupby(grouping_cols).agg(
        cno_revenue=('CNO_AC_Vendite in Valore', 'sum'),
        cno_volume=('CNO_AC_Vendite in Volume', 'sum'),
        cno_sellout_revenue=('Sellout Importo', 'sum'),
        cno_sellout_volume=('Sellout Quantita', 'sum'),
        cno_margin_cost=('Margine Costo Netto', 'sum'),
        cno_margin_sold=('Margine Venduto', 'sum')
    ).reset_index()
    # Add missing clusters and set their values to 0
    sales_agg = add_missing_clusters(
        df=sales_agg,
        lvl_of_detail_cols=grouping_cols,
        sorted_clusters_map=sorted_clusters_map
    )
    sales_agg['Clus_Help'] = sales_agg['Cluster'].map(sorted_clusters_map)

    ##
    def get_total(df, grp_cols, col2agg):
        return sales_agg.groupby(grp_cols)[col2agg].transform('sum')

    ##
    sales_agg['cno_tot_revenue'] = get_total(sales_agg, grp_cols_no_cluster, 'cno_revenue')
    sales_agg['cno_tot_volume'] = get_total(sales_agg, grp_cols_no_cluster, 'cno_volume')
    sales_agg['cno_tot_sellout_revenue'] = get_total(sales_agg, grp_cols_no_cluster, 'cno_sellout_revenue')
    sales_agg['cno_tot_sellout_volume'] = get_total(sales_agg, grp_cols_no_cluster, 'cno_sellout_volume')
    sales_agg['cno_tot_margin_cost'] = get_total(sales_agg, grp_cols_no_cluster, 'cno_margin_cost')
    sales_agg['cno_tot_margin_sold'] = get_total(sales_agg, grp_cols_no_cluster, 'cno_margin_sold')
    sales_agg['clus_rev_perc_cno_by_cat'] = sales_agg['cno_revenue'] / \
                                            sales_agg['cno_tot_revenue']
    sales_agg['clus_vol_perc_cno_by_cat'] = sales_agg['cno_volume'] / \
                                            sales_agg['cno_tot_volume']
    sales_agg['clus_sellout_rev_perc_cno_by_cat'] = sales_agg['cno_sellout_revenue'] / \
                                                    sales_agg['cno_tot_sellout_revenue']
    sales_agg['clus_sellout_vol_perc_cno_by_cat'] = sales_agg['cno_sellout_volume'] / \
                                                    sales_agg['cno_tot_sellout_volume']
    sales_agg['clus_margin_cost_perc_cno_by_cat'] = sales_agg['cno_margin_cost'] / \
                                                    sales_agg['cno_tot_margin_cost']
    sales_agg['clus_margin_sold_perc_cno_by_cat'] = sales_agg['cno_margin_sold'] / \
                                                    sales_agg['cno_tot_margin_sold']
    sales_agg = sales_agg[
        grouping_cols + [
            'Clus_Help', 'clus_rev_perc_cno_by_cat', 'clus_vol_perc_cno_by_cat',
            'clus_sellout_rev_perc_cno_by_cat', 'clus_sellout_vol_perc_cno_by_cat',
            'clus_margin_cost_perc_cno_by_cat', 'clus_margin_sold_perc_cno_by_cat'
        ]]
    # Add cumulative metrics for revenue and volume
    sortby_cols = grouping_cols.copy()
    sortby_cols.remove('Cluster')
    sortby_cols.append('Clus_Help')
    for col in [c for c in sales_agg.columns if '_perc_cno_by_cat' in c]:
        for flag in [True, False]:
            suffix = '_asc' if flag else '_desc'
            new_col_name = 'cum_' + col.replace('clus_', '') + suffix
            sales_agg[new_col_name] = get_cumulative_perc(
                col2agg=col,
                df=sales_agg,
                sortby_cols=sortby_cols,
                grouping_cols=grp_cols_no_cluster,
                asc=flag
            )
    return sales_agg


# ## 3.3 Sales per SKU
# Useful to add to clustering and loyalty results in order to understand volumes moved by each SKU in the group.

def volumes_agg_by_sku(df, grouping_cols):
    max_date = df[tx_date].max()
    volumes_by_sku = df \
        .groupby([pd.Grouper(key=tx_date, freq='ME')] + grouping_cols) \
        .agg({
        tx_id: pd.Series.nunique,
        amount: 'sum',
        qty: 'sum',
        amount + '_promo': "sum",
        qty + '_promo': "sum"
    }) \
        .reset_index()
    volumes_by_sku = volumes_by_sku \
        .groupby(grouping_cols) \
        .agg({
        tx_id: 'sum',
        amount: 'sum',
        qty: 'sum',
        amount + '_promo': "sum",
        qty + '_promo': "sum",
        tx_date: 'min'
    }) \
        .reset_index() \
        .fillna(0)
    volumes_by_sku['months_since_first_tx'] = \
        (max_date.year - volumes_by_sku[tx_date].dt.year) * 12 + \
        (max_date.month - volumes_by_sku[tx_date].dt.month) + 1
    volumes_by_sku['avg_monthly_revenues'] = volumes_by_sku[amount] / \
                                             volumes_by_sku['months_since_first_tx']
    volumes_by_sku['avg_monthly_quantity'] = volumes_by_sku[qty] / \
                                             volumes_by_sku['months_since_first_tx']
    return volumes_by_sku.drop(columns=['months_since_first_tx', tx_date]) \
        .rename(columns={
        sku_id: "sku_id",
        tx_id: "num_tx",
        qty: "tot_pieces",
        amount: "tot_amount",
        qty + '_promo': "tot_pieces_nopr",
        amount + '_promo': "tot_amount_nopr"})

cat_lookup = smart_load_to_pd(fname=lookup_file, sep=",", decimal=".", encoding="latin-1")
cat_lookup = cat_lookup[cat_lookup["sales_2y"] > 0]  # elimina categorie. Da 290 a 144
cat_lookup = cat_lookup.sort_values(by="sales_2y")

empty_cat = []
noclus_cat = []



def elaborazione(cat):
    print("elaboro i dati")
    start_meta = time.time()
    cat_out = workarea_path + re.sub("/", "", str(cat))
    if not os.path.exists(cat_out):
        os.makedirs(cat_out)
    cat_out = cat_out + "/"
    cat_code = cat_lookup[cat_lookup["category"] == str(cat)]["cat_code"].values[0]
    sales_files, multi_sales = utl.get_sales_files(sales_path, cat_code)
    #print("Preprocessing: step 1")
    if not os.path.exists(cat_out + 'metadata_red.csv'):
        print("Empty metadata for ", cat)
        return
    ## 1.1
    pdv_anag = process_anagrafica_pdv(file=anag_file, optimize_flag=True)
    #print("pdv_anag shape: ", pdv_anag.shape)
    ## 1.2
    clusters_anag = process_anagrafica_clusters(clus_file, optimize_flag=True)
    #print("clusters_anag shape: ", clusters_anag.shape)  # 8671925
    ## 1.3
    sku_meta = process_metadata(cat_out + 'metadata_red.csv', [cat], optimize_flag=True, rename=False)
    #print("sku_meta shape: ", sku_meta.shape)  # 996,132
    #print("Preprocessing: step 2")
    # 2.1 - start saving stuff
    sku_meta['Articolo Radice_COD'] = pd.to_numeric(sku_meta['Articolo Radice_COD'], errors='coerce').fillna(0).astype(int).astype(str)
    hlpr_meta = create_metadata_helper(pdv_anag, clusters_anag, sku_meta, optimize_flag=True)
    print ('scrivo sku_pdv_meta...', hlpr_meta.shape)
    hlpr_meta.to_csv(cat_out + 'sku_pdv_meta.csv', index=False, sep=";", decimal=",")
    # hlpr_meta.to_excel(cat_out+'CATMAN_OUTPUT_' + '_' + str(cat_code).zfill(3) + ".xlsx", index=False, sheet_name='sku_pdv_meta')
    del pdv_anag
    del clusters_anag
    # 2.3.1
    # WARNING - this aggregation may take a few minutes to run
    sku_meta_by_LOD = sku_meta.groupby([
        'EAN', 'Articolo Radice', 'Articolo Radice_COD',
        'Prodotto', 'Cluster', 'Regione', sku_status
    ],
        as_index=False,
        dropna=False
    ).agg({
        category_iri: "min",
        category_meta: "min",
        'Settore': "min",
        'Settore merceologico': "min",
        group_key: "min",
        'Marca': "min",
        'Fornitore': "min",
        sku_score: "max",
        'CNO_AC_Vendite in Valore': "sum",
        'CNO_AC_Vendite in Volume': "sum",
        'MKT_AC_Vendite in Valore': "sum",
        'MKT_AC_Vendite in Volume': "sum",
        'Sellout Importo': "sum",
        'Sellout Quantita': "sum",
        'Margine Costo Netto': "sum",
        'Margine Venduto': "sum",
        'CNO_Margine': "sum",
    })
    # aa=sku_meta_by_LOD[(sku_meta_by_LOD["Articolo Radice_COD"]==4968080) & (sku_meta_by_LOD["Regione"]== "Sardegna")]
    # aa[["Cluster", sku_score]]
    print('scrivo sku_clus_reg_meta...', sku_meta_by_LOD.shape)
    sku_meta_by_LOD.to_csv(cat_out + 'sku_clus_reg_meta.csv', index=False, sep=";", decimal=",")
    # sku_meta_by_LOD.to_excel(cat_out + 'CATMAN_OUTPUT_' + '_' + str(cat_code).zfill(3) + ".xlsx", index=False, sheet_name='sku_clus_reg_meta')
    # 2.3.2
    totals_by_sku = get_totals_by_LOD(
        sku_meta,
        ['Settore', 'Categoria',
         'Articolo Radice_COD', 'Regione', 'Cluster',
         group_key, sku_status]
    )
    print('scrivo cno_sales_by_sku_reg_clus...', totals_by_sku.shape)
    totals_by_sku.to_csv(cat_out + 'cno_sales_by_sku_reg_clus.csv', index=False, sep=";", decimal=",")
    # totals_by_sku.to_excel(cat_out+'CATMAN_OUTPUT_' + '_' + str(cat_code).zfill(3) + ".xlsx", index=False, sheet_name='cno_sales_by_sku_reg_clus')
#    print("Preprocessing: step 3")
    # 3.1
    # By category, by region
    mk_vs_cno_by_cat_reg = get_mkt_vs_cno(sku_meta, grouping_cols=['Regione', 'Categoria'])
    # By category, by region, by group key (tipo-varietà)
    mk_vs_cno_by_cat_reg_grpkey = get_mkt_vs_cno(
        sku_meta.loc[~(
            sku_meta['Margine Venduto'].isna()) & ~(
            sku_meta['Margine Costo Netto'].isna())],
        grouping_cols=['Regione', 'Categoria', group_key])
    # save the actual file we need for listing

    print('scrivo cno_vs_market_sales_by_cat_reg...', mk_vs_cno_by_cat_reg.shape)
    mk_vs_cno_by_cat_reg.to_csv(cat_out + 'cno_vs_market_sales_by_cat_reg.csv', index=False, sep=";", decimal=",")

    print('scrivo cno_vs_market_sales_by_cat_reg_grpkey...', mk_vs_cno_by_cat_reg_grpkey.shape)
    mk_vs_cno_by_cat_reg_grpkey.to_csv(cat_out + 'cno_vs_market_sales_by_cat_reg_grpkey.csv', index=False, sep=";",
                                       decimal=",")

    # mk_vs_cno_by_cat_reg.to_excel(cat_out+'CATMAN_OUTPUT_' + '_' + str(cat_code).zfill(3) + ".xlsx", index=False, sheet_name='cno_vs_market_sales_by_cat_reg')
    # mk_vs_cno_by_cat_reg_grpkey.to_excel(cat_out+'CATMAN_OUTPUT_' + '_' + str(cat_code).zfill(3) + ".xlsx", index=False, sheet_name='cno_vs_market_sales_by_cat_reg_grpkey')# ### 3.2 CNO Sales by category-cluster-region
    sku_clus_reg_sales = get_cno_sales_agg(
        df_meta=sku_meta,
        sorted_clusters_map=cluster2rank_map,
        grouping_cols=['Categoria', 'Regione', 'Cluster']
    )
    #print("sku_clus_reg_sales shape: ", sku_clus_reg_sales.shape)  # 588

    print('scrivo cno_sales_by_category_cluster_region...', sku_clus_reg_sales.shape)
    sku_clus_reg_sales.to_csv(cat_out + 'cno_sales_by_category_cluster_region.csv', index=False, sep=";", decimal=",")
    # sku_clus_reg_sales.to_excel(cat_out+'CATMAN_OUTPUT_' + '_' + str(cat_code).zfill(3) + ".xlsx", index=False, sheet_name='cno_sales_by_category_cluster_region')
    del sku_meta
    del sku_meta_by_LOD
    del totals_by_sku
    del mk_vs_cno_by_cat_reg
    del mk_vs_cno_by_cat_reg_grpkey
    del sku_clus_reg_sales
    gc.collect()
    ## 1.4
    sku_buy = []
    for ff in sales_files:
        print("loading " + ff)
        tx_data = load_sales(ff, optimize_flag=False)
        print(tx_data.shape)
        tx_bound = 30000000
        if tx_data.shape[0] > tx_bound:
            grp_bckt_size = 15
            tx_data["cust_grp"] = tx_data.groupby([sku_id]).ngroup() // grp_bckt_size
            n_bckt = tx_data["cust_grp"].max() + 1
            print(f"steps: {n_bckt}")
            for this_grp in range(n_bckt):
                print(this_grp + 1, "/", n_bckt)
                tx_red = tx_data[tx_data.cust_grp == this_grp]
                tx_red = clean_sales(tx_red)
                tx_red = create_sales_plus_meta(tx_red, hlpr_meta)
                if tx_red.shape[0]:
                    tx_by_sku = volumes_agg_by_sku(
                        tx_red,
                        grouping_cols=[sku_id]
                    )
                    #print(tx_by_sku.shape)
                    sku_buy.append(tx_by_sku)
            del tx_red
        else:
            tx_data = clean_sales(tx_data)
            tx_data = create_sales_plus_meta(tx_data, hlpr_meta)
            if tx_data.shape[0]:
                tx_by_sku = volumes_agg_by_sku(
                    tx_data,
                    grouping_cols=[sku_id]
                )
                print(tx_by_sku.shape)  # 1400
                sku_buy.append(tx_by_sku)
        del tx_data
    # 2.2
    del hlpr_meta
    if len(sku_buy) == 0:
        empty_cat.append(cat)
        return
    else:
        sku_buy = pd.concat(sku_buy)
#        print("sku_buy shape", sku_buy.shape)
        # Volumes by SKU
        print('scrivo sales_per_sku...', sku_buy.shape)
        sku_buy.to_csv(cat_out + 'sales_per_sku.csv', index=False, sep=";", decimal=",")
        # sku_buy.to_excel(cat_out + 'CATMAN_OUTPUT_' + '_' + str(cat_code).zfill(3) + ".xlsx", index=False, sheet_name='sales_per_sku')
    del sku_buy


def process_single_category(category: str):
    """
    Funzione che contiene tutta la logica di elaborazione
    per una SOLA categoria.
    """
    #print(f"Eseguo il prefiltering per la categoria: '{category}'...")

    elaborazione(current_category)


    #print(f"Prefiltering per '{category}' completato.")


if __name__ == "__main__":
    # Il programma ora si aspetta un argomento dalla riga di comando.
    # sys.argv è una lista che contiene gli argomenti:
    # sys.argv[0] è il nome dello script ("prefiltering.py")
    # sys.argv[1] è il primo argomento (la nostra categoria)

    if len(sys.argv) < 2:
        print("ERRORE: Nessuna categoria fornita.")
        print("Uso: python prefiltering.py <nome_categoria>")
        sys.exit(1)  # Esce con un codice di errore

    # Prende la categoria dal primo argomento passato
    current_category = sys.argv[1]

    # Lancia l'elaborazione solo per quella categoria
    process_single_category(current_category)

    # Quando lo script termina, il processo viene distrutto e la memoria liberata.
    sys.exit(0)  # Esce indicando successo                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             