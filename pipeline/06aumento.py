# ## Augmentation of existing SKUs in new clusters
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

# log_file = config['files'].get('logging_file')
# if log_file is None:
#     log_file = "log_Modulo3.txt"

# misc options
min_sku_score = config['parameters']['augm_min_score']
max_subs_to_keep = config['parameters']['augm_max_cannib']
# max proportion of sales that the new SKU can cannibalise from each similar product
transfer_factor = config['parameters']['augm_tx_factor']
# max proportion of sales that can be allocated to net new sales (vs cannibalised) for the new SKU
# Note: the formula will use the max value between this threshold and the mean loyalty;
# set the threshold to 0 if you don't want to use it, so that the mean loyalty will be considered
on_top_factor = config['parameters']['augm_ot_factor']
# Number of quantiles used in sales to separate similar SKUs for sales cannibalization (default: quintiles)
sales_quants = config['parameters']['augm_sales_quants']

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
sku_desc_meta = lista_colonne['sku_desc_meta']
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

col_rename_dict = {
    'Sellout Importo': 'revenues',
    'Sellout Quantita': 'volume',
    'Margine Costo Netto': 'margin_cost',
    'Margine Venduto': 'margin_sold'
    }

share2total_map = {
    'clus_sellout_rev_perc_cno_by_cat': 'revenues',
    'clus_sellout_vol_perc_cno_by_cat': 'volume',
    'clus_margin_cost_perc_cno_by_cat': 'margin_cost',
    'clus_margin_sold_perc_cno_by_cat': 'margin_sold'
    }

def smart_load_to_pd(fname, sep, decimal, encoding):
    _, file_ext = os.path.splitext(fname)
    if file_ext == "zip":
        return pd.read_csv(fname, compression='zip', sep=sep, decimal=decimal, encoding=encoding)
    else:
        return pd.read_csv(fname, sep=sep, decimal=decimal, encoding=encoding)


# ### Identify existing SKUs eligible for listing
# For each existing, active SKU for the selected category, for each region (where avg priorità assortimento for that SKU and that region >=3):
# - (a) If it is not present in that region yet, then ignore (no listing)
# - (b) If it is present in that region in all valid clusters, then ignore (no listing needed)
# - (c) If it is present in that region but not in all clusters, assess impact in each missing cluster
#   - Exclude clusters that do not exist in any SKU for that category, e.g. M2 and SPAZIO for Merendine
#   - Cumulate impact: from cluster x and above, excluding clusters as explained in note above and clusters that already exist for that SKU in that region
#
# ### Assess impact
# #### 1. Expected sales
# For each valid SKU as selected in option (c), for each region, for each missing cluster:
# - Calculate % of sales for the given cluster, in the selected region and category
#   - If CNO % = 0, e.g. MEDIO2 and SPAZIO for Merendine, we exclude those clusters from the proposed listing
#   - **Use  sellout (revenue, volume) and margin; not CNO vendite**
# - For each SKU, region, calculate the total sales (revenue, volume, margin) for each missing cluster
#
# #### 2. On top vs cannibalised
# - Calculate mean loyalty of the products more similar to the selected SKU to define which proportion of sales is cannibalised (if similar products have a low loyalty on average, the SKU analysed will cannibalise more from them)
# - On top = total expected sales per cluster * mean loyalty
# - Cannibalised sales = total expected sales per cluster - on top
#
# #### 3. Top 10 cannibalised
# - Identify SKUs that belong to the same "Gruppo", top 10 by avg monthly quantity and lowest loyalty
# - Calculate cannibalised portion of each cannibalised product
#   - Apply same calculations used in new listing to cannibal bucket
#
# #### 4. Margins and cumulative impact
# - Add margin columns
# - Cumulate columns
#
# #### 5. Prepare output
# - Clean column names

def check_expected_totals(subset2analyse, subset2analyse_red, expected_sales, cluster_shares):
    # Input only has existing clusters; output only has missing clusters
    assert set(subset2analyse['Cluster']) & set(subset2analyse_red['Cluster']) == set()
    assert subset2analyse_red['Cluster'].nunique() + subset2analyse['Cluster'].nunique() == len(cluster2rank_map)
    for share_col, tot_col in share2total_map.items():
        test = subset2analyse_red.merge(
            cluster_shares,
            on=[category_iri, 'Regione', 'Cluster']
            ).fillna(0)
        assert ((
            expected_sales.loc[tot_col] * test[share_col]).values != (
            test[f'new_{tot_col}']).values
            ).sum() == 0

