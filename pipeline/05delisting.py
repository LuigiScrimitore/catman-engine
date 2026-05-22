# ## Delisting of existing SKUs
import sys

import numpy as np
import pandas as pd
import re
import yaml
import os
import time
import utils as utl

config = utl.get_Config()
input_path = config['paths']['input_path']
sales_path = config['paths']['sales_path']
workarea_path = config['paths']['workarea_path']

lookup_file = input_path + config['files']['lookup_cats']

# log_file = config['files'].get('logging_file')
# if log_file is None:
#     log_file = "log_Modulo3.txt"

# misc options
max_sku_score = config['parameters']['delist_max_score']
max_subs_to_keep = config['parameters']['delist_max_cannib']
write_out = True   ## change only when you know what you're doing!

# run_cfg = config['files']['cat_config']
# 
# with open(run_cfg, "r") as f:
#     cat_config = yaml.safe_load(f)
# 
# categories_to_keep = cat_config['cat_to_run']

# Define column names
lista_colonne = utl.get_Config_Colonne()
group_key = lista_colonne['group_key']
category = lista_colonne['category']
category_meta = lista_colonne['category_meta']
category_iri = lista_colonne['category_iri']
segment = lista_colonne['segment']
sku_id = lista_colonne['sku_id']
sku_desc = lista_colonne['sku_desc']
sku_status = lista_colonne['sku_status']
cust_id = lista_colonne['cust_id']
pdv_id = lista_colonne['pdv_id']
tx_id = lista_colonne['tx_id']
tx_date = lista_colonne['tx_date']
amount = lista_colonne['amount']
qty = lista_colonne['qty']
#fidelity = lista_colonne['fidelity']
#promo = lista_colonne['promo']
pop_cluster = lista_colonne['pop_cluster']
sku_group = lista_colonne['sku_group']
sku_id_focus = lista_colonne['sku_id_focus']
sku_id_sub = lista_colonne['sku_id_sub']
sku_desc_focus = lista_colonne['sku_desc_focus']
sku_desc_sub = lista_colonne['sku_desc_sub']
sku_sold_focus = lista_colonne['sku_sold_focus']
sku_sold_sub = lista_colonne['sku_sold_sub']
sku_gkey_focus = lista_colonne['sku_gkey_focus']
sku_gkey_sub = lista_colonne['sku_gkey_sub']
sku_loyalty = lista_colonne['loyalty']
sku_score = lista_colonne['sku_score']


# column names
#supplier = 'FORNITORE_PRINCIPALE_DESC'
#region = lista_colonne['region']
#margin_sold = 'Margine Venduto'
#margin_cost = 'Margine Costo Netto'

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


def smart_load_to_pd(fname, sep, decimal, encoding):
    _, file_ext = os.path.splitext(fname)
    if file_ext == "zip":
        return pd.read_csv(fname, compression='zip', sep=sep, decimal=decimal, encoding=encoding)
    else:
        return pd.read_csv(fname, sep=sep, decimal=decimal, encoding=encoding)


# Granularity for sku score, delsiting calculations and dashboard
LOD_cols = [sku_id, 'Regione', pop_cluster]
suffix ='_by_LOD'

def get_substitute_transfer_rates(clusters, max_subs_to_keep):
    # Compute substitutes for each sku
    clusters = clusters.loc[(
        clusters[group_key+' IRI (Focus)'] == clusters[group_key+' IRI (Substitute)'])
        ].rename(
            columns = {group_key+' IRI (Focus)': group_key}
        )
    #
    ### FIXMEEEE
    if np.any(clusters['substitution']>0):
        top_n_subs_by_sku = clusters[
                clusters['substitution']>0
            ]
    else:
        top_n_subs_by_sku = clusters
    #
    #top_n_subs_by_sku[sku_sold_sub] = top_n_subs_by_sku[sku_sold_sub].astype(np.float64)
    if top_n_subs_by_sku.shape[0] == 0:
        top_n_subs_by_sku['avg_substitution_scaled'] = top_n_subs_by_sku['substitution_scaled']
        top_n_subs_by_sku['adjusted_substitution_score'] = top_n_subs_by_sku['substitution_scaled']
    else:
        top_n_subs_by_sku = top_n_subs_by_sku.groupby(
                sku_id_focus
            ).apply(
                lambda x: x.sort_values(
                    by=['substitution_scaled'],
                    ascending=False
                ).reset_index()[
                    [sku_desc_focus, sku_id_sub, sku_desc_sub,
                     sku_sold_sub, group_key,
                     'substitution_scaled', sku_group]
            ],
            #].head(max_subs_to_keep)
            include_groups = False
        ).reset_index(
            level=[0]
        )
        # compute avg substitute score for each SKU
        top_n_subs_by_sku['avg_substitution_scaled'] = top_n_subs_by_sku.groupby(
                sku_id_focus
            )['substitution_scaled'].transform('mean')
        top_n_subs_by_sku['substitute_adjustment_factor'] = top_n_subs_by_sku[sku_sold_sub] / \
            (top_n_subs_by_sku.groupby(
                sku_id_focus
                )[sku_sold_sub].transform('sum')
            )
        top_n_subs_by_sku['adjusted_substitution_score'] = top_n_subs_by_sku['substitution_scaled'] *\
            top_n_subs_by_sku['substitute_adjustment_factor']
    #
    return top_n_subs_by_sku[
        [sku_id_focus, sku_id_sub, group_key, 'Gruppo',
         'adjusted_substitution_score', 'avg_substitution_scaled']
        ]

