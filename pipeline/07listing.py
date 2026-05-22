# ## Listing of new EANs
import sys
import numpy as np
import pandas as pd
import re
import os
import time
import utils as utl

config = utl.get_Config()
input_path = config['paths']['input_path']
# sales_path = config['paths']['sales_path']
workarea_path = config['paths']['workarea_path']

lookup_file = input_path + config['files']['lookup_cats']

# misc options
min_sku_score = config['parameters']['list_min_score']
max_subs_to_keep = config['parameters']['list_max_cannib']
min_mkt_revenue_by_new_sku_region = config['parameters']['list_min_mkt_rev']
# max proportion of sales that the new SKU can cannibalise from each similar product
transfer_factor = config['parameters']['list_tx_factor']
# max proportion of sales that can be allocated to net new sales (vs cannibalised) for the new SKU
# Note: the formula will use the max value between this threshold and the mean loyalty;
# set the threshold to 0 if you don't want to use it, so that the mean loyalty will be considered
on_top_factor = config['parameters']['list_ot_factor']
# Number of quantiles used in sales to separate similar SKUs for sales cannibalization (default: quintiles)
sales_quants = config['parameters']['list_sales_quants']

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
sku_id_meta = lista_colonne['sku_id_meta']
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
mkt_revenue = lista_colonne['mkt_revenue']
mkt_volume = lista_colonne['mkt_volume']

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



# # 1. Import data

def add_missing_clusters(df, lvl_of_detail_cols, sorted_clusters_map):
    mux_values_all = [
        df[col].unique() if col!='Cluster' else list(sorted_clusters_map.keys())
        for col in lvl_of_detail_cols
        ]
    # create complete multi-index
    mux = pd.MultiIndex.from_product(
        mux_values_all,
        names=lvl_of_detail_cols
    )
    mux = mux.to_frame(index=False)
    # Add meta information at sku-region level for new clusters added
    mux = mux.merge(
        df[['Gruppo', sku_id, sku_desc, 'loyalty', group_key, 'quant', 'Regione']],
        on = [sku_id, 'Regione']
        ).drop_duplicates()
    return mux


# # 2. Calculate impact of listing

def filter_eligible_skus(clus_reg_cno_shares, gkey_reg_cno_sales, eligible_new_sku):
    # identify available data for each region, category and group key for the selected category
    cat_reg_in_cno_check = clus_reg_cno_shares.loc[
        clus_reg_cno_shares['clus_rev_perc_cno_by_cat']>0,
        [category_iri, 'Regione']
        ].drop_duplicates(
        ).apply(
            lambda row: row[category_iri] + '_' + row['Regione'],
            axis = 1
        )
    grp_key_in_region_check = gkey_reg_cno_sales[
        [category_iri, group_key, 'Regione']
        ].drop_duplicates(
        ).apply(
            lambda row: row[category_iri] + '_' + row[group_key] + '_' + row['Regione'],
            axis = 1
        )
    return eligible_new_sku[(
        eligible_new_sku.apply(
            lambda row: row[category_iri] + '_' + row[group_key] + '_' + row['Regione'],
            axis =1
            ).isin(grp_key_in_region_check)) & (
        eligible_new_sku.apply(
            lambda row: row[category_iri] + '_' + row['Regione'],
            axis =1
            ).isin(cat_reg_in_cno_check))
        ]


def assign_group(sim_items, min_num=3):
    if sim_items['Gruppo'].nunique() > 1:
        median_volume_by_sku_focus = sim_items.groupby(
                [sku_group, sku_id_focus]
            ).agg(
                volume_by_sku_focus = ('SKU # Sold (Focus)', "min")
            ).groupby(
                [sku_group]
            ).agg(
                median_volume_by_sku_focus = ('volume_by_sku_focus', 'median')
            )
        by_gruppo = sim_items.groupby(
                [sku_group]
            ).agg(
                skus = (sku_id_focus, 'nunique'),
                avg_substitution = ('substitution', 'mean')
            ).join(median_volume_by_sku_focus
            ).fillna(0) #SKUs of group 999 have null values; fill them with 0
        # keep only groups with at least 3 SKUs
        best_grp_flt1 = by_gruppo['skus']>=min(min_num, by_gruppo['skus'].max())
        # best group based on higher avg sales by sku
        best_grp_flt2 = by_gruppo.loc[best_grp_flt1]['median_volume_by_sku_focus'] == \
            by_gruppo.loc[best_grp_flt1]['median_volume_by_sku_focus'].max()
        assigned_group = by_gruppo.loc[best_grp_flt1 & best_grp_flt2].index[0]
    else:
        assigned_group = sim_items['Gruppo'].values[0]
    #
    return assigned_group



def run_checks(cannibal_bucket, round_dig=4):
    for suffix in ['revenues', 'volume']: #, 'margin_cost', 'margin_sold']:
        assert sum(round(pd.concat([
            cannibal_bucket.groupby(sku_id)[f'total_sellout_{suffix}'].sum(),
            cannibal_bucket.groupby(sku_id)[f'{suffix}_by_region_sub'].min()
            ], axis=1
            ).diff(axis=1
            ).iloc[:, 1], round_dig) != 0) == 0

def run_checks2(clus_new_sales, metric, cols_dict, round_dig=1):
    if metric != 'margin':
        total_metric = cols_dict[metric][0]
        assert round(total_metric, round_dig) == \
            round(clus_new_sales[f'clus_new_{metric}'].sum(), round_dig) == \
            round((clus_new_sales[f'clus_on_top_{metric}'] + \
                   clus_new_sales[f'clus_cannibal_{metric}']).sum(), round_dig)
    else:
        if clus_new_sales[f'clus_new_{metric}'].sum()>0:
            total_metric = cols_dict['margin_sold'][0] - cols_dict['margin_cost'][0]
            assert (total_metric - clus_new_sales[f'clus_new_{metric}'].sum())<1e-1

def get_transferred_margin_by_sub(row, revenue_col):
    if row[revenue_col] < 0.5:
        margin_sold_incidence_sub = 0
        margin_cost_incidence_sub = 0
    else:
        margin_sold_incidence_sub = row['total_margin_sold'] / row[revenue_col]
        margin_cost_incidence_sub = row['total_margin_cost'] / row[revenue_col]
    #
    transferred_margin_sold = row['transferred_revenue'] * margin_sold_incidence_sub
    transferred_margin_cost = row['transferred_revenue'] * margin_cost_incidence_sub
    transferred_margin = transferred_margin_sold - transferred_margin_cost
    return transferred_margin