def get_expected_totals(subset2analyse, sku2analyse_meta, region2analyse, clus_reg_sales):
    #######
    # Calculate expected total sales (revenues, volumes, margins) using the CNO
    # shares by cluster for the selected category and region and the totals
    # of the existing clusters
    #######
    subset2analyse_red = subset2analyse[
        [sku_id_meta, category_iri, 'Regione', 'Cluster'
        ] + list(share2total_map.values())]
    # Identify CNO sales (using sellout) and margin shares by cluster for the selected category and region
    cluster_shares = clus_reg_sales.loc[(
        clus_reg_sales[category_iri] == subset2analyse[category_iri].unique()[0]) & (
        clus_reg_sales['Regione']==region2analyse
        ),
        [category_iri, 'Regione', 'Cluster', 'Clus_Help'] + list(share2total_map.keys())]
    #
    subset2analyse_red = subset2analyse_red.merge(
        cluster_shares,
        on = [category_iri, 'Regione', 'Cluster'],
        how = 'outer'
        ).sort_values(
            by = 'Clus_Help',
            ascending = False
        )
    # Sum shares of existing clusters and
    # calculate expected total sales considering existing totals wrt total share of existing clusters
    expected_sales = subset2analyse_red.dropna()[list(share2total_map.keys())].sum()
    expected_sales = pd.Series([x/y if y !=0 else 0 for x,y in
                    zip(subset2analyse_red[list(share2total_map.values())].sum(), expected_sales)])
    expected_sales.index = list(share2total_map.values())
    # Calculate expected total for each cluster using cluster share and exp total for that SKU in that region
    for share_col, tot_col in share2total_map.items():
        subset2analyse_red[f'new_{tot_col}'] = subset2analyse_red[share_col] * expected_sales.loc[tot_col]
    # Keep only subset with missing clusters and expected totals
    subset2analyse_red = subset2analyse_red.loc[(
        subset2analyse_red[sku_id_meta].isna()
        )].drop(
            columns = list(share2total_map.keys()) + list(share2total_map.values())
        )
    subset2analyse_red[sku_id_meta] = subset2analyse_red[sku_id_meta].fillna(sku2analyse_meta[sku_id_meta])
    #print(sku2analyse_meta)
    #print(region2analyse)
    #print(subset2analyse["Cluster"])
    #print(subset2analyse_red["Cluster"])
    # Check results
    check_expected_totals(subset2analyse, subset2analyse_red, expected_sales, cluster_shares)
    # Clean output: change index and column names
    subset2analyse_red = subset2analyse_red.set_index(
        ['Regione', 'Cluster', 'Clus_Help']
        ).drop(
            columns=[sku_id_meta, category_iri]
        )
    return subset2analyse_red


def get_cannibal_bucket(grp_df, lty_df, sales_df, sku2analyse, sku2analyse_meta):
    #######
    # Extract the products most similar to the SKU analysed and their loyalty
    #######
    # Find products similar to the SKU being analysed
    sim_skus = grp_df[grp_df[group_key+" IRI (Focus)"] == sku2analyse_meta[group_key]]
    sim_skus = sim_skus[[sku_id_focus, sku_desc_focus, sku_group, group_key+" IRI (Focus)"]
        ].drop_duplicates()
    #
    if sku2analyse in sim_skus['SKU ID (Focus)'].unique():
        assigned_group = sim_skus.loc[sim_skus['SKU ID (Focus)']==sku2analyse, 'Gruppo'].values[0]
        # Add loyalty data from most similar products and thier sales data in one table
        red_loyalty = lty_df[(
                lty_df[sku_id].isin(sim_skus[sku_id_focus])
            ) & (
                lty_df['Gruppo'] == assigned_group
            )].rename(
                columns={
                    sku_id: sku_id_meta,
                    sku_desc: sku_desc_meta
                }
            ).merge(
                sim_skus[[sku_id_focus, group_key+" IRI (Focus)"]].rename(
                    columns={
                        sku_id_focus: sku_id_meta,
                        group_key+" IRI (Focus)": group_key
                    }),
                on=sku_id_meta,
                how='left'
            ).merge(
                sales_df.rename(
                    columns={'sku_id': sku_id_meta}),
                on=sku_id_meta,
                how='left'
            )
        if red_loyalty['avg_monthly_quantity'].isna().all():
            red_loyalty['quant'] = 1
        else:
            red_loyalty['quant'] = pd.qcut(
                red_loyalty['avg_monthly_quantity'],
                sales_quants,
                labels=False,
                duplicates='drop'
                )
            red_loyalty['quant'] = red_loyalty['quant'].fillna(1)
        #
        # Calculate cannibal bucket
        # Extract cannibalised SKUs
        red_loyalty = red_loyalty.loc[red_loyalty[sku_id_meta]!=sku2analyse]
        cannibal_bucket = red_loyalty.sort_values(
                by = ['quant', 'loyalty'],
                ascending = (False,True)
            #).head(10)[
            )[
                ['Gruppo', sku_id_meta, sku_desc_meta, 'loyalty', group_key, 'quant']
            ]
    else:
        red_loyalty = pd.DataFrame(
            columns = ["Gruppo", "Articolo Radice_COD", "Articolo Radice", "loyalty",
                       "num_trans_item", "num_customer", "avg_trans_cust", "Tipo-Varieta",
                       "num_tx", "tot_amount", "tot_pieces", "tot_amount_nopr", "tot_pieces_nopr",
                       "avg_monthly_revenues", "avg_monthly_quantity", "quant"]
            )
        cannibal_bucket = pd.DataFrame(
            columns = ['Gruppo', 'Articolo Radice_COD', 'Articolo Radice', 'loyalty', 'Tipo-Varieta', 'quant']
            )
    return red_loyalty, cannibal_bucket