def get_at_risk_columns(data_by_sku_pdv, cols_suffix):
    data_by_sku_pdv = data_by_sku_pdv.rename(columns={
        'avg_substitution_scaled': 'substitution_rate',
        'loyalty': 'loyal_rate'
        })
    data_by_sku_pdv['lost_rate'] = data_by_sku_pdv.apply(
        lambda row: row['loyal_rate']*(1-row['substitution_rate'])
            if row['substitution_rate']>0
            else 1,
        axis=1
        )
    data_by_sku_pdv['transferable_rate'] = (1-data_by_sku_pdv['lost_rate'])
    #
    for suffix in cols_suffix:
        data_by_sku_pdv[f'transferred_{suffix}'] = data_by_sku_pdv[f'total_sellout_{suffix}'] * \
            data_by_sku_pdv['transferable_rate']
        data_by_sku_pdv[f'lost_{suffix}'] = data_by_sku_pdv[f'total_sellout_{suffix}'] * \
            data_by_sku_pdv['lost_rate']
    return data_by_sku_pdv


def get_sku_score(df, score_map, sku_id_colname, join_cols, suffix):
    df = df.rename(
        columns={sku_id_colname: sku_id}
        ).merge(
            score_map,
            on=join_cols,
            how='left'
        ).rename(
            columns={
                sku_id: sku_id_colname,
                sku_score: sku_score+suffix
            }
        )
    # fill missing values with max available score for the given sku
    df[sku_score+suffix] = df[sku_score+suffix].fillna(
        df.groupby(
            sku_id_colname
            )[sku_score+suffix].transform("max")
        )
    return df


def get_transferred_margin_by_sub(row):
    if row['total_sellout_revenues_sub'] < 0.5:
        margin_sold_incidence_sub = 0
        margin_cost_incidence_sub = 0
    else:
        margin_sold_incidence_sub = row['total_margin_sold_sub'] / row['total_sellout_revenues_sub']
        margin_cost_incidence_sub = row['total_margin_cost_sub'] / row['total_sellout_revenues_sub']
    #
    transferred_margin_sold = row['transferred_revenues'] * margin_sold_incidence_sub
    transferred_margin_cost = row['transferred_revenues'] * margin_cost_incidence_sub
    #
    transferred_margin = transferred_margin_sold - transferred_margin_cost
    return transferred_margin_sold, transferred_margin_cost, transferred_margin

def run_checks_totals_by_lod(df, round_dig=3):
    for suffix in ['revenues', 'volume']:
        assert sum(round(
            df[f'total_sellout_{suffix}'] - (
              df[f'transferred_{suffix}'] + \
              df[f'lost_{suffix}']
            ), round_dig)) == 0
    assert sum(round(
        (df['lost_rate'] + df['transferable_rate']), round_dig
        ) != 1) == 0


def run_checks_vols_by_sub(df1, df2, cols_suffix):
    for suffix in cols_suffix:

        # 1. Calcola le tre serie di dati separatamente
        s1 = df1.groupby([sku_id, 'Regione', 'Cluster'])[f'total_sellout_{suffix}'].min()
        s2 = df2.groupby([sku_id_focus, 'Regione', 'Cluster'])[f'total_sellout_{suffix}'].min()
        s3 = df2.groupby([sku_id_sub, 'Regione', 'Cluster'])[f'total_sellout_{suffix}_sub'].min()

        # 2. Standardizza i nomi dell'indice per un allineamento corretto
        # Assumiamo che il nome standard per l'SKU debba essere 'sku_id'
        s2.index = s2.index.rename([sku_id, 'Regione', 'Cluster'])
        s3.index = s3.index.rename([sku_id, 'Regione', 'Cluster'])

        # 3. Concatena i dati, ora con indici allineati correttamente
        combined_df = pd.concat([s1, s2, s3], axis=1).dropna()

        # 4. Applica la logica di controllo usando .iloc
        non_matching_rows = combined_df.apply(
            lambda row: not (row.iloc[0] == row.iloc[1] == row.iloc[2]),
            axis=1
        )

        # 5. Esegui l'assertion
        assert sum(non_matching_rows) == 0, "Trovate righe con valori di sellout minimo non corrispondenti!"



        assert sum(pd.concat([
            df1.groupby([sku_id, 'Regione', 'Cluster'])[f'lost_{suffix}'].min(),
            df2.groupby([sku_id_focus, 'Regione', 'Cluster'])[f'lost_{suffix}'].min(),
            ], axis=1
            ).dropna(
            ).diff(axis=1).iloc[:, 1]
            ) == 0


# def run_checks_totals_by_lod_cumul(df, cols2cumulate):
#     for c in ['lost_revenues', 'lost_volume']:
#         assert 0 == sum(
#             df.groupby([sku_id, 'Regione']).agg({
#                 f'{c}': sum,
#                 f'{c}_cumul': max
#             }).diff(axis=1
#             ).iloc[:, 1].round(5)!=0)

# def check_quality(suffix1, suffix2, grp_cols1, grp_cols2, sku_id2=sku_id_focus):
#     assert 0 == sum(pd.concat([
#         volumes_total_by_LOD.groupby(
#                     grp_cols1
#                     )[f'total_{suffix1}'].sum(
#             ),
#         volumes_by_sub[
#             [sku_id2, 'Regione', 'Cluster', f'total_{suffix2}']
#             ].drop_duplicates(
#             ).groupby(grp_cols2
#             )[f'total_{suffix2}'].sum()
#         ], axis=1,
#         join='inner'
#         ).diff(axis=1).iloc[:,1].round(5)!=0)