cat_lookup = smart_load_to_pd(fname=lookup_file, sep=",", decimal= ".", encoding="latin-1")
cat_lookup = cat_lookup[cat_lookup["sales_2y"] > 0]
cat_lookup = cat_lookup.sort_values(by="sales_2y")
#cat_lookup["category"] = cat_lookup.category.replace("(_)+", "_", regex=True)

nosales_cat = []
empty_cat = []
nogrp_cat = []
noloy_cat = []


def process_single_category(cat: str):

    # print("==================")
    # print("SCRIPT 7 - listing")
    # print("==================")

    start_list = time.time()

    print("Running listing for category: " + str(cat))
    cat_out = workarea_path + re.sub("/", "", str(cat))
    hlp_out = workarea_path + re.sub("/", "", str(cat)) + "/"
    supp_out = workarea_path + re.sub("/", "", str(cat)) + "/"
    if not os.path.exists(cat_out):
        os.makedirs(cat_out)
    cat_out = cat_out + "/"
    cat_code = cat_lookup[cat_lookup["category"] == str(cat)]["cat_code"].values[0]
    cat_listing = cat_out + 'listing' + '_' + str(cat_code).zfill(3) +'.xlsx'
    # ## Import data
    ######
    cat_group = hlp_out + 'grouping' + '_' + str(cat_code).zfill(3) + ".csv"
    if not os.path.exists(cat_group):
        nogrp_cat.append(cat)
        return
    cat_loyal = hlp_out + 'loyalty' + '_' + str(cat_code).zfill(3) +'.csv'
    if not os.path.exists(cat_loyal):
        noloy_cat.append(cat)
        return
    cat_sku_sold = supp_out + 'sales_per_sku.csv'
    cat_sku_clus_reg = supp_out + 'sku_clus_reg_meta.csv'
    cat_clus_reg_sales = supp_out + 'cno_sales_by_category_cluster_region.csv'
    cat_sales_sku_reg_clus = supp_out + 'cno_sales_by_sku_reg_clus.csv'
    cat_mk_vs_cno = supp_out + 'cno_vs_market_sales_by_cat_reg.csv'
    cat_mk_vs_cno_grpkey = supp_out + 'cno_vs_market_sales_by_cat_reg_grpkey.csv'
    if not os.path.exists(cat_sku_sold) or not os.path.exists(cat_sku_clus_reg) \
            or not os.path.exists(cat_clus_reg_sales) or not os.path.exists(cat_sales_sku_reg_clus) \
            or not os.path.exists(cat_mk_vs_cno) or not os.path.exists(cat_mk_vs_cno_grpkey):
        nosales_cat.append(cat)
        return
    print("listing: step 1 - import")
    # CNO sales from metadata
    sales_by_sku_reg_clus = pd.read_csv(cat_sales_sku_reg_clus, sep=";", decimal= ",", encoding='latin-1')
    # Add incidence of margin cost and margin sold wrt sales
    sales_by_sku_reg_clus['margin_sold_incidence'] = sales_by_sku_reg_clus.apply(
        lambda row: 0 if row['total_sellout_revenues'] < 0.5 else (row['total_margin_sold'] / row['total_sellout_revenues']),
            axis = 1)
    sales_by_sku_reg_clus['margin_cost_incidence'] = sales_by_sku_reg_clus.apply(
        lambda row: 0 if row['total_sellout_revenues'] < 0.5 else (row['total_margin_cost'] / row['total_sellout_revenues']),
            axis = 1)
    # Identify SKUs with a valid cluster
    valid_skus = sales_by_sku_reg_clus.loc[
        sales_by_sku_reg_clus['Cluster'].isin(cluster2rank_map.keys()),
        'Articolo Radice_COD'].unique()
    #print(len(valid_skus))
    # Results of hierarchical similarity and clustering
    df_groups = pd.read_csv(cat_group, sep=';', decimal=',', encoding='latin-1')
    # df_groups = df_groups.astype({sku_id_focus: str, sku_id_sub: str})
    # df_groups[sku_id_sub] = df_groups[sku_id_sub].astype(float).astype(int).astype(str)
    # df_groups[sku_id_sub]= df_groups[sku_id_sub].astype(float).astype(str).replace('.0', '')
    # df_groups[sku_id_sub]= df_groups[sku_id_sub].astype(float).astype(str).replace(',0', '')
    # df_groups[sku_id_sub]= df_groups[sku_id_sub].str.replace(',0', '', regex=False)
    # df_groups[sku_id_sub]= df_groups[sku_id_sub].str.replace('.0', '', regex=False)

    df_groups = df_groups[df_groups[sku_id_focus].isin(valid_skus)]
    df_groups = df_groups.astype({sku_id_focus: str, sku_id_sub: str})

    # Results of loyalty
    df_loyalty = pd.read_csv(cat_loyal, sep=';', decimal=',', encoding='latin-1')
    df_loyalty = df_loyalty.astype({sku_id: str})
    df_loyalty = df_loyalty.drop_duplicates()
    df_loyalty = df_loyalty.groupby([sku_group, sku_id, sku_desc]).mean().reset_index()
    # Sales from transaction data
    sku_sold = pd.read_csv(cat_sku_sold, sep=";", decimal= ",", encoding='latin-1')
    sku_sold = sku_sold.astype({'sku_id': str})
    # FIXMEEE: Hack to compensate dupes in metadata!!
    #aa=sku_sold[sku_sold["sku_id"]==4990401]
    #aa
    sku_sold = sku_sold.groupby(["sku_id"]).agg({cc:"mean" for cc in sku_sold.columns if cc != "sku_id"}).reset_index()
    # Metadata at SKU, region, cluster level
    sku_clus_reg_meta = pd.read_csv(cat_sku_clus_reg, sep=';', decimal= ",", encoding='latin-1', low_memory=False)
    # FIXMEEE: Hack to compensate error in metadata (duplicated sku_score)!!
    #aa=sku_clus_reg_meta[(sku_clus_reg_meta["Articolo Radice_COD"]==4968080) & (sku_clus_reg_meta["Regione"]== "Sardegna")]
    #aa[["Articolo Radice_COD", "Regione", "Cluster", sku_score, 'Sellout Importo']]
    #aa=sku_clus_reg_meta[(sku_clus_reg_meta["Articolo Radice_COD"]==4968080) & (sku_clus_reg_meta["Regione"]== "Emilia-Romagna")]
    #aa[["Articolo Radice_COD", "Regione", "Cluster", sku_score, 'Sellout Importo']]
    sku_clus_reg_meta[sku_id_meta]= sku_clus_reg_meta[sku_id_meta].fillna(0)

    scr_meta_p1 = sku_clus_reg_meta[sku_clus_reg_meta[sku_id_meta]!=0].copy()
    scr_meta_p1["min_score"] = scr_meta_p1.groupby([category_meta, sku_id_meta, "Regione", "Cluster", sku_status])[sku_score].transform("min")
    scr_meta_p1["cum_count"] = scr_meta_p1.groupby([category_meta, sku_id_meta, "Regione", "Cluster", sku_status]).cumcount()
    scr_meta_p1 = scr_meta_p1[(scr_meta_p1[sku_score] == scr_meta_p1["min_score"]) & (scr_meta_p1["cum_count"] == 0)]
    scr_meta_p1 = scr_meta_p1.drop(["min_score", "cum_count"], axis=1)
    scr_meta_p2 = sku_clus_reg_meta[sku_clus_reg_meta[sku_id_meta]==0].copy()
    scr_meta_p2["min_score"] = scr_meta_p2.groupby(["EAN", "Regione"])[sku_score].transform("min")
    scr_meta_p2["cum_count"] = scr_meta_p2.groupby(["EAN", "Regione"]).cumcount()
    scr_meta_p2 = scr_meta_p2[(scr_meta_p2[sku_score] == scr_meta_p2["min_score"]) & (scr_meta_p2["cum_count"] == 0)]
    scr_meta_p2 = scr_meta_p2.drop(["min_score", "cum_count"], axis=1)
    sku_clus_reg_meta = pd.concat([scr_meta_p1, scr_meta_p2])
    #print(sku_clus_reg_meta.shape) #507,056
    # CNO sales shares by category, region, cluster
    clus_reg_sales = pd.read_csv(cat_clus_reg_sales, sep=';', decimal= ",", encoding='latin-1')
    # Sales from metadata at sku and region level (only valid clusters)
    sales_by_sku_reg = sales_by_sku_reg_clus.loc[
        sales_by_sku_reg_clus['Cluster'].isin(cluster2rank_map.keys())
        ].rename(columns = {'Articolo Radice_COD': sku_id}
        ).groupby(
            [sku_id, 'Regione'],
            as_index = False
        )[['total_sellout_revenues', 'total_sellout_volume',
           'total_margin_cost', 'total_margin_sold']
        ].sum()
    # sales mkt vs cno from metadata
    mk_vs_cno = pd.read_csv(cat_mk_vs_cno, sep=";", decimal= ",", encoding='latin-1')
    mk_vs_cno_grpkey = pd.read_csv(cat_mk_vs_cno_grpkey, sep=";", decimal= ",", encoding='latin-1')
    print("listing: step 2 - produce list of similar SKUs to new EANs")
    # Assign to each 'group_key' value (Tipo-Varieta) the corresponding most similar group
    # This will determine the cannibal bucket for new EAN of that Tipo-Varieta
    # (if no valid similar SKU exists, create an empty DataFrame)
    if df_groups.shape[0]:
        assigned_grps = df_groups.groupby([sku_gkey_focus]).apply(
            lambda x:assign_group(x),
            include_groups=False
        ).reset_index(name=sku_group)
    else:
        assigned_grps = pd.DataFrame(columns = [sku_gkey_focus, sku_group])
    #
    # Attach the actual SKUs that can be cannibalized, their loyalty and sales
    potential_sub = assigned_grps.merge(df_groups[[sku_id_focus, sku_desc_focus,
                                            sku_group, sku_gkey_focus]].drop_duplicates(),
                                        on=[sku_group, sku_gkey_focus], how="left").rename(columns={
                                                sku_gkey_focus:group_key,
                                                sku_id_focus:sku_id,
                                                sku_desc_focus:sku_desc
                                        })
    #PATCH DEL 02-04-2026
    potential_sub[sku_desc] = potential_sub[sku_desc].astype(str)
    df_loyalty[sku_desc] = df_loyalty[sku_desc].astype(str)
    # FINE PATCHE
    potential_sub = potential_sub.merge(df_loyalty, on=[sku_id, sku_desc, sku_group], how="left")
    potential_sub = potential_sub.merge(sku_sold[["sku_id", "avg_monthly_quantity"]].rename(columns={'sku_id':sku_id}),
                          on=[sku_id], how="left")
    # Define sales quintiles in order to sort the cannibalized SKUs based on their "popularity"
    potential_sub["quant"] = potential_sub.groupby([group_key, sku_group])["avg_monthly_quantity"].transform(lambda x:
                                    pd.qcut(x, sales_quants, labels=False, duplicates='drop') if not x.isna().all()
                                        else np.nan).fillna(0)
    potential_sub = potential_sub.sort_values(
            by = ['quant', 'loyalty'],
            ascending = (False, True)
        )[[group_key, sku_group, sku_id, sku_desc, 'loyalty', 'quant']]
    potential_sub["mean_loyalty"] = potential_sub.groupby([group_key])['loyalty'].transform("mean")
    # finally, for each group_key and region, pick the first 10 based on sales (quantized) and reversed loyalty
    ### V1 - correct but too granular
    #potential_sub = potential_sub.merge(
    #            sales_by_sku_reg_clus.loc[
    #                sales_by_sku_reg_clus['Cluster'].isin(cluster2rank_map.keys()) &
    #                (sales_by_sku_reg_clus['total_sellout_revenues']>0)][
    #            ['Articolo Radice_COD', 'Regione', 'Cluster',
    #                'total_sellout_revenues', 'total_sellout_volume',
    #                'total_margin_cost', 'total_margin_sold']
    #            ].rename(columns={'Articolo Radice_COD': sku_id}),
    #                on = [sku_id])
    ### end of V1
    ### V2 - correct at regional level

    #CEGIL: ERRORE DI TIPO:
    # 1. Prepara il DataFrame di sinistra e converti la colonna chiave in stringa
    left_df = potential_sub[[sku_id, group_key, 'Gruppo', 'quant', 'loyalty']].copy()
    left_df[sku_id] = left_df[sku_id].astype(str)

    # 2. Prepara il DataFrame di destra e converti la colonna chiave in stringa
    right_df = sales_by_sku_reg_clus.loc[
        sales_by_sku_reg_clus['Cluster'].isin(cluster2rank_map.keys()) &
        (sales_by_sku_reg_clus['total_sellout_revenues'] > 0)
        ][['Articolo Radice_COD', 'Regione']].drop_duplicates()

    right_df = right_df.rename(columns={'Articolo Radice_COD': sku_id})
    right_df[sku_id] = right_df[sku_id].astype(str)
    # 3. Ora esegui il merge con i tipi di dato allineati
    top10_helper = left_df.merge(right_df, on=[sku_id])

    #top10_helper = potential_sub[[sku_id, group_key, 'Gruppo', 'quant', 'loyalty']].merge(
    #            sales_by_sku_reg_clus.loc[
    #                sales_by_sku_reg_clus['Cluster'].isin(cluster2rank_map.keys()) &
    #                (sales_by_sku_reg_clus['total_sellout_revenues']>0)][
    #            ['Articolo Radice_COD', 'Regione']
    #            ].drop_duplicates().rename(
    #                columns={'Articolo Radice_COD': sku_id}
    #            ), on = [sku_id]
    #            )
    top10_helper = top10_helper.sort_values(
        by=[group_key, 'Gruppo', 'Regione', 'quant', 'loyalty'],
        ascending=(True, True, True, False, True)
    ).reset_index(drop=True).groupby([group_key, 'Gruppo', 'Regione']).head(max_subs_to_keep)

    #CEGIL
    df_left = sales_by_sku_reg_clus.loc[
        sales_by_sku_reg_clus['Cluster'].isin(cluster2rank_map.keys()) &
        (sales_by_sku_reg_clus['total_sellout_revenues'] > 0)
        ][
        ['Articolo Radice_COD', 'Regione', 'Cluster', 'total_sellout_revenues',
         'total_sellout_volume', 'total_margin_cost', 'total_margin_sold']
    ].rename(columns={'Articolo Radice_COD': sku_id})

    df_left[sku_id] = df_left[sku_id].astype(str)
    top10_helper[sku_id] = top10_helper[sku_id].astype(str)

    top10_sku_reg = df_left.merge(top10_helper[[sku_id, 'Regione']], on=[sku_id, "Regione"])

    #top10_sku_reg = sales_by_sku_reg_clus.loc[
    #    sales_by_sku_reg_clus['Cluster'].isin(cluster2rank_map.keys()) &
     #   (sales_by_sku_reg_clus['total_sellout_revenues'] > 0)][
    #    ['Articolo Radice_COD', 'Regione', 'Cluster',
    #     'total_sellout_revenues', 'total_sellout_volume',
    #     'total_margin_cost', 'total_margin_sold']
    #].rename(columns={'Articolo Radice_COD': sku_id}).merge(
     #   top10_helper[[sku_id, 'Regione']], on=[sku_id, "Regione"]
    #)



    sku_cannibal_bkt = potential_sub.merge(top10_sku_reg, on = [sku_id])
    ### end of V2
    # Next, we compute transferrable sales for those items
    sku_cannibal_bkt['transferrable_revenue'] = transfer_factor * (1 - sku_cannibal_bkt['loyalty']) * \
                                                    sku_cannibal_bkt['total_sellout_revenues']
    sku_cannibal_bkt['transferrable_volume'] = transfer_factor * (1 - sku_cannibal_bkt['loyalty']) * \
                                                    sku_cannibal_bkt['total_sellout_volume']
    ### needed?!? we could just sum over clusters...
    sku_cannibal_bkt[sku_id]=sku_cannibal_bkt[sku_id].astype(str)
    sales_by_sku_reg[sku_id]=sales_by_sku_reg[sku_id].astype(str)
    sku_clus_reg_meta['Articolo Radice_COD']=sku_clus_reg_meta['Articolo Radice_COD'].astype(str)
    sku_cannibal_bkt = sku_cannibal_bkt.merge(
            sales_by_sku_reg[[sku_id, 'Regione', 'total_sellout_revenues', 'total_sellout_volume']
            ].rename(columns = {
                'total_sellout_revenues': 'revenues_by_region_sub',
                'total_sellout_volume': 'volume_by_region_sub'
            }),
            on = [sku_id, 'Regione']
            )
    # Add sku score
    sku_cannibal_bkt = sku_cannibal_bkt.merge(
            sku_clus_reg_meta[['Articolo Radice_COD', 'Cluster', 'Regione', sku_score]
            ].rename(columns = {'Articolo Radice_COD': sku_id}
            ), on = [sku_id, 'Cluster', 'Regione'],
            )
    ### FIXMEEE fails on 10 & 50?
    #run_checks(bkt_single_reg)
    print("listing: step 3 - prepare new products")
    # Identify new products that can potentially be listed