def get_bucket_transferrable_sales(bucket, region2analyse, cols_suffix, transfer_factor, missing_clusters, sales_by_sku_reg_clus, sales_by_sku_reg):    #######
    # For the top 10 similar products to the analysed SKU, for the selected region
    # and for each cluster, calculate the following:
    # - monthly sales (revenues, volumes, margins)
    # - monthly transferrable sales
    # - monthly total by cannibalised SKU - region
    #######
    # Add sales of cannibalised SKUs increasing granularity from SKU to SKU, cluster and region
    bucket = bucket.merge(
        sales_by_sku_reg_clus.loc[
            (sales_by_sku_reg_clus['Cluster'].isin(cluster2rank_map.keys())) &
            (sales_by_sku_reg_clus['Regione'] == region2analyse) &
            (sales_by_sku_reg_clus['total_sellout_revenues'] > 0),
            [
            'Articolo Radice_COD', 'Regione', 'Cluster', group_key,
            'total_sellout_revenues', 'total_sellout_volume',
            'total_margin_cost', 'total_margin_sold'
            ]
        ],
        on=[sku_id_meta, group_key]
    )
    # Extract top 10 similar products per region
    subs2keep_top10 = bucket[
        [sku_id_meta, 'Regione', 'loyalty', 'quant']
        ].drop_duplicates(
        ).sort_values(
            by = ['quant', 'loyalty'],
            ascending = (False, True)
        ).head(max_subs_to_keep
        )[sku_id_meta].tolist()
    bucket = bucket.loc[bucket[sku_id_meta].isin(subs2keep_top10)]
    # Calculate transferrable sales
    for suffix in cols_suffix:
        bucket[f'transferrable_{suffix}'] = transfer_factor * (
            1-bucket['loyalty']
            ) * bucket[f'total_sellout_{suffix}']
    # Calculate total sales in that region by sub
    bucket = bucket.merge(
        sales_by_sku_reg[
              [sku_id_meta, 'Regione', 'total_sellout_revenues', 'total_sellout_volume']
        ].rename(
            columns = {
                'total_sellout_revenues': 'revenues_by_region_sub',
                'total_sellout_volume': 'volume_by_region_sub'
            }
        ),
        on = [sku_id_meta, 'Regione']
        )
    # Keep only non existing clusters
    bucket = bucket.loc[bucket['Cluster'].isin(missing_clusters)]
    #
    return bucket


def adjust_transferred_cannibal_sales(new_sales, bucket, cols_suffix):
    #######
    # For each cluster, check if the amount that can be cannibalised can be covered
    # entirely by the cannibal_bucket; if not, adjust it so that the total transferred amount
    # from the cannibalised products equals the cannibalised amount by the SKU analysed
    #######
    for suffix in cols_suffix:
        bucket[f'transferred_{suffix}'] = np.nan
    #
    region_idx_pos = 0
    cluster_idx_pos = 1
    #
    for mux in new_sales.index:
        region = mux[region_idx_pos]
        clus = mux[cluster_idx_pos]
        subset = new_sales.loc[mux]
        #
        if subset.loc['new_revenues']>0:
            subset_bucket = bucket.loc[(
                bucket['Cluster']==clus) & (
                bucket['Regione']==region
                )]
            ## Adjust transferred sales from cannibalised products where the tot transferrable
            # is more than the tot amount that can be cannibalised
            for suffix in cols_suffix:
                if subset_bucket[f'transferrable_{suffix}'].sum() > subset[f'cannibal_{suffix}']:
                    bucket.loc[(
                            bucket['Cluster']==clus) & (
                            bucket['Regione']==region
                        ),
                        f'transferred_{suffix}'] = subset[f'cannibal_{suffix}'] * (
                            subset_bucket[f'transferrable_{suffix}'] /
                                subset_bucket[f'transferrable_{suffix}'].sum()
                            )
                else:
                    bucket.loc[(
                        bucket['Cluster']==clus) & (
                        bucket['Regione']==region
                        ),
                        f'transferred_{suffix}'] = subset_bucket[f'transferrable_{suffix}']
                    new_sales.loc[mux, f'on_top_{suffix}'] = subset[f'on_top_{suffix}'] + (
                            subset[f'cannibal_{suffix}'] -
                            subset_bucket[f'transferrable_{suffix}'].sum()
                        )
                    new_sales.loc[mux, f'cannibal_{suffix}'] = new_sales.loc[mux, f'new_{suffix}'] -\
                        new_sales.loc[mux, f'on_top_{suffix}']
                bucket[f'transferred_{suffix}'] = bucket[f'transferred_{suffix}'].fillna(0)
    ## Compute cannibalised ratio
    # Ratio cannibalised by SKU analysed
    new_sales['cannibalised_ratio'] = (new_sales['cannibal_revenues'] / new_sales['new_revenues']
        ).fillna(0)
    # Share of the amount "stolen" from SKU analysed for the cannibalised products in the same cluster
    bucket['cannibalised_share_on_sub'] = (bucket['transferred_revenues'] / \
        bucket.groupby(
            ['Regione', 'Cluster']
        )['transferred_revenues'].transform("sum")).fillna(0)
    # Check results
    #for suffix in cols_suffix:
    #    assert round(bucket[f'transferred_{suffix}'].sum(),5)==\
    #        round(new_sales[f'cannibal_{suffix}'].sum(), 5)
    #
    assert sum(
        (round(bucket.groupby(
            ['Regione', 'Cluster']
        )['cannibalised_share_on_sub'].sum(),3)!=1)
        &
        (round(bucket.groupby(
            ['Regione', 'Cluster']
        )['cannibalised_share_on_sub'].sum(),3)!=0)
        ) == 0
    return new_sales, bucket


# def get_transferred_margin_by_sub(row):
#     if row['total_sellout_revenues'] < 0.5:
#         margin_sold_incidence_sub = 0
#         margin_cost_incidence_sub = 0
#     else:
#         margin_sold_incidence_sub = row['total_margin_sold'] / row['total_sellout_revenues']
#         margin_cost_incidence_sub = row['total_margin_cost'] / row['total_sellout_revenues']
#     #
#     transferred_margin_sold = row['transferred_revenues'] * margin_sold_incidence_sub
#     transferred_margin_cost = row['transferred_revenues'] * margin_cost_incidence_sub
#     transferred_margin = transferred_margin_sold - transferred_margin_cost
#
#     return transferred_margin