cat_lookup = smart_load_to_pd(fname=lookup_file, sep=",", decimal= ".", encoding="latin-1")
cat_lookup = cat_lookup[cat_lookup["sales_2y"] > 0]
cat_lookup = cat_lookup.sort_values(by="sales_2y")
#cat_lookup["category"] = cat_lookup.category.replace("(_)+", "_", regex=True)

nometa_cat = []
noclus_cat = []
nosales_cat = []
nogrp_cat = []
noloy_cat = []
review_cat = []

def process_single_category(cat: str):

    # print("====================")
    # print("SCRIPT 5 - delisting")
    # print("====================")

    start_delist = time.time()
    print("Running delisting for category: " + str(cat))
    cat_out = workarea_path + re.sub("/", "", str(cat))
    hlp_out = workarea_path + re.sub("/", "", str(cat)) + "/"
    supp_out = workarea_path + re.sub("/", "", str(cat)) + "/"
    if not os.path.exists(cat_out):
        os.makedirs(cat_out)
    cat_out = cat_out + "/"
    cat_code = cat_lookup[cat_lookup["category"] == str(cat)]["cat_code"].values[0]
    cat_delist = cat_out + 'delisting' + '_' + str(cat_code).zfill(3) +'.xlsx'
    # # 1. Import data
    # Import sku metadata
    sku_filter = supp_out + config['files']['sku_filter']
    if not os.path.exists(sku_filter):
        nometa_cat.append(cat)
        return
    hlpr_meta = pd.read_csv(sku_filter, sep=";", decimal= ",")
    hlpr_meta = hlpr_meta.astype({sku_id: float}).rename(columns={ category_meta: category })
    hlpr_meta = hlpr_meta.loc[
        hlpr_meta[pop_cluster].isin(cluster2rank_map.keys())
        ]
    #hlpr_meta = hlpr_meta[hlpr_cols2use].drop_duplicates()
    #print(hlpr_meta.shape)
    # Create mapping of priorità assortimento by the desired level of detail
    # Keep the higher score for each group
    score_map_LOD = hlpr_meta.groupby(
        LOD_cols, as_index=False
        )[sku_score].max()
    ######
    cat_group = hlp_out + 'grouping' + '_' + str(cat_code).zfill(3) + ".csv"
    if not os.path.exists(cat_group):
        nogrp_cat.append(cat)
        return
    cat_loyal = hlp_out + 'loyalty' + '_' + str(cat_code).zfill(3) +'.csv'
    if not os.path.exists(cat_loyal):
        noloy_cat.append(cat)
        return
    cat_sales_grpd = supp_out + 'cno_sales_by_sku_reg_clus.csv'
    if not os.path.exists(cat_sales_grpd):
        nosales_cat.append(cat)
        return
    print("delisting: step 1 - import")
    ## Import hierarchical clustering results
    df_groups = pd.read_csv(cat_group, sep=';', decimal=',', encoding='latin-1')
    df_groups = df_groups.astype({
        sku_id_focus: float, 
        sku_id_sub: float,
        sku_sold_focus: float, 
        sku_sold_sub: float,
    })
    # Rescale substitution on a scale 0-1 (current range 0-2)
    df_groups['substitution_scaled'] = df_groups['substitution']/2
    # Import similarity, clustering, loyalty results
    df_loyalty = pd.read_csv(cat_loyal, sep=';', decimal=',', encoding='latin-1')
    df_loyalty = df_loyalty.astype({sku_id: float})
    df_loyalty = df_loyalty.drop_duplicates()
    df_loyalty = df_loyalty.groupby([sku_group, sku_id, sku_desc]).mean().reset_index()
    # Mapping SKU-Gruppo
    sku_group_map = pd.concat([
            df_groups[[sku_id_focus, sku_group]].rename(columns={sku_id_focus: sku_id}),
            df_groups[[sku_id_sub, sku_group]].rename(columns={sku_id_sub: sku_id})
        ]).drop_duplicates()
    ## Import total margin and sales data at SKU, region, cluster, level
    sales_by_sku_reg_clus = pd.read_csv(cat_sales_grpd, sep=";", decimal= ",")
    sales_by_sku_reg_clus = sales_by_sku_reg_clus.rename(
        columns={'Articolo Radice_COD': sku_id}
        )
    sales_by_sku_reg_clus = sales_by_sku_reg_clus.drop(
        columns = ['avg_monthly_margin_cost', 'avg_monthly_margin_sold']
        )
    sales_by_sku_reg_clus['Clus_Help'] = sales_by_sku_reg_clus['Cluster'].map(cluster2rank_map)
    #print(sales_by_sku_reg_clus.shape)
    ### REALLY NEEDED??
    sku_flt = hlpr_meta[
        hlpr_meta[sku_id].isin(
            sku_group_map[sku_id].unique()
        )]
    #print(sku_flt.shape) #15,598
    if sku_flt.shape[0] == 0:
        noclus_cat.append(cat)
        return
    ######
    # # 2. Calculate impact of delisting
    #
    print("delisting: step 2 - compute total volumes")
    # ## 2.1 Volumes for LOD (SKU, region, cluster)
    # Add metadata and Gruppo to SKU totals for the relevant category
    volumes_total_by_LOD = sales_by_sku_reg_clus.merge(
            sku_flt[[sku_id, 'Settore', category_iri, group_key, 'Regione', 'Cluster']
                ].drop_duplicates(
                ).rename(columns={category_iri: 'Categoria IRI'}),
                on = [sku_id, 'Settore', 'Categoria IRI', group_key, 'Regione', 'Cluster']
            ).merge(
                sku_group_map,
                on=[sku_id],
                how='inner'
            )
    #print(volumes_total_by_LOD.shape)
    #print(volumes_total_by_LOD[sku_id].nunique())
    # Calculation of transfer rates for each of the substitutes of the SKU focus
    # note: df_clusters already considers only substitutes within the same group (column "cluster")
    top_subs_rates_by_focus = get_substitute_transfer_rates(df_groups,max_subs_to_keep)
    #print(top_subs_rates_by_focus.shape) #346
    # Add avg substitution score and loyalty score by SKU
    # note: SKUs with a null loyalty score are lost
    volumes_total_by_LOD = volumes_total_by_LOD.merge(
            top_subs_rates_by_focus[[sku_id_focus, 'avg_substitution_scaled']
            ].drop_duplicates(
            ).rename(
                columns={sku_id_focus: sku_id}
            ),
            on = sku_id,
            how = 'left'
        ).fillna(0
        ).merge(
            df_loyalty[[sku_id, 'loyalty']],
            on=[sku_id]
        )
    #print(volumes_total_by_LOD.shape)
    #print(volumes_total_by_LOD[sku_id].nunique())
    # Identify SKUs candidate for delisting that have no substitutes
    # in a particular region and in a particular cluster;
    # then assign all sales of that SKU in that region in that cluster to lost sales
    # (transferred sales = 0)
    LOD_in_substitutes_sheet = top_subs_rates_by_focus.merge(
            volumes_total_by_LOD.loc[:, LOD_cols
            ].rename(
                columns={sku_id: sku_id_focus}
            ), on=[sku_id_focus]
        ).merge(
            volumes_total_by_LOD.loc[:, LOD_cols
            ].rename(columns={sku_id: sku_id_sub}
            ).drop_duplicates(),
            on=[sku_id_sub, 'Regione', 'Cluster']
        )[[sku_id_focus, 'Regione', 'Cluster']
         ].drop_duplicates()
    #
    volumes_total_by_LOD = volumes_total_by_LOD.merge(
        LOD_in_substitutes_sheet,
        left_on = [sku_id, 'Regione', 'Cluster'],
        right_on = [sku_id_focus, 'Regione', 'Cluster'],
        how = 'left'
    )
    #
    volumes_total_by_LOD['avg_substitution_scaled'] = volumes_total_by_LOD.apply(
        lambda row: 0 if pd.isnull(row[sku_id_focus]) else row['avg_substitution_scaled'],
        axis = 1
    )
    #print(volumes_total_by_LOD.shape)
    #print(volumes_total_by_LOD[sku_id].nunique())
    print("delisting: step 3 - compute volumes at risk")
    # Estimate sales transferable vs at risk
    # Identify @risk threshold and total @risk volumes vs total transferable volumes
    # note: granularity: SKU and cluster
    volumes_total_by_LOD = get_at_risk_columns(volumes_total_by_LOD, ['revenues', 'volume'])
    volumes_total_by_LOD = volumes_total_by_LOD.sort_values(
        by = [sku_group, sku_id, 'Clus_Help'],
        ascending = [True, True, False]
        )
    #print(volumes_total_by_LOD.shape) #823
    run_checks_totals_by_lod(volumes_total_by_LOD)
    # ## 2.2 Volumes by SKU focus, SKU substitutes, region and cluster
    # - Transferred sales refer to the sales that can be transferred for each SKU focus, in each region, in each cluster
    # - substitute_transfer_rate sums up to 1 or each SKU focus, region and cluster
    cols_suffix = ['revenues', 'volume', 'margin_cost', 'margin_sold']
    print("delisting: step 4 - compute transferrable volumes")
    # Identify total @risk volumes vs total transferable volumes for top X substitutes
    # note: granularity: SKU focus and SKU substitute
    volumes_by_sub = top_subs_rates_by_focus.merge(
            volumes_total_by_LOD.loc[:,
                LOD_cols + ['Clus_Help'] + \
                [c for c in volumes_total_by_LOD.columns for suf in cols_suffix if suf in c]
            ].rename(
                columns={sku_id: sku_id_focus}
            ).drop_duplicates(), on=[sku_id_focus]
        ).merge(
            volumes_total_by_LOD.loc[:,
                LOD_cols + [
                'total_sellout_revenues', 'total_sellout_volume',
                'total_margin_cost', 'total_margin_sold'
                ]
            ].rename(
                columns={
                    sku_id: sku_id_sub,
                    'total_sellout_revenues': 'total_sellout_revenues_sub',
                    'total_sellout_volume': 'total_sellout_volume_sub',
                    'total_margin_cost': 'total_margin_cost_sub',
                    'total_margin_sold': 'total_margin_sold_sub'
                }
            ).drop_duplicates(),
            on=[sku_id_sub, 'Regione', 'Cluster']
        )
    volumes_by_sub = volumes_by_sub.sort_values(
            by=[sku_id_focus, 'Clus_Help'],
            ascending=[True, False]
        )
    if volumes_by_sub.shape[0] == 0:
        review_cat.append(cat)
        return
    #print(volumes_by_sub.shape) #4660
    #print(volumes_by_sub[[sku_id_focus, 'Regione', 'Cluster']].drop_duplicates().shape)
    # Extract top 10 similar products per sku focus and region
    subs2keep_top10 = volumes_by_sub[
        [sku_id_focus, 'Regione', sku_id_sub, 'adjusted_substitution_score']
    ].drop_duplicates().groupby([sku_id_focus, 'Regione']
        ).apply(
            lambda x: x.sort_values(
                by = ['adjusted_substitution_score'],
                ascending = False
            ).head(max_subs_to_keep),
            # CEGIL: Add this line to fix the warning
            include_groups=False
        ).reset_index().drop(columns=['adjusted_substitution_score'])

    volumes_by_sub = volumes_by_sub.merge(
        subs2keep_top10,
        on = [sku_id_focus, 'Regione', sku_id_sub]
        )
    #print(volumes_by_sub.shape)
    # ### 2.2.1 Proportion of transferred sales to each substitute for each SKU focus
    volumes_by_sub['substitute_transfer_rate'] = volumes_by_sub['adjusted_substitution_score'] / (
        volumes_by_sub.groupby(
            [sku_id_focus, 'Regione', 'Cluster']
            )['adjusted_substitution_score'].transform('sum'))
    volumes_by_sub = volumes_by_sub.drop(columns=['avg_substitution_scaled', 'adjusted_substitution_score'])
    ### FIXMEEE fails for 'ACCESSORI_VARI_PULIZIA_CASA'
    #assert 0 == sum(
    #    volumes_by_sub.groupby(
    #        [sku_id_focus, 'Regione', 'Cluster']
    #    )['substitute_transfer_rate'].sum().round(2) != 1
    #    )
    # Calculate the portion of transferred sales for each SKU sub, region, cluster,
    # using the total transfered sales of the delisted SKU in that region and cluster
    for suffix in ['revenues', 'volume']:
        volumes_by_sub[f'transferred_{suffix}'] = volumes_by_sub[f'transferred_{suffix}'] * \
            volumes_by_sub['substitute_transfer_rate']
    # checks
    run_checks_vols_by_sub(volumes_total_by_LOD, volumes_by_sub, ['revenues', 'volume'])
    #
    tmp = volumes_total_by_LOD.groupby(
            LOD_cols, as_index=False
            )[['transferred_revenues', 'transferred_volume']].min(
        ).merge(
        volumes_by_sub.groupby(
            [sku_id_focus, 'Regione', 'Cluster'], as_index=False
            )[['transferred_revenues', 'transferred_volume']].sum(),
        left_on=LOD_cols,
        right_on=[sku_id_focus, 'Regione', 'Cluster']
        )
    ### FIXMEEEE: fails for transferred_revenues_x in 'UOVA_FRESCHE'
    #for c in tmp.columns:
    #    if 'transferred_' and '_x' in c:
    #        assert 0 == sum(round(tmp[c] - tmp[c[:-1]+'y'])!=0)
    print("delisting: step 5 - add sales and priority")
    # ### 2.2.3 Add sales of substitutes by region
    # Add sales from metadata at sku and region level (only valid clusters)
    sales_by_sku_region = sales_by_sku_reg_clus.loc[
        sales_by_sku_reg_clus['Cluster'].isin(cluster2rank_map.keys())
        ].rename(
            columns = {'Articolo Radice_COD': sku_id}
        ).groupby(
        [sku_id, 'Regione'],
        as_index = False
        )[[
            'total_sellout_revenues', 'total_sellout_volume',
            'total_margin_cost', 'total_margin_sold']
        ].sum()
    #print(volumes_by_sub.shape) #4660
    volumes_by_sub = volumes_by_sub.merge(
        sales_by_sku_region.rename(
            columns={
                sku_id: sku_id_sub,
                'total_sellout_revenues': 'revenues_by_region_sub',
                'total_sellout_volume': 'volume_by_region_sub',
                'total_margin_cost': 'margin_cost_by_region_sub',
                'total_margin_sold': 'margin_sold_by_region_sub',
            }),
        on = [sku_id_sub, 'Regione']
        )
    #print(volumes_by_sub.shape) #4660
    # ## 3. Filter by priorità assortimento
    ## Add sku score in all files
    # Add focus sku score
    volumes_total_by_LOD = get_sku_score(
        df = volumes_total_by_LOD,
        score_map = score_map_LOD,
        sku_id_colname = sku_id,
        join_cols = LOD_cols,
        suffix = ''
        )
    # Add focus sku score
    volumes_by_sub = get_sku_score(
        df = volumes_by_sub,
        score_map = score_map_LOD,
        sku_id_colname = sku_id_focus,
        join_cols = LOD_cols,
        suffix = ' (Focus)'
        )
    # Add substitute sku score
    volumes_by_sub = get_sku_score(
        df = volumes_by_sub,
        score_map = score_map_LOD,
        sku_id_colname = sku_id_sub,
        join_cols = LOD_cols,
        suffix = ' (Substitute)'
        )
    #print(volumes_total_by_LOD.shape) #823
    #print(volumes_by_sub.shape) #4660
    # Keep only the sku focus that can potentially be delisted
    # i.e. only thos with a score of 1, 2 or 3 and those with an active status
    volumes_total_by_LOD = volumes_total_by_LOD[(
            volumes_total_by_LOD[sku_score] <= max_sku_score
        ) & (
            volumes_total_by_LOD[sku_status] == 'Attivo'
        )]
    volumes_by_sub = volumes_by_sub.loc[(
            volumes_by_sub[sku_score+' (Focus)'] <= max_sku_score
        ) & (
            volumes_by_sub[sku_id_focus].isin(volumes_total_by_LOD[sku_id].unique())
        )]
    #print(volumes_total_by_LOD.shape) #736
    #print(volumes_by_sub.shape) #4237
    # checks
    run_checks_totals_by_lod(volumes_total_by_LOD)
    for suffix in ['revenues', 'volume']:
        assert 0 == sum(pd.concat([
            volumes_total_by_LOD.groupby(
            [sku_id, 'Regione', 'Cluster']
            )[f'total_sellout_{suffix}'].min(),
            volumes_by_sub.loc[(
                volumes_by_sub[sku_score+' (Substitute)']<=3
                )].groupby(
                [sku_id_sub, 'Regione', 'Cluster']
                )[f'total_sellout_{suffix}_sub'].min()
            ], axis=1).diff(axis=1
            ).iloc[:,1].round(5).dropna() !=0)
    print("delisting: step 6 - compute margins")
    # ## 4. Calculate margins
    volumes_by_sub['total_margin_sub'] = volumes_by_sub['total_margin_sold_sub'] - \
        volumes_by_sub['total_margin_cost_sub']
    volumes_by_sub['total_margin_pct_sub'] = volumes_by_sub.apply(
        lambda row: 0 if row['total_margin_sold_sub']==0 else (
            row['total_margin_sub'] / row['total_margin_sold_sub']),
        axis = 1
        )
    # Calculate transferred margin by each delisted SKU to each substitute, by region and cluster
    volumes_by_sub['transferred_margin_sold'] = volumes_by_sub.apply(lambda row: get_transferred_margin_by_sub(row)[0], axis=1)
    volumes_by_sub['transferred_margin_cost'] = volumes_by_sub.apply(lambda row: get_transferred_margin_by_sub(row)[1], axis=1)
    volumes_by_sub['transferred_margin'] = volumes_by_sub.apply(lambda row: get_transferred_margin_by_sub(row)[2], axis=1)
    # Calculate total and lost margin for each delisted SKU at region and cluster level
    volumes_total_by_LOD['total_margin'] = volumes_total_by_LOD['total_margin_sold'] - \
        volumes_total_by_LOD['total_margin_cost']
    volumes_total_by_LOD['total_margin_pct'] = volumes_total_by_LOD['total_margin'] / \
        volumes_total_by_LOD['total_margin_sold']
    # Add total margin transferred to substitutes
    volumes_total_by_LOD = volumes_total_by_LOD.merge(
        volumes_by_sub.rename(
            columns={sku_id_focus: sku_id}
        ).groupby(
            [sku_id, 'Regione', 'Cluster'],
            as_index = False
            )[['transferred_margin', 'transferred_margin_cost', 'transferred_margin_sold']].sum(),
        on = [sku_id, 'Regione', 'Cluster'],
        how='left'
        )
    volumes_total_by_LOD['lost_margin_cost'] = volumes_total_by_LOD['total_margin_cost'] - \
        volumes_total_by_LOD['transferred_margin_cost']
    volumes_total_by_LOD['lost_margin_sold'] = volumes_total_by_LOD['total_margin_sold'] - \
        volumes_total_by_LOD['transferred_margin_sold']
    volumes_total_by_LOD['lost_margin'] = volumes_total_by_LOD['total_margin'] - \
        volumes_total_by_LOD['transferred_margin']
    # ## 5. Compute cumulative columns
    # Cumulate by SKU delisted and Region
    volumes_total_by_LOD = volumes_total_by_LOD.sort_values(
        by = [sku_id, 'Regione', 'Clus_Help'],
        ascending = [True, True, False]
        )
    cols2cumulate = ['lost_revenues', 'lost_volume', 'lost_margin', 'lost_margin_cost', 'lost_margin_sold']
    volumes_total_by_LOD[cols2cumulate] = volumes_total_by_LOD[cols2cumulate].fillna(0)
    volumes_total_by_LOD[[c+'_cumul' for c in cols2cumulate]] = volumes_total_by_LOD.groupby(
        [sku_id, 'Regione']
        )[cols2cumulate].transform('cumsum')
    #print(volumes_total_by_LOD.shape) #736
    # Cumulate for transferred sales by SKU focus, substitutes and region
    cols2cumulate = ['transferred_revenues', 'transferred_volume', 
        'transferred_margin', 'transferred_margin_sold', 'transferred_margin_cost']
    volumes_by_sub[[c+'_cumul' for c in cols2cumulate]] = volumes_by_sub.sort_values(
        by=[sku_id_focus, sku_id_sub, 'Regione', 'Clus_Help'],
        ascending=[True, True, True, False]
        ).groupby(
            [sku_id_focus, sku_id_sub, 'Regione']
        )[cols2cumulate].transform('cumsum')
    # var = volumes_by_sub.shape  #4237
    # checks
    run_checks_totals_by_lod(volumes_total_by_LOD)
    #run_checks_totals_by_lod_cumul(volumes_total_by_LOD, ['lost_revenues', 'lost_volume'])
    # check margin
    for sku2test in volumes_total_by_LOD[sku_id].unique():
        for region2test in volumes_total_by_LOD.loc[volumes_total_by_LOD[sku_id]==sku2test, 'Regione'].unique():
            subset_test = volumes_total_by_LOD.loc[(
                volumes_total_by_LOD[sku_id]==sku2test) & (
                volumes_total_by_LOD['Regione']==region2test)
                ]
            ## FIXMEEEE FAILS FOR CREME_VISO...
            #assert round(subset_test['lost_margin'].sum(), 2) == round(
            #    subset_test.loc[
            #    subset_test['Clus_Help']==subset_test['Clus_Help'].min(),
            #    'lost_margin_cumul'].values[0],
            #    2)
    # ## 6. Quality checks
    ## FIXMEEEE FAILS FOR CREME_VISO...
    #for suffix in ['sellout_revenues', 'sellout_volume', 'margin_cost', 'margin_sold']:
    #    # a) total sales by sku, region, cluster
    #    print(suffix)
    #    check_quality(suffix, suffix, [sku_id, 'Regione', 'Cluster'], [sku_id_focus, 'Regione', 'Cluster'])
    #    print("Step2")
    #    check_quality(suffix, f'{suffix}_sub',
    #        [sku_id, 'Regione', 'Cluster'],
    #        [sku_id_sub, 'Regione', 'Cluster'],
    #        sku_id_sub
    #        )
    #    # b) total transferable + lost volumes by sku
    #    if suffix in ['revenues', 'volume']:
    #        assert (volumes_total_by_LOD[f'transferred_{suffix}'] + volumes_total_by_LOD[f'lost_{suffix}']
    #            ).reset_index(
    #            ).join(
    #            volumes_total_by_LOD[f'total_{suffix}'].reset_index(drop=True)
    #            ).drop(columns='index'
    #            ).diff(axis=1
    #            ).round(4
    #            ).loc[:, f'total_{suffix}'
    #            ].sum() == 0
    print("delisting: step 7 - prepare output")
    # ## 7. Clean output
    # Add tipo and varietà
    volumes_total_by_LOD['Tipo'] = volumes_total_by_LOD[group_key].apply(lambda x: x.split(' / ')[0])
    volumes_total_by_LOD['Varietà'] = volumes_total_by_LOD[group_key].apply(lambda x: x.split(' / ')[1])
    volumes_by_sub['Tipo'] = volumes_by_sub[group_key].apply(lambda x: x.split(' / ')[0])
    volumes_by_sub['Varietà'] = volumes_by_sub[group_key].apply(lambda x: x.split(' / ')[1])
    ## Add meta columns
    volumes_total_by_LOD = volumes_total_by_LOD.merge(
        sku_flt[
            [sku_id, sku_desc, category, 'Marca', 'Fornitore']
        ].drop_duplicates(),
        on = [sku_id],
        how = 'left'
    )
    volumes_by_sub = volumes_by_sub.merge(
        sku_flt[[sku_id, sku_desc, category, category_iri, 'Settore']].drop_duplicates(
        ).rename(columns={
            sku_id: sku_id_focus,
            sku_desc: sku_desc+'_focus',
        }),
        on = [sku_id_focus],
        how = 'left'
    )
    volumes_by_sub = volumes_by_sub.merge(
        sku_flt[[sku_id, sku_desc]].drop_duplicates(
        ).rename(columns={
            sku_id: sku_id_sub,
            sku_desc: sku_desc+'_sub'
        }),
        on = [sku_id_sub],
        how = 'left'
    )
    #print(volumes_total_by_LOD.shape) #736
    #print(volumes_by_sub.shape) #4237
    # Remove columns not needed
    volumes_total_by_LOD = volumes_total_by_LOD.drop(
        columns=[sku_id_focus, sku_status, 'loyal_rate', 'substitution_rate'
            ] #+ [c for c in volumes_total_by_LOD.columns if 'margin_cost' in c or 'margin_sold' in c]
            )
    volumes_by_sub = volumes_by_sub.drop(
        columns=['total_sellout_revenues',
            'total_sellout_volume',
            'lost_revenues',
            'lost_volume'
            ] #+ [c for c in volumes_by_sub.columns if 'margin_cost' in c or 'margin_sold' in c]
            )
    #print(volumes_total_by_LOD.shape) #736
    #print(volumes_by_sub.shape) #4237
    #Rename and reorder columns
    cols2rename_map_1 = {
        'ART_RADICE_COD': 'Articolo Radice COD',
        'Regione': 'Regione',
        'Cluster': 'Cluster',
        'Clus_Help': 'Cluster Rank',
        'Tipo-Varieta': 'Tipo-Varietà',
        'total_sellout_revenues': 'Fatturato annuale',
        'total_sellout_volume': 'Volumi annuali',
        'total_margin_cost': 'Margine costo netto annuale',
        'total_margin_sold': 'Margine venduto annuale',
        'total_margin': 'Margine annuale',
        'total_margin_pct': 'Margine annuale pct',
        'Gruppo': 'Gruppo',
        #'substitution_rate': 'Tasso di sostituibilità',
        #'loyal_rate': 'Fedeltà',
        'lost_rate': 'Proporzione a rischio',
        'transferable_rate': 'Proporzione trasferibile',
        'transferred_revenues': 'Fatturato trasferibile',
        'transferred_volume': 'Volumi trasferibili',
        'transferred_margin_sold': 'Margine venduto trasferibile',
        'transferred_margin_cost': 'Margine costo netto trasferibile',
        'transferred_margin': 'Margine trasferibile',
        'lost_revenues': 'Fatturato a rischio',
        'lost_volume': 'Volumi a rischio',
        'lost_margin_sold': 'Margine venduto a rischio',
        'lost_margin_cost': 'Margine costo netto a rischio',
        'lost_margin': 'Margine a rischio',
        #'total_sellout_revenues_cumul': 'Fatturato annuale (cumulato)',
        #'total_sellout_volume_cumul': 'Volumi annuali (cumulato)',
        #'total_margin_cumul': 'Margine annuale (cumulato)',
        #'total_margin_pct_cumul': 'Margine annuale pct (cumulato)',
        #'transferred_revenues_cumul': 'Fatturato trasferibile (cumulato)',
        #'transferred_volume_cumul': 'Volumi trasferibili (cumulato)',
        #'transferred_margin_cumul': 'Margine trasferibile (cumulato)',
        #'transferred_margin_pct_cumul': 'Margine pct trasferibile (cumulato)',
        'lost_revenues_cumul': 'Fatturato a rischio (cumulato)',
        'lost_volume_cumul': 'Volumi a rischio (cumulato)',
        'lost_margin_sold_cumul': 'Margine venduto a rischio (cumulato)',
        'lost_margin_cost_cumul': 'Margine costo netto a rischio (cumulato)',
        'lost_margin_cumul': 'Margine a rischio (cumulato)',
        #'lost_margin_pct_cumul': 'Margine pct a rischio (cumulato)',
        "PRIORITA' ASSORTIMENTO COMPLESSIVO": 'Priorità assortimento',
        'Tipo': 'Tipo',
        'Varietà': 'Varietà',
        'ART_RADICE_DESC': 'Prodotto',
        'CATEG_MERC_PDV_DESC': 'Categoria CNO',
        'Categoria': 'Categoria IRI',
        'Settore': 'Settore',
        'Marca': 'Marca',
        'Fornitore': 'Fornitore'
        }
    delist1 = volumes_total_by_LOD.rename(columns = cols2rename_map_1)
    delist1 = delist1[cols2rename_map_1.values()]
    print("output 1 shape: ", delist1.shape) #736
    # Rename and reorder columns
    cols2rename_map_2 = {
        'SKU ID (Focus)': 'Articolo Radice COD (Focus)',
        'SKU ID (Substitute)': 'Articolo Radice COD (Sostituto)',
        'Tipo-Varieta': 'Tipo-Varietà',
        'Gruppo': 'Gruppo',
        'Regione': 'Regione',
        'Cluster': 'Cluster',
        'Clus_Help': 'Cluster Rank',
        'transferred_revenues': 'Fatturato trasferibile',
        'transferred_volume': 'Volumi trasferibili',
        'transferred_margin_cost': 'Margine costo netto trasferibile',
        'transferred_margin_sold': 'Margine venduto trasferibile',
        'transferred_margin': 'Margine trasferibile',
        #'transferred_margin_pct': 'Margine pct trasferibile',
        #'lost_rate': 'Proporzione a rischio',
        'total_sellout_revenues_sub': 'Fatturato annuale (Sostituto)',
        'total_sellout_volume_sub': 'Volumi annuali (Sostituto)',
        'total_margin_sold_sub': 'Margine venduto annuale (Sostituto)',
        'total_margin_cost_sub': 'Margine costo netto annuale (Sostituto)',
        'total_margin_sub': 'Margine annuale (Sostituto)',
        'total_margin_pct_sub': 'Margine pct annuale (Sostituto)',
        'substitute_transfer_rate': "Proporzione trasferita al sostituto",
        'transferred_revenues_cumul': 'Fatturato trasferibile (cumulato)',
        'transferred_volume_cumul': 'Volumi trasferibili (cumulato)',
        'transferred_margin_sold_cumul': 'Margine venduto trasferibile (cumulato)',
        'transferred_margin_cost_cumul': 'Margine costo netto trasferibile (cumulato)',
        'transferred_margin_cumul': 'Margine trasferibile (cumulato)',
        #'transferred_margin_pct_cumul': 'Margine pct trasferibile (cumulato)',
        'revenues_by_region_sub': 'Fatturato annuale per regione (Sostituto)',
        'volume_by_region_sub': 'Volumi annuali per regione (Sostituto)',
        #'margin_by_region_sub': 'Margine mensile per regione (Sostituto)',
        #'margin_pct_by_region_sub': 'Margine pct mensile per regione (Sostituto)',
        "PRIORITA' ASSORTIMENTO COMPLESSIVO (Focus)": 'Priorità assortimento (Focus)',
        "PRIORITA' ASSORTIMENTO COMPLESSIVO (Substitute)": 'Priorità assortimento (Sostituto)',
        'Tipo': 'Tipo',
        'Varietà': 'Varietà',
        'CATEG_MERC_PDV_DESC': 'Categoria CNO',
        'Categoria': 'Categoria IRI',
        'Settore': 'Settore',
        'ART_RADICE_DESC_focus': 'Prodotto (Focus)',
        'ART_RADICE_DESC_sub': 'Prodotto (Sostituto)'
        }
    delist2 = volumes_by_sub.rename(columns = cols2rename_map_2)
    delist2 = delist2[cols2rename_map_2.values()]
    print("output 2 shape: ", delist2.shape) #4237
    # Save output for dashboard
    if write_out:
        #with pd.ExcelWriter(cat_delist) as writer:
        #    delist1.to_excel(writer, sheet_name="sku_cluster", index=False)
        #    delist2.to_excel(writer, sheet_name="top_10_delisted", index=False)
        delist1.to_parquet(re.sub(".xlsx$", "_sheet1.parquet", cat_delist), index=False)
        delist2.to_parquet(re.sub(".xlsx$", "_sheet2.parquet", cat_delist), index=False)




if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("ERRORE: Nessuna categoria fornita.")
        print("Uso: python metadata.py <nome_categoria>")
        sys.exit(1)  # Esce con un codice di errore

    current_category = sys.argv[1]

    process_single_category(current_category)

    sys.exit(0)  # Esce indicando successo