#    sku_clus_reg_meta=sku_clus_reg_meta[sku_clus_reg_meta["EAN"].astype(str)]
    sku_clus_reg_meta["EAN"]= sku_clus_reg_meta["EAN"].astype(str)

    new_sku = sku_clus_reg_meta.loc[sku_clus_reg_meta["Categoria Merceologica"] == "Non in assortimento CNO"]
    new_sku = new_sku[new_sku[group_key].isin(df_groups[sku_gkey_focus].unique())]
    new_sku = new_sku[new_sku[sku_score]>=min_sku_score]
    new_sku = new_sku[(~new_sku["EAN"].str.contains("Private Label", na=False))]
    new_sku = new_sku[new_sku[mkt_revenue]>min_mkt_revenue_by_new_sku_region]

    # new_sku = sku_clus_reg_meta[
    #     (sku_clus_reg_meta["Categoria Merceologica"]=="Non in assortimento CNO") &
    #     (sku_clus_reg_meta[group_key].isin(df_groups[sku_gkey_focus].unique())) &
    #     (sku_clus_reg_meta[sku_score]>=min_sku_score) &
    #     (~sku_clus_reg_meta["EAN"].str.contains("Private Label", na=False)) &
    #     (sku_clus_reg_meta[mkt_revenue]>min_mkt_revenue_by_new_sku_region)
    #     ]
    new_sku = filter_eligible_skus(
        clus_reg_cno_shares = clus_reg_sales,
        gkey_reg_cno_sales = mk_vs_cno_grpkey,
        eligible_new_sku = new_sku
        )
    new_sku['EAN'] = new_sku['EAN'].astype(str)
    print('New SKU df shape: ', new_sku.shape)
    if new_sku.shape[0] == 0:
        empty_cat.append(cat)
        return
    helper2 = sku_cannibal_bkt[[group_key, "Regione", "mean_loyalty"]].drop_duplicates()
    support = sales_by_sku_reg_clus[["Categoria IRI", "Regione", "Tipo-Varieta",
                                     "margin_sold_incidence",
                                     "margin_cost_incidence"]].rename(columns={"Categoria IRI":"Categoria"})
    support = support.groupby(["Categoria", "Regione", "Tipo-Varieta"]).agg(
                        margin_sold_incidence=('margin_sold_incidence','mean'),
                        margin_cost_incidence=('margin_cost_incidence','mean') ).reset_index()
    # create all possible combinations of cannibalised SKUs, regions and clusters
    multi_idx = pd.MultiIndex.from_product([
                            sku_cannibal_bkt[sku_id].unique(),
                            sku_cannibal_bkt["Regione"].unique(),
                            list(cluster2rank_map.keys())
                        ], names=[sku_id, 'Regione', 'Cluster']).to_frame(index=False)
    # keep only the existing pairs (SKU ID, 'Regione') and add info to complete the table in next join
    multi_idx = multi_idx.merge(sku_cannibal_bkt[
                                ['Gruppo', sku_id, sku_desc, 'loyalty',
                                group_key, 'quant', 'Regione']].drop_duplicates(),
                on=[sku_id, 'Regione'])
    # add missing clusters and fill last columns
    helper = sku_cannibal_bkt.merge(multi_idx,
        on = [sku_id, 'Regione', 'Cluster', 'Gruppo', 'loyalty', sku_desc, group_key, 'quant'],
        how = 'right')
    for col in ['revenues_by_region_sub', 'volume_by_region_sub', sku_score]:
        helper[col] = helper.groupby(
            [sku_id, 'Regione'])[col].transform("max")
    helper = helper.fillna(0)
    #
    tmp = new_sku[["EAN", "Categoria", "Tipo-Varieta", "Regione", mkt_revenue, mkt_volume]]
    tmp = tmp.merge(mk_vs_cno[["Categoria", "Regione", "perc_revenue", "perc_volume"]], on=["Categoria", "Regione"], how="left")
    tmp = tmp.merge(
        support,
        on = ["Categoria", "Regione", "Tipo-Varieta"],
        how = "left"
        )
    #AHIA
    tmp = tmp.merge(
        clus_reg_sales.loc[
        # remove clusters not present in transactions data in any SKU of the selected category
        clus_reg_sales['clus_rev_perc_cno_by_cat']>0,
            ["Categoria", "Regione", "Cluster",
            'clus_sellout_rev_perc_cno_by_cat', 'clus_sellout_vol_perc_cno_by_cat',
            'clus_margin_cost_perc_cno_by_cat', 'clus_margin_sold_perc_cno_by_cat']],
        on = ["Categoria", "Regione"],
        how = "left"
        )
    #print('Step 1')
    ########
    # Calculate expected total using cno share wrt market for revenues and volumes
    # and avg margin per product at category-region-group_key level for margins
    ########
    # Estimate total yearly sales of new item as market sales of
    # new item * CNO share for that category and that region
    # (use share calculated based on vendite in valore e volume CNO over MKT)
    tmp["region_new_revenue"] = tmp[mkt_revenue] * tmp["perc_revenue"]
    tmp["region_new_volume"] = tmp[mkt_volume] * tmp["perc_volume"]
    # Estimate total yearly margin of new item using the avg incidence of margin cost and margin sold
    # for that category, region and group key (considering only category and region may be too broad)
    tmp["region_new_margin_sold"] = tmp["region_new_revenue"] * tmp["margin_sold_incidence"]
    tmp["region_new_margin_cost"] = tmp["region_new_revenue"] * tmp["margin_cost_incidence"]
    ## Estimate total sales of new item for each cluster
    # use sellout columns for the redistribution of cno sales by cluster
    tmp["clus_new_revenue"] = tmp["region_new_revenue"] * tmp["clus_sellout_rev_perc_cno_by_cat"]
    tmp["clus_new_volume"] = tmp["region_new_volume"] * tmp["clus_sellout_vol_perc_cno_by_cat"]
    tmp["clus_new_margin_cost"] = tmp["region_new_margin_cost"] * tmp["clus_margin_cost_perc_cno_by_cat"]
    tmp["clus_new_margin_sold"] = tmp["region_new_margin_sold"] * tmp["clus_margin_sold_perc_cno_by_cat"]
    ## FIXMEEEE: fails with VINI_LIQUOROSI (new_item 6000/7400)
    #    cols_dict = {
    #        'revenue': [region_new_revenue, 'sellout_rev_perc_cno_by_cat'],
    #        'volume': [region_new_volume, 'sellout_vol_perc_cno_by_cat'],
    #        'margin_cost': [region_new_margin_cost, 'margin_cost_perc_cno_by_cat'],
    #        'margin_sold': [region_new_margin_sold, 'margin_sold_perc_cno_by_cat'],
    #        }
    #for el in cols_dict.items():
    #    suffix = el[0]
    #    print(suffix)
    #    if clus_new_sales[f'clus_new_{suffix}'].sum() > 0:
    #        assert round(clus_new_sales[f'clus_new_{suffix}'].sum(), 0
    #        ) == round(el[1][0], 0
    tmp = tmp.merge(helper2,
                on=["Tipo-Varieta", "Regione"], how="left")
    tmp["on_top_factor"] = on_top_factor * tmp.shape[0]
    tmp.loc[tmp["mean_loyalty"]==0, "on_top_factor"] = 0
    #
    tmp["clus_on_top_revenue"] = tmp["clus_new_revenue"] * tmp[["mean_loyalty", "on_top_factor"]].max(axis=1)
    tmp["clus_on_top_volume"] = tmp["clus_new_volume"] * tmp[["mean_loyalty", "on_top_factor"]].max(axis=1)
    #
    tmp["clus_cannibal_revenue"] = tmp["clus_new_revenue"] - tmp["clus_on_top_revenue"]
    tmp["clus_cannibal_volume"] = tmp["clus_new_volume"] - tmp["clus_on_top_volume"]
    support2 = tmp[["EAN", "Regione", "Cluster", "Tipo-Varieta"]].drop_duplicates().reset_index(drop=True)
    support2 = support2.merge(helper[["Regione", "Cluster", "Tipo-Varieta",
                                  "ART_RADICE_COD", "ART_RADICE_DESC", "Gruppo", "total_sellout_revenues",
                                  "total_sellout_volume", "total_margin_cost", "total_margin_sold",
                                  "transferrable_revenue", "transferrable_volume",
                                  "revenues_by_region_sub", "volume_by_region_sub"]],
                          on=["Regione", "Cluster", "Tipo-Varieta"], how="left")
    support2["ean_transferrable_revenue"] = support2.groupby(["EAN", "Regione", "Cluster", "Tipo-Varieta"])['transferrable_revenue'].transform("sum")
    support2["ean_transferrable_volume"] = support2.groupby(["EAN", "Regione", "Cluster", "Tipo-Varieta"])['transferrable_volume'].transform("sum")
    #support2.tail(5)
    #print('Step 3')
    tmp2 = tmp.merge(support2, on=["EAN", "Regione", "Cluster", "Tipo-Varieta"], how="left")
    tmp2["rescaled_tx_revenue"] = tmp2["clus_cannibal_revenue"] * tmp2["transferrable_revenue"] / tmp2["ean_transferrable_revenue"]
    tmp2["transferred_revenue"] = tmp2["transferrable_revenue"]
    change_condn = (tmp2["ean_transferrable_revenue"] > 0) & (tmp2["ean_transferrable_revenue"] > tmp2["clus_cannibal_revenue"])
    tmp2.loc[change_condn, "transferred_revenue"] = tmp2.loc[change_condn,"rescaled_tx_revenue"]
    tmp2.loc[~change_condn, "clus_on_top_revenue"] = tmp2.loc[~change_condn,"clus_on_top_revenue"] + (
        tmp2.loc[~change_condn,"clus_cannibal_revenue"] - tmp2.loc[~change_condn,"ean_transferrable_revenue"])
    tmp2.loc[~change_condn, "clus_cannibal_revenue"] = tmp2.loc[~change_condn,"clus_new_revenue"] - tmp2.loc[~change_condn,"clus_on_top_revenue"]
    tmp2 = tmp2.drop("rescaled_tx_revenue", axis=1)
    #
    tmp2["rescaled_tx_volume"] = tmp2["clus_cannibal_volume"] * tmp2["transferrable_volume"] / tmp2["ean_transferrable_volume"]
    tmp2["transferred_volume"] = tmp2["transferrable_volume"]
    change_condn = (tmp2["ean_transferrable_volume"] > 0) & (tmp2["ean_transferrable_volume"] > tmp2["clus_cannibal_volume"])
    tmp2.loc[change_condn, "transferred_volume"] = tmp2.loc[change_condn,"rescaled_tx_volume"]
    tmp2.loc[~change_condn, "clus_on_top_volume"] = tmp2.loc[~change_condn,"clus_on_top_volume"] + (
        tmp2.loc[~change_condn,"clus_cannibal_volume"] - tmp2.loc[~change_condn,"ean_transferrable_volume"])
    tmp2.loc[~change_condn, "clus_cannibal_volume"] = tmp2.loc[~change_condn,"clus_new_volume"] - tmp2.loc[~change_condn,"clus_on_top_volume"]
    tmp2 = tmp2.drop("rescaled_tx_volume", axis=1)
    ####
    #FAILS WITH PRODOTTI_EQUO_SOLIDALI
    #for suffix in cols_suffix:
    #    assert round(cannibal_bucket[f'transferred_{suffix}'].sum(),5)==\
    #            round(clus_new_sales[f'clus_cannibal_{suffix}'].sum(), 5)
    ####
    # Compute cannibalised ratio
    #print('Step 5')
    tmp2["tot_transf_rev"] = tmp2.groupby(["EAN", "Regione", "Cluster", "Tipo-Varieta"])['transferred_revenue'].transform("sum")
    tmp2["cannibalised_ratio_on_sub"] = tmp2["transferred_revenue"] / tmp2["tot_transf_rev"]
    tmp2=tmp2.drop("tot_transf_rev", axis=1)
    # check
    ## FIXMEEE FAILS WITH VINI_LIQUOROSI
    ##assert 0 == sum(cannibal_bucket.groupby('Cluster')['cannibalised_ratio_on_sub'].sum().round(3)!=1)
    # Compute cannibalised ratio
    tmp2["clus_cannibalised_ratio"] = (tmp2["clus_cannibal_revenue"] / tmp2['clus_new_revenue']).fillna(0)
    # check
    #FIXMEEE FAILS WITH PRODOTTI_EQUO_SOLIDALI
    #if cannibal_bucket.shape[0]>0:
    #    for suffix in cols_suffix:
    #        assert round(cannibal_bucket[f'transferred_{suffix}'].sum(),5
    #          ) == round(clus_new_sales[f'clus_cannibal_{suffix}'].sum(),5
    #            )
    #####################
    ## 3. Calculate margins
    #####################
    #print('Step 6')
    tmp2["total_margin"] = tmp2["total_margin_sold"] - tmp2["total_margin_cost"]
    tmp2["total_margin_pct"] = tmp2.apply(
                lambda row: 0 if row["total_margin_sold"]==0 else (
                    row["total_margin"] / row["total_margin_sold"]),
                axis = 1
                )
    tmp2["transferred_margin"] = tmp2.apply(
                lambda row: get_transferred_margin_by_sub(
                    row, revenue_col = "total_sellout_revenues"), axis=1)
    # Add total margin transferred from cannibalised products
    tmp2["clus_transferred_margin"] = tmp2.groupby(["EAN", "Regione", "Cluster", "Tipo-Varieta"])['transferred_margin'].transform("sum")
    # check
    #assert 0 == cannibal_bucket.groupby(
    #                ['Cluster']
    #                )[['transferred_revenue']].sum(
    #            ).join(
    #                clus_new_sales[['clus_cannibal_revenue']]
    #            ).diff(axis=1).iloc[:, 1].round(4).sum()
    #assert 0 == cannibal_bucket.groupby(
    #                ['Cluster']
    #                )[['transferred_margin']].sum(
    #            ).join(
    #                clus_new_sales[['transferred_margin']],
    #                rsuffix='_right'
    #            ).diff(axis=1).iloc[:, 1].round(4).sum()
    # Calculate total and lost margin for each SKU at region and cluster level
    tmp2['clus_new_margin'] = tmp2['clus_new_margin_sold'] - tmp2['clus_new_margin_cost']
    tmp2['clus_new_margin_pct'] = (tmp2['clus_new_margin'] / tmp2['clus_new_margin_sold']).fillna(0)
    tmp2['clus_on_top_margin'] = tmp2['clus_new_margin'] - tmp2['clus_transferred_margin']
    #####################
    ## 4. Calculate cumulative impact
    #####################
    # Add cumulative on-top metrics
    #print('Step 7')
    tmp2['Clus_Help'] = tmp2['Cluster'].map(pd.Series(cluster2rank_map))
    cumul_support = tmp2[[
        "EAN", "Regione", "Tipo-Varieta", "Cluster", "Clus_Help",
        "clus_on_top_revenue", "clus_on_top_volume", "clus_on_top_margin"]
        ].drop_duplicates().reset_index()
    for metric in ['revenue', 'volume', 'margin']:
        cumul_support[f"from_clus_on_top_{metric}"] = cumul_support.sort_values(
            by = ["EAN", "Regione", "Tipo-Varieta", "Clus_Help"]
            ).groupby(
            ["EAN", "Regione", "Tipo-Varieta"]
            )[f"clus_on_top_{metric}"].transform(
                lambda x: x.cumsum()
            )
    tmp2 = tmp2.merge(cumul_support[["EAN", "Regione", "Tipo-Varieta", "Cluster",
                                   "from_clus_on_top_revenue", "from_clus_on_top_volume", "from_clus_on_top_margin"]],
                    on=["EAN", "Regione", "Tipo-Varieta", "Cluster"], how="left")
    # checks
    ## FIXMEEE FAILS WITH VINI_LIQUOROSI
    #for el in ['revenue', 'volume', 'margin']:
    #    run_checks2(clus_new_sales, el, cols_dict, round_dig=0)
    # Add cumulative transferred revenues after adding missing clusters
    #FAILS WITH PRODOTTI_EQUO_SOLIDALI
    #for suffix in cols_suffix:
    #    assert round(cannibal_bucket[f'transferred_{suffix}'].sum(),5
    #      ) == round(clus_new_sales[f'clus_cannibal_{suffix}'].sum(),5
    #        )
    ###############
    # Add missing clusters
    # Calculate the smallest cluster having non null similar SKUs for each EAN and region
    tmp2['max_clus_help1'] = np.where(tmp2[sku_id].isna(), np.nan, tmp2['Clus_Help'])
    tmp2['max_clus_help'] = tmp2.groupby(
        ['EAN', 'Regione']
        )['max_clus_help1'].transform("max")
    # add similar SKUs to missing clusters smaller than the smallest existing cluster
    cols_for_miss_clus = [sku_id, sku_desc, 'Gruppo', 'revenues_by_region_sub', 'volume_by_region_sub']
    missing_clus_tmp = tmp2.loc[
            tmp2['max_clus_help1'].isna()
            ].drop(columns = cols_for_miss_clus
        ).merge(
            support2[['EAN', 'Regione'] + cols_for_miss_clus].dropna(),
            on = ['EAN', 'Regione']
        )
    tmp2 = pd.concat([
        tmp2.loc[(
            tmp2['Clus_Help'] <= tmp2['max_clus_help']) | (
            tmp2['max_clus_help'].isna())
        ],
        missing_clus_tmp
        ]).drop(columns=['max_clus_help', 'max_clus_help1'])
    del missing_clus_tmp
    # Fill missing values - numerical
    tmp2 = tmp2.fillna(0)
    # Add cumulative columns for transferred revenues
    tmp2 = tmp2.sort_values(
        by = ['EAN', sku_id, 'Regione', 'Clus_Help'],
        ascending = True
        )
    #print('Step 8')
    for c in ['transferred_revenue', 'transferred_volume', 'transferred_margin']:
        tmp2[c+'_cumul'] = tmp2.groupby(
            ['EAN', sku_id, 'Regione']
            )[c].transform(lambda x: x.cumsum())
    tmp2['transferred_revenue_cumul_by_cluster'] = tmp2.groupby(
        ['EAN', 'Regione', 'Cluster']
        )['transferred_revenue_cumul'].transform("sum")
    tmp2['cannibalised_ratio_on_sub_cumul'] = tmp2.apply(
        lambda row: 0 if row['transferred_revenue_cumul_by_cluster'] == 0 else (
            row['transferred_revenue_cumul'] / row['transferred_revenue_cumul_by_cluster']),
            axis = 1
        )
    tmp2 = tmp2.drop(columns='transferred_revenue_cumul_by_cluster')
    # checks
    #assert sum(round(
    #            cannibal_bucket.groupby(['Cluster'])['cannibalised_ratio_on_sub_cumul'].sum(), 2
    #            ) != 1) == 0
    #for metric in ['revenue', 'volume']:
    #    assert 0 == cannibal_bucket.groupby('Cluster')[[f'transferred_{metric}']].sum().join(
    #                clus_new_sales[f'clus_cannibal_{metric}']
    #                ).diff(axis=1).iloc[:,1].round(2).sum()
    #####################
    ## 5. Prepare output
    #####################
    #print('Step 9')
    new_listed = tmp2[["EAN", "Categoria", "Tipo-Varieta", "Regione", "Cluster",
                    "clus_cannibalised_ratio",
                    # revenues
                    "clus_new_revenue", "clus_on_top_revenue",
                    "clus_cannibal_revenue", "from_clus_on_top_revenue",
                    # volume
                    "clus_new_volume", "clus_on_top_volume",
                    "clus_cannibal_volume", "from_clus_on_top_volume",
                    # margin
                    "clus_new_margin", "clus_on_top_margin",
                    "clus_transferred_margin",
                    "clus_new_margin_pct", "from_clus_on_top_margin"
                   ]].drop_duplicates().reset_index(drop=True)
    new_listed['Categoria CNO'] = re.sub("_", " ", str(cat))
    new_listed = new_listed.merge(new_sku[["EAN", "Regione", "Prodotto", sku_score,
                                            "Marca", "Fornitore", "Settore"]].drop_duplicates(),
                                            on=["EAN", "Regione"], how="left")
    #CEGIL: new_listed['ProdClean'] = new_listed['Prodotto'].map(lambda x: x.split('-')[1])
    #new_listed['Prodotto']=new_listed['Prodotto'].astype(str)
    #new_listed['ProdClean'] = new_listed['Prodotto'].map(lambda x: x.split('-')[0])
    new_listed['ProdClean'] = new_listed['Prodotto']
    new_listed['Tipo'] = new_listed[group_key].map(lambda x: x.split('/')[0])
    new_listed['Varietà'] = new_listed[group_key].map(lambda x: x.split('/')[1])
    ## prepare output: variables in a specific order and with specific names
    new_listed = new_listed[["EAN", "Prodotto", "ProdClean", "Settore",
                             "Categoria CNO", "Categoria", group_key,
                             "Tipo", "Varietà", "Marca", "Fornitore",
                             "Regione", "Cluster", sku_score,
                             "clus_cannibalised_ratio",
                             "clus_new_revenue", "clus_on_top_revenue",
                             "clus_cannibal_revenue", "from_clus_on_top_revenue",
                             "clus_new_volume", "clus_on_top_volume",
                             "clus_cannibal_volume", "from_clus_on_top_volume",
                             "clus_new_margin", "clus_on_top_margin",
                             "clus_transferred_margin",
                             "clus_new_margin_pct", "from_clus_on_top_margin"
    ]].rename(columns={
        "EAN": "Nuovo EAN",
        "Prodotto": "Nuovo prodotto (original)",
        "ProdClean": "Nuovo prodotto",
        sku_score: "Priorità assortimento",
        "Categoria": "Categoria IRI",
        "clus_cannibalised_ratio": "Tasso di cannibalizzazione",
        # revenue columns
        "clus_new_revenue": "Fatturato annuale atteso (singolo)",
        "clus_on_top_revenue": "Fatturato annuale atteso netto (singolo)",
        "clus_cannibal_revenue": "Fatturato annuale atteso cannibalizzato (singolo)",
        "from_clus_on_top_revenue": "Fatturato annuale atteso netto (cumulato)",
        # volume columns
        "clus_new_volume": "Volumi annuali attesi (singolo)",
        "clus_on_top_volume": "Volumi annuali attesi netti (singolo)",
        "clus_cannibal_volume": "Volumi annuali attesi cannibalizzati (singolo)",
        "from_clus_on_top_volume": "Volumi annuali attesi netti (cumulato)",
        # margin columns
        "clus_new_margin": "Margine annuale atteso (singolo)",
        "clus_on_top_margin": "Margine annuale atteso netto (singolo)",
        "clus_transferred_margin": "Margine annuale atteso cannibalizzato (singolo)",
        "clus_new_margin_pct": "Margine pct annuale atteso (singolo)",
        "from_clus_on_top_margin": "Margine annuale atteso netto (cumulato)",
    })
    ###
    #print('Step 10')
    sub_listed = tmp2.loc[(
            tmp2[sku_id]!=0) & (
            tmp2['cannibalised_ratio_on_sub_cumul']>0),
        ["EAN", "Categoria", "Tipo-Varieta", "Regione", "Cluster",
        sku_id, sku_desc,
        "cannibalised_ratio_on_sub", "cannibalised_ratio_on_sub_cumul",
        # revenues
        "total_sellout_revenues", "transferred_revenue",
        "transferred_revenue_cumul", "revenues_by_region_sub",
        # volume
        "total_sellout_volume", "transferred_volume",
        "transferred_volume_cumul", "volume_by_region_sub",
        # margin
        "total_margin", "total_margin_pct",
        "transferred_margin", "transferred_margin_cumul"
       ]].drop_duplicates(
        ).reset_index(drop = True)
    # missing sku_desc!!!
    sub_listed['Categoria CNO'] = re.sub("_", " ", str(cat))
    sub_listed = sub_listed.merge(new_sku[["EAN", "Regione", "Prodotto", sku_score,
                                            "Marca", "Fornitore", "Settore"]].drop_duplicates(),
                                            on=["EAN", "Regione"], how="left")
    #CEGIL:sub_listed['ProdClean'] = sub_listed['Prodotto'].map(lambda x: x.split('-')[1])
    #sub_listed['ProdClean'] = sub_listed['Prodotto'].map(lambda x: x.split('-')[0])
    sub_listed['ProdClean'] = sub_listed['Prodotto']
    sub_listed['Tipo'] = sub_listed[group_key].map(lambda x: x.split('/')[0])
    sub_listed['Varietà'] = sub_listed[group_key].map(lambda x: x.split('/')[1])
    ## prepare output: variables in a specific order and with specific names
    sub_listed = sub_listed[["EAN", "ProdClean", "Settore",
                             "Categoria CNO", "Categoria", group_key,
                             "Regione", "Cluster", sku_score,
                             sku_id, sku_desc,
                             "cannibalised_ratio_on_sub", "cannibalised_ratio_on_sub_cumul",
                             "total_sellout_revenues", "transferred_revenue",
                             "transferred_revenue_cumul", "revenues_by_region_sub",
                             "total_sellout_volume", "transferred_volume",
                             "transferred_volume_cumul", "volume_by_region_sub",
                             "total_margin", "total_margin_pct",
                             "transferred_margin", "transferred_margin_cumul"
    ]].rename(columns={
        "EAN": "Nuovo EAN",
        "ProdClean": "Nuovo prodotto",
        sku_score: "Priorità assortimento",
        "Categoria": "Categoria IRI",
        sku_id: "Articolo Radice COD (Cannibalizzato)",
        sku_desc: "Prodotto cannibalizzato",
        # sku_score: "Priorità assortimento",
        "cannibalised_ratio_on_sub": "Proporzione 'rubata'",
        "cannibalised_ratio_on_sub_cumul": "Proporzione 'rubata' (cumulato)",
        # revenues
        "total_sellout_revenues": 'Fatturato annuale (Cannibalizzato)',
        "transferred_revenue": "Fatturato annuale 'rubato' dal nuovo SKU",
        "transferred_revenue_cumul": "Fatturato annuale 'rubato' dal nuovo SKU (cumulato)",
        "revenues_by_region_sub": "Fatturato annuale per regione",
        # volume
        "total_sellout_volume": "Volumi annuali (Cannibalizzato)",
        "transferred_volume": "Volumi annuali 'rubati' dal nuovo SKU",
        "transferred_volume_cumul": "Volumi annuali 'rubati' dal nuovo SKU (cumulato)",
        "volume_by_region_sub": "Volumi annuali per regione",
        # margin
        "total_margin": "Margine annuale (Cannibalizzato)",
        "total_margin_pct": "Margine pct annuale (Cannibalizzato)",
        "transferred_margin": "Margine annuale 'rubato' dal nuovo SKU",
        "transferred_margin_cumul": "Margine annuale 'rubato' dal nuovo SKU (cumulato)"
    })
    #print('Step 11')
    if len(new_listed) == 0 and len(sub_listed) == 0:
        empty_cat.append(cat)
        return
    # ## Prepare output for dashboard
    # ### First sheet
    list1 = new_listed.drop_duplicates(subset=None, keep='first', inplace=False)
    print("output 1 shape: ", list1.shape) #2310
    # ### Second sheet
    list2 = sub_listed.drop_duplicates(subset=None, keep='first', inplace=False)

    print("output 2 shape: ", list2.shape) #18530
    # Save output for dashboard
    #if write_out:
    #    with pd.ExcelWriter(cat_listing) as writer:
    #        list1.to_excel(writer, sheet_name="choose sku-cluster to list", index=False)
    #        list2.to_excel(writer, sheet_name="top 10 cannibalised skus", index=False)
    #        ##print(f'Output saved in {cat_listing}')

    colonna_margine = 'Margine annuale atteso netto (cumulato)'
    colonne_list1 = list1.columns.drop(colonna_margine)

    # 3. Applica la logica di prima usando la lista di colonne appena creata
    df_pulito = list1.sort_values(colonna_margine).drop_duplicates(
        subset=colonne_list1,
        keep='first'
    )

    if write_out:
        list1.to_parquet(re.sub(".xlsx$", "_sheet1.parquet", cat_listing), index=False)
        list2.to_parquet(re.sub(".xlsx$", "_sheet2.parquet", cat_listing), index=False)
        list1.to_csv(cat_out + 'listing1.csv', index=False, sep=';', decimal='.', encoding='latin-1')
        list2.to_csv(cat_out + 'listing2.csv', index=False, sep=';', decimal='.', encoding='latin-1')


if __name__ == "__main__":

    if len(sys.argv) < 2:
        print("ERRORE: Nessuna categoria fornita.")
        print("Uso: python metadata.py <nome_categoria>")
        sys.exit(1)  # Esce con un codice di errore

    current_category = sys.argv[1]

    process_single_category(current_category)

    sys.exit(0)  # Esce indicando successo