def add_missing_clusters(df, lvl_of_detail_cols, clusters_to_include, fillna=True):
    mux_values_all = [
        df[col].unique() if col!='Cluster' else clusters_to_include
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


def run_sku_region_listing(subset2analyse, sku2analyse, region2analyse, on_top_factor, col_rename_dict,
                        df_groups, df_loyalty, sku_sold, clus_reg_sales, sales_by_sku_reg_clus, sales_by_sku_reg):
    ###########
    # Run the listing analysis for the selected SKU in the selected region,
    # calculating the expected sales and the distribution of net new sales("on-top") vs
    # cannibalised sales from the 10 most similar products
    ###########
    ######
    # 1. Identify missing clusters in the selected region for the SKU analysed
    ######
    # Subset at SKU level (no cluster granularity)
    sku2analyse_meta = subset2analyse[
        [sku_id_meta, sku_desc_meta, 'EAN', 'Prodotto', 'Regione',
         category_iri, category_meta, group_key,
        'Settore', 'Marca', 'Fornitore', sku_score+'_by_sku_reg']
        ].drop_duplicates(
        ).iloc[0]
    # add yearly sales of SKU on existing clusters in the selected region
    sku2analyse_meta = pd.concat([sku2analyse_meta, subset2analyse.agg({
            'revenues': "sum",
            'volume': "sum",
            'Margine': "sum",
            'Margine pct': "mean"
            })])
    # Expected new totals for missing clusters (existing clusters not shown)
    clus_new_sales = get_expected_totals(subset2analyse, sku2analyse_meta, region2analyse, clus_reg_sales)
    clus_new_sales = clus_new_sales.sort_index(level=2)
    missing_clusters = clus_new_sales.index.unique(level='Cluster').tolist()
    ## Here, only proceed if there are sales in that cluster/region for that category
    if len(missing_clusters)>0 and clus_new_sales['new_revenues'].sum()>0:
        ######
        # 2. Build cannibal bucket
        ######
        # Find products similar to the SKU being analysed
        red_loyalty, cannibal_bucket = get_cannibal_bucket(
            df_groups, df_loyalty, sku_sold, sku2analyse, sku2analyse_meta
            )
        ## FIXME (Aug 2023): WHY DUPLICATED CONTENT HERE SOMETIMES!?!
        ## For 'CARNI_SURGELATE' product 2793375.0 is in two groups and similar to Focus 5122780.0... investigate!!
        red_loyalty = red_loyalty.drop_duplicates().reset_index(drop=True)
        cannibal_bucket = cannibal_bucket.drop_duplicates().reset_index(drop=True)
        ######
        # 3. On top vs cannibalised sales
        ######
        # Calculate the transferrable sales amount for each cannibalised product, in each region
        cannibal_bucket = get_bucket_transferrable_sales(
            cannibal_bucket, region2analyse, ['revenues', 'volume'], transfer_factor, missing_clusters,
            sales_by_sku_reg_clus, sales_by_sku_reg  # <-- Aggiungi queste due
            )
        # Calculate mean loyalty on top 10 similar products of the same group
        mean_loyalty = 0
        if red_loyalty.shape[0] > 0:
            mean_loyalty = red_loyalty.groupby(sku_id_meta)['loyalty'].mean().mean()
        if mean_loyalty == 0:
            on_top_factor = 0
        #
        # Calculate net new sales (on top sales) and cannibalised sales
        for col in [c for c in clus_new_sales.columns if 'new_' in c and 'margin' not in c]:
            new_col = col.replace('new_', '')
            clus_new_sales[f'on_top_{new_col}'] = clus_new_sales[col] * \
                max(mean_loyalty, on_top_factor)
            clus_new_sales[f'cannibal_{new_col}'] = clus_new_sales[col] - clus_new_sales[f'on_top_{new_col}']
        #
        # Adjust the transferrable amount for the total amount that the SKU analysed can cannibalise
        clus_new_sales, cannibal_bucket = adjust_transferred_cannibal_sales(
            clus_new_sales, cannibal_bucket, ['revenues', 'volume'])
        ######
        # 4. Calculate margins
        ######
        # Remove clusters with no expected sales
        clus_new_sales = clus_new_sales.loc[clus_new_sales['new_revenues']>0]
        if cannibal_bucket.shape[0]>0:
            cannibal_bucket['total_margin'] = cannibal_bucket['total_margin_sold'] - \
                cannibal_bucket['total_margin_cost']
            cannibal_bucket['total_margin_pct'] = cannibal_bucket.apply(
                lambda row: 0 if row['total_margin_sold']==0 else (
                    row['total_margin'] / row['total_margin_sold']),
                axis = 1
                )
            # cannibal_bucket['transferred_margin'] = cannibal_bucket.apply(
            #     lambda row: get_transferred_margin_by_sub(row),
            #     axis=1)

            # Usa np.where per la condizione if/else su tutta la colonna
            margin_sold_incidence = np.where(
                cannibal_bucket['total_sellout_revenues'] < 0.5,
                0,
                cannibal_bucket['total_margin_sold'] / cannibal_bucket['total_sellout_revenues']
            )
            margin_cost_incidence = np.where(
                cannibal_bucket['total_sellout_revenues'] < 0.5,
                0,
                cannibal_bucket['total_margin_cost'] / cannibal_bucket['total_sellout_revenues']
            )

            # Esegui i calcoli su intere colonne
            cannibal_bucket['transferred_margin'] = cannibal_bucket['transferred_revenues'] * (
                        margin_sold_incidence - margin_cost_incidence)


            # Add total margin transferred from cannibalised products
            clus_new_sales = clus_new_sales.join(
                cannibal_bucket.groupby(['Regione', 'Cluster']
                )['transferred_margin'].sum(),
                how = 'left'
                )
        else:
            clus_new_sales['transferred_margin'] = 0
        #
        # Calculate total and lost margin for each SKU at region and cluster level
        clus_new_sales['new_margin'] = clus_new_sales['new_margin_sold'] - \
            clus_new_sales['new_margin_cost']
        clus_new_sales['new_margin_pct'] = clus_new_sales['new_margin'] / \
            clus_new_sales['new_margin_sold']
        clus_new_sales = clus_new_sales.fillna(0)
        clus_new_sales['on_top_margin'] = clus_new_sales['new_margin'] - \
            clus_new_sales['transferred_margin']
        ######
        # 5. Calculate cumulative impact
        ######
        # Add cumulative columns for net new sales
        for c in ['on_top_revenues', 'on_top_volume', 'on_top_margin']:
            clus_new_sales[c+'_cumul'] = clus_new_sales[c].cumsum()
        if cannibal_bucket.shape[0]>0:
            #for suffix in ['revenues', 'volume']:
            #    assert round(cannibal_bucket[f'transferred_{suffix}'].sum(),5
            #      ) == round(clus_new_sales[f'cannibal_{suffix}'].sum(),5
            #        )
            # Add missing clusters (the ones that appear in clus_new_sales)
            cannibal_bucket = add_missing_clusters(
                cannibal_bucket,
                lvl_of_detail_cols = [sku_id_meta, 'Regione', 'Cluster'],
                clusters_to_include = clus_new_sales.index.get_level_values('Cluster').values,
                fillna=False
                )
            # Fill missing values - categorical
            cannibal_bucket_fillna_values = cannibal_bucket.dropna(subset=['Articolo Radice']).groupby(
                [sku_id_meta, 'Regione'], as_index=False
                ).agg({
                    'Articolo Radice': "min",
                    'Gruppo': "min",
                    'loyalty': "min",
                    group_key: "min",
                    'revenues_by_region_sub': "min",
                    'volume_by_region_sub': "min"
                })
            cannibal_bucket = cannibal_bucket.drop(
                    columns=['Articolo Radice', 'Gruppo', 'loyalty', group_key,
                             'revenues_by_region_sub', 'volume_by_region_sub']
                ).merge(
                    cannibal_bucket_fillna_values,
                    on=[sku_id_meta, 'Regione']
                )
            # Fill missing values - numerical
            cannibal_bucket = cannibal_bucket.fillna(0)
            # Add cumulative columns for transferred revenues
            cannibal_bucket['Clus_Help'] = cannibal_bucket['Cluster'].map(pd.Series(cluster2rank_map))
            cannibal_bucket = cannibal_bucket.sort_values(
                by = [sku_id_meta, 'Regione', 'Clus_Help'],
                ascending = True
                )
            for c in ['transferred_revenues', 'transferred_volume', 'transferred_margin']:
                cannibal_bucket[c+'_cumul'] = cannibal_bucket.groupby([sku_id_meta, 'Regione'])[c].cumsum()
            cannibal_bucket['transferred_revenues_cumul_by_cluster'] = cannibal_bucket.groupby(
                    ['Regione', 'Cluster']
                )['transferred_revenues_cumul'].transform("sum")
            cannibal_bucket['cannibalised_share_on_sub_cumul'] = cannibal_bucket.apply(
                lambda row: 0 if row['transferred_revenues_cumul_by_cluster'] == 0 else (
                    row['transferred_revenues_cumul'] / row['transferred_revenues_cumul_by_cluster']),
                    axis = 1
                )
            cannibal_bucket = cannibal_bucket.drop(columns='transferred_revenues_cumul_by_cluster')
            cannibal_bucket = cannibal_bucket[cannibal_bucket['cannibalised_share_on_sub_cumul']>0]
            # checks
            assert sum(round(
                cannibal_bucket.groupby(['Cluster'])['cannibalised_share_on_sub_cumul'].sum(),
                ) != 1) == 0
            for metric in ['revenues', 'volume']:
                assert 0 == cannibal_bucket.groupby('Cluster')[[f'transferred_{metric}']].sum().join(
                    clus_new_sales[f'cannibal_{metric}']
                    ).diff(axis=1).iloc[:,1].round(2).sum()
        #
        ######
        # 6. Prepare output
        ######
        # Add meta columns
        clus_new_sales = clus_new_sales.reset_index()
        cannibal_bucket = cannibal_bucket.rename(columns={
            sku_id_meta: sku_id_meta+'_cannibalised',
            sku_desc_meta: sku_desc_meta+'_cannibalised'
            })
        for c in sku2analyse_meta.index:
            if c not in ['Regione']:
                clus_new_sales[c] = sku2analyse_meta.loc[c]
            if c not in ['Regione', 'Marca', 'Fornitore', group_key, sku_score+'_by_sku_reg',
                'revenues', 'volume', 'Margine', 'Margine pct']:
                cannibal_bucket[c] = sku2analyse_meta.loc[c]
        clus_new_sales['Tipo'] = clus_new_sales[group_key].apply(lambda x: x.split(' / ')[0])
        clus_new_sales['Varietà'] = clus_new_sales[group_key].apply(lambda x: x.split(' / ')[1])
    else:
        clus_new_sales = pd.DataFrame()
        cannibal_bucket = pd.DataFrame()
    #
    return clus_new_sales, cannibal_bucket



cat_lookup = smart_load_to_pd(fname=lookup_file, sep=",", decimal= ".", encoding="latin-1")
cat_lookup = cat_lookup[cat_lookup["sales_2y"] > 0]
cat_lookup = cat_lookup.sort_values(by="sales_2y")
#cat_lookup["category"] = cat_lookup.category.replace("(_)+", "_", regex=True)

nosales_cat = []
empty_cat = []
nogrp_cat = []
noloy_cat = []
augm_debug = []

# 4958069.0 - Toscana
def fix_categ(categ):
    hlpr = categ.drop_duplicates().to_list()
    in_assort = [cc for cc in hlpr if cc != "Non in assortimento IRI"]
    if (('Non in assortimento IRI' not in hlpr) and (len(hlpr)>1)) or (('Non in assortimento IRI' in hlpr) and (len(hlpr)>2)):
        #print("ERROR IN METADATA FIX!!")
        print(f"⚠️ ANOMALIA DATI (METADATA FIX): Trovate categorie multiple per lo stesso SKU/Regione: {hlpr}")
    if ('Non in assortimento IRI' in hlpr) and (len(hlpr)>1):
        categ[categ=='Non in assortimento IRI']=in_assort[0]
        print(f"AUTOFIX su categorie multiple per lo stesso SKU/Regione: {hlpr}")
    return categ


def process_single_category(cat: str):

    #print("Running augmentation for category: " + str(cat))

    # print("=======================")
    # print("SCRIPT 6 - augmentation")
    # print("=======================")

    start_augm = time.time()
    cat_out = workarea_path + re.sub("/", "", str(cat))
    hlp_out = workarea_path + re.sub("/", "", str(cat)) + "/"
    supp_out = workarea_path + re.sub("/", "", str(cat)) + "/"
    if not os.path.exists(cat_out):
        os.makedirs(cat_out)
    cat_out = cat_out + "/"
    cat_code = cat_lookup[cat_lookup["category"] == str(cat)]["cat_code"].values[0]
    cat_aumento = cat_out + 'aumento' + '_' + str(cat_code).zfill(3) +'.xlsx'
    # ## Import data
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
    if not os.path.exists(cat_sku_sold) or not os.path.exists(cat_sku_clus_reg) \
            or not os.path.exists(cat_clus_reg_sales) or not os.path.exists(cat_sales_sku_reg_clus):
        nosales_cat.append(cat)
        return
    print("augmentation: step 1 - import")
    # Results of hierarchical similarity and clustering
    df_groups = pd.read_csv(cat_group, sep=';', decimal=',', encoding='latin-1')
    df_groups = df_groups.astype({sku_id_focus: float, sku_id_sub: float})
    # Results of loyalty
    df_loyalty = pd.read_csv(cat_loyal, sep=';', decimal=',', encoding='latin-1')
    df_loyalty = df_loyalty.astype({sku_id: float})
    df_loyalty = df_loyalty.drop_duplicates()
    df_loyalty = df_loyalty.groupby([sku_group, sku_id, sku_desc]).mean().reset_index()
    # Sales from transaction data
    sku_sold = pd.read_csv(cat_sku_sold, sep=";", decimal= ",", encoding='latin-1')
    sku_sold = sku_sold.astype({'sku_id': float})
    # FIXMEEE: Hack to compensate dupes in metadata!!
    #aa=sku_sold[sku_sold["sku_id"]==4990401]
    #aa
    sku_sold = sku_sold.groupby(["sku_id"]).agg({cc:"mean" for cc in sku_sold.columns if cc != "sku_id"}).reset_index()
    # Metadata at SKU, region, cluster level
    sku_clus_reg_meta = pd.read_csv(cat_sku_clus_reg, sep=';', decimal= ",", encoding='latin-1', low_memory=False)
    #print(sku_clus_reg_meta.shape) #507,056
    # FIXMEEE: Hack to compensate error in metadata (duplicated sku_score)!!
    #aa=sku_clus_reg_meta[(sku_clus_reg_meta["Articolo Radice_COD"]==49680080) & (sku_clus_reg_meta["Regione"]== "Sardegna")]
    #aa[["Articolo Radice_COD", "Regione", "Cluster", sku_score, 'Sellout Importo']]
    #aa=sku_clus_reg_meta[(sku_clus_reg_meta["Articolo Radice_COD"]==4968080) & (sku_clus_reg_meta["Regione"]== "Emilia-Romagna")]
    #aa[["Articolo Radice_COD", "Regione", "Cluster", sku_score, 'Sellout Importo']]
    scr_meta_p1 = sku_clus_reg_meta[~sku_clus_reg_meta[sku_id_meta].isna() & (sku_clus_reg_meta[sku_id_meta] != 0)].copy()
    scr_meta_p1["min_score"] = scr_meta_p1.groupby([category_meta, sku_id_meta, "Regione", "Cluster", sku_status])[sku_score].transform("min").fillna(0)
    scr_meta_p1["cum_count"] = scr_meta_p1.groupby([category_meta, sku_id_meta, "Regione", "Cluster", sku_status]).cumcount().fillna(0)
    scr_meta_p1 = scr_meta_p1[(scr_meta_p1[sku_score] == scr_meta_p1["min_score"]) & (scr_meta_p1["cum_count"] == 0)]
    scr_meta_p1 = scr_meta_p1.drop(["min_score", "cum_count"], axis=1)
    scr_meta_p2 = sku_clus_reg_meta[sku_clus_reg_meta[sku_id_meta].isna() | (sku_clus_reg_meta[sku_id_meta] == 0)].copy()
    scr_meta_p2["min_score"] = scr_meta_p2.groupby(["EAN", "Regione"])[sku_score].transform("min")
    scr_meta_p2["cum_count"] = scr_meta_p2.groupby(["EAN", "Regione"]).cumcount()
    scr_meta_p2 = scr_meta_p2[(scr_meta_p2[sku_score] == scr_meta_p2["min_score"]) & (scr_meta_p2["cum_count"] == 0)]
    scr_meta_p2 = scr_meta_p2.drop(["min_score", "cum_count"], axis=1)
    sku_clus_reg_meta = pd.concat([scr_meta_p1, scr_meta_p2]).reset_index(drop=True)
    ## FIXME (Aug 2023): there can be mismatched IRI categories for a common SKU/Region in different clusters!?!
    sku_clus_reg_meta['Categoria'] = sku_clus_reg_meta.groupby([sku_id_meta, "Regione"])["Categoria"].transform(
        lambda x: fix_categ(x) 
    )
    # sku_clus_reg_meta.loc[(sku_clus_reg_meta[sku_id_meta]==sku2analyse),['Regione', 'Cluster', 'Categoria', 'CategFixed']]
    # Add margins
    sku_clus_reg_meta['Margine'] = sku_clus_reg_meta['Margine Venduto'] - sku_clus_reg_meta['Margine Costo Netto']
    sku_clus_reg_meta['Margine pct'] = sku_clus_reg_meta.apply(
        lambda row: 0 if row['Margine Venduto']==0 else (row['Margine'] / row['Margine Venduto']),
        axis = 1
        )
    # CNO sales shares by category, region, cluster
    clus_reg_sales = pd.read_csv(cat_clus_reg_sales, sep=';', decimal= ",", encoding='latin-1')
    # CNO sales from metadata
    sales_by_sku_reg_clus = pd.read_csv(cat_sales_sku_reg_clus, sep=";", decimal= ",", encoding='latin-1')
    # Sales from metadata at sku and region level (only valid clusters)
    sales_by_sku_reg = sales_by_sku_reg_clus.loc[
        sales_by_sku_reg_clus['Cluster'].isin(cluster2rank_map.keys())
        ].groupby(
        [sku_id_meta, 'Regione'],
        as_index = False
        )[[
            'total_sellout_revenues', 'total_sellout_volume',
            'total_margin_cost', 'total_margin_sold']
        ].sum()
    print("augmentation: step 2 - select products")
    # ## 1. Identify existing SKUs eligible for listing
    # Identify existing CNO products with:
    # category CNO = category to analyse
    # status = active
    # valid clusters
    # tipo-varietà = one of the values from the cluster file results
    # average priorità assortimento of that SKU in the selected region >= min threshold (3)
    sku_clus_reg_meta = sku_clus_reg_meta.loc[(
        sku_clus_reg_meta[category_meta]==re.sub("_", " ", str(cat))) & (
        sku_clus_reg_meta[sku_status]=='Attivo') & (
        sku_clus_reg_meta['Cluster'].isin(cluster2rank_map.keys())) & (
        sku_clus_reg_meta[group_key].isin(df_groups[sku_gkey_focus].unique().tolist()))
        ]
    if sku_clus_reg_meta.shape[0] == 0:
        empty_cat.append(cat)
        return
    # Compute average priorità assortimento by SKU and region
    sku_clus_reg_meta[f"{sku_score}_by_sku_reg"] = sku_clus_reg_meta.groupby(
        [sku_id_meta, 'Regione']
        )[sku_score].transform("mean")
    # Exclude SKU-regions with average score below threshold
    sku_clus_reg_meta = sku_clus_reg_meta[sku_clus_reg_meta[sku_score+'_by_sku_reg']>=min_sku_score]
    #print(sku_clus_reg_meta.shape) #823
    # Identify all unique SKUs
    sku_list = sku_clus_reg_meta[sku_id_meta].unique().tolist()
    ## Run listing analysis for the eligible SKUs
    list1 = []
    list2 = []
    print("augmentation: step 3 - compute impact of augmentation")
    print("steps: "+str(len(sku_list)))
    for ii, sku2analyse in enumerate(sku_list):
        # if ii % 50==0:
        #     print("step: " + str(ii))
        # Identify all available regions for the selected SKU
        regions = sku_clus_reg_meta.loc[
            sku_clus_reg_meta[sku_id_meta]==sku2analyse,
            'Regione'].unique().tolist()
        for region2analyse in regions:
            # Identify metadata subset for the selected SKU and region
            subset2analyse = sku_clus_reg_meta.loc[(
                sku_clus_reg_meta[sku_id_meta]==sku2analyse) & (
                sku_clus_reg_meta['Regione'] == region2analyse
                )].rename(
                    columns = col_rename_dict
                )
            ### FIXMEEEE - it breaks here!
            # Run listing analysis for the selected SKU and region
            clus_new_sales, cannibal_bucket = run_sku_region_listing(
                subset2analyse,
                sku2analyse,
                region2analyse,
                on_top_factor,
                col_rename_dict,
                df_groups, df_loyalty, sku_sold, clus_reg_sales,
                sales_by_sku_reg_clus, sales_by_sku_reg  # <-- Aggiungi queste due
            )
            list1.append(clus_new_sales)
            list2.append(cannibal_bucket)
    list1 = pd.concat(list1).reset_index(drop=True)

    # CEGIL
    # list2 = pd.concat(list2).reset_index(drop=True)
    # 1. Create a new list that excludes any empty DataFrames
    # 2. Check if the new list has anything in it before concatenating
    non_empty_list = [df for df in list2 if not df.empty]
    if non_empty_list:
        list2 = pd.concat(non_empty_list).reset_index(drop=True)
    else:
        # If all DataFrames were empty, create an empty DataFrame to avoid errors
        list2 = pd.DataFrame()

    augm_debug.append(pd.DataFrame(
        { "source":"old", "cat":cat, "cat_code":cat_code,
        "new_sales":list1.shape[0],
        "new_sku":list1[sku_id_meta].nunique() if len(list1) else 0,
        "new_tot":list1['new_revenues'].sum() if len(list1) else 0,
        "cann_sales":list2.shape[0],
        "cann_sku":list2[sku_id_meta].nunique() if len(list2) else 0,
        "cann_tot":list2['total_sellout_revenues'].sum() if len(list2) else 0
        },
        index=[cat_code]
    ))
    if list1.shape[0]:
        # Rename columns
        list1_cols_rename_dict = {
            'EAN': 'EAN',
            sku_id_meta: 'Articolo Radice COD',
            'Prodotto': 'Prodotto (original)',
            sku_desc_meta: 'Prodotto',
            'Settore': 'Settore',
            category_iri: 'Categoria IRI',
            'Categoria Merceologica': 'Categoria CNO',
            'Tipo-Varieta': 'Tipo-Varietà',
            'Tipo': 'Tipo',
            'Varietà': 'Varietà',
            'Marca': 'Marca',
            'Fornitore': 'Fornitore',
            'Regione': 'Regione',
            'Cluster': 'Cluster',
            'Clus_Help': 'Cluster Rank',
            sku_score+'_by_sku_reg': 'Priorità assortimento (media per regione)',
            'cannibalised_ratio': 'Tasso di cannibalizzazione',
            'revenues': 'Fatturato annuale',
            'volume': 'Volumi annuali',
            'Margine': 'Margine annuale',
            'Margine pct': 'Margine annuale pct',
            'new_revenues': 'Fatturato annuale atteso (singolo)',
            'on_top_revenues': 'Fatturato annuale atteso netto (singolo)',
            'on_top_revenues_cumul': 'Fatturato annuale atteso netto (cumulato)',
            'cannibal_revenues': 'Fatturato annuale atteso cannibalizzato (singolo)',
            'new_volume': 'Volumi annuali attesi (singolo)',
            'on_top_volume': 'Volumi annuali attesi netti (singolo)',
            'on_top_volume_cumul': 'Volumi annuali attesi netti (cumulato)',
            'cannibal_volume': 'Volumi annuali attesi cannibalizzati (singolo)',
            'new_margin': 'Margine annuale atteso (singolo)',
            'on_top_margin': 'Margine annuale atteso netto (singolo)',
            'on_top_margin_cumul': 'Margine annuale atteso netto (cumulato)',
            'transferred_margin': 'Margine annuale atteso cannibalizzato (singolo)',
            'new_margin_pct': 'Margine pct annuale atteso (singolo)',
            #'new_margin_pct_cumul': 'Margine pct annuale atteso (cumulato)',
            #'on_top_margin_pct': 'Margine pct annuale atteso netto (singolo)',
            #'on_top_margin_cumul_pct': 'Margine pct annuale atteso netto (cumulato)',
            #'cannibal_margin_pct': 'Margine pct annuale atteso cannibalizzato (singolo)'
            }
        list1 = list1.rename(columns=list1_cols_rename_dict)
        # Reorder columns
        list1 = list1[list(list1_cols_rename_dict.values())]
        print("output 1 shape: ", list1.shape)
    if list2.shape[0]:
        # Rename columns
        list2_cols_rename_dict = {
            'EAN': 'EAN',
            sku_id_meta: 'Articolo Radice COD',
            'Prodotto': 'Prodotto (original)',
            sku_desc_meta: 'Prodotto',
            'Settore': 'Settore',
            category_iri: 'Categoria IRI',
            'Categoria Merceologica': 'Categoria CNO',
            'Tipo-Varieta': 'Tipo-Varietà',
            'Gruppo': 'Gruppo',
            sku_id_meta+'_cannibalised': 'Articolo Radice COD (Cannibalizzato)',
            sku_desc_meta+'_cannibalised': 'Prodotto cannibalizzato',
            #sku_score: 'Priorità assortimento',
            'Regione': 'Regione',
            'Cluster': 'Cluster',
            'cannibalised_share_on_sub': "Proporzione 'rubata'",
            'cannibalised_share_on_sub_cumul': "Proporzione 'rubata' (cumulato)",
            'total_sellout_revenues': 'Fatturato annuale (Cannibalizzato)',
            'total_sellout_volume': 'Volumi annuali (Cannibalizzato)',
            'total_margin': 'Margine annuale (Cannibalizzato)',
            'total_margin_pct': 'Margine pct annuale (Cannibalizzato)',
            'revenues_by_region_sub': 'Fatturato annuale per regione',
            'volume_by_region_sub': 'Volumi annuali per regione',
            'transferred_revenues': "Fatturato annuale 'rubato' dal nuovo SKU",
            'transferred_volume': "Volumi annuali 'rubati' dal nuovo SKU",
            'transferred_margin': "Margine annuale 'rubato' dal nuovo SKU",
            'transferred_revenues_cumul': "Fatturato annuale 'rubato' dal nuovo SKU (cumulato)",
            'transferred_volume_cumul': "Volumi annuali 'rubati' dal nuovo SKU (cumulato)",
            'transferred_margin_cumul': "Margine annuale 'rubato' dal nuovo SKU (cumulato)"
            }
        list2 = list2.rename(columns=list2_cols_rename_dict)
        # Reorder columns
        list2 = list2[list(list2_cols_rename_dict.values())]
        print("output 2 shape: ", list2.shape)
    if (list2.shape[0]==0) or (list2.shape[0]==0):
        return
    list1["EAN"] = list1["EAN"].astype(str)
    list2["EAN"] = list2["EAN"].astype(str)
    # Save output for dashboard
    #if write_out:
    #    with pd.ExcelWriter(cat_aumento) as writer:
    #        list1.to_excel(writer, sheet_name="choose sku-cluster to list", index=False)
    #        list2.to_excel(writer, sheet_name="top 10 cannibalised skus", index=False)
    if write_out:
        list1.to_parquet(re.sub(".xlsx$", "_sheet1.parquet", cat_aumento), index=False)
        list2.to_parquet(re.sub(".xlsx$", "_sheet2.parquet", cat_aumento), index=False)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("ERRORE: Nessuna categoria fornita.")
        print("Uso: python metadata.py <nome_categoria>")
        sys.exit(1)  # Esce con un codice di errore

    current_category = sys.argv[1]

    process_single_category(current_category)

    sys.exit(0)  # Esce indicando successo
