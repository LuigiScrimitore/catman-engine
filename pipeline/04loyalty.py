# # Loyalty
import gc
import sys

import numpy as np
import pandas as pd
import re
import os
import time
import utils as utl

# config_file = "./config/configurazioni.yaml"
# with open(config_file, "r") as f:
#     config = yaml.safe_load(f)
config = utl.get_Config()

input_path = config['paths']['input_path']
sales_path = config['paths']['sales_path']
workarea_path = config['paths']['workarea_path']

# files to process
sku_filt_file = config['files']['sku_filter'] #sku_pdv_meta.csv
lookup_file = input_path + config['files']['lookup_cats']

# log_file = config['files'].get('logging_file')
# if log_file is None:
#     log_file = "log_Modulo3.txt"

# misc options
filter_promo = config['parameters']['tx_filter_promo']
min_count = config['parameters']['loy_min_count']
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
sku_id = lista_colonne['sku_id']
sku_desc = lista_colonne['sku_desc']
cust_id = lista_colonne['cust_id']
tx_date = lista_colonne['tx_date']
sku_status = lista_colonne['sku_status']
amount = lista_colonne['amount']
qty = lista_colonne['qty']
fidelity = lista_colonne['fidelity']
promo = lista_colonne['promo']
sku_group = lista_colonne['sku_group']
sku_id_focus = lista_colonne['sku_id_focus']
sku_id_sub = lista_colonne['sku_id_sub']
sku_gkey_focus = lista_colonne['sku_gkey_focus']
sku_gkey_sub = lista_colonne['sku_gkey_sub']
sku_loyalty = lista_colonne['loyalty']

# load_filtered_sales_parquet e smart_load_to_pd sono state centralizzate
# in utils/sales_loader.py e sono accessibili tramite utl.smart_load_to_pd
smart_load_to_pd = utl.smart_load_to_pd


def get_customers_without_fidelity(df_buy):
    # Check customers with and without fidelity flag
    cust_no_fidelity = set(list(df_buy[df_buy[fidelity]==0][cust_id].unique()))
    cust_with_fidelity = set(list(df_buy[df_buy[fidelity]==1][cust_id].unique()))
    cust_never_fidelity = cust_no_fidelity-cust_with_fidelity
    return cust_never_fidelity

## here we do not need the transaction id...
def clean_tx_data_red(df_tx):
    # Clean data
    df_tx[sku_id] = df_tx[sku_id].astype(str)
    df_tx[tx_date] = pd.to_datetime(df_tx[tx_date].astype(str), format='%Y-%m-%d')
    #
    # Filter invalid transactions
    df_tx = df_tx[df_tx[cust_id]!=-1]
    customers_without_fidelity = get_customers_without_fidelity(df_tx)
    df_tx[qty]=df_tx[qty].astype(float)
    df_tx[amount]=df_tx[amount].astype(float)
    df_tx = df_tx[(df_tx[qty]>0) &
                  (df_tx[amount]>0) &
                  (~df_tx[cust_id].isin(customers_without_fidelity)) # customers no fidelity
                 ]
    return df_tx


# ## Compute loyalty for all groups at once, through ```groupby```
def compute_loyalty(df_sku, min_buy):
    # customers with enough transactions in this group
    ids_tmp = df_sku.groupby(
            [sku_group, cust_id]
        ).size(
        ).reset_index(
        ).rename(
            columns={0: 'num_trans_cust'}
        )
    ids_tmp['key'] = ids_tmp[sku_group].astype(str) + "_" + ids_tmp[cust_id].astype(str)
    ids_tmp = ids_tmp[ids_tmp['num_trans_cust'] > min_buy]
    #
    # transaction of such customers in this group
    #
    sku_wip = df_sku.merge(ids_tmp[[sku_group, cust_id, "num_trans_cust"]], on=[sku_group, cust_id], how="inner").sort_values(
            by=[sku_group, cust_id, tx_date],
            axis=0,
            ascending=True
        )
    sku_wip['num_trans_item'] = sku_wip[sku_id].map(sku_wip[sku_id].value_counts())
    sku_wip['next_'+sku_id] = sku_wip.groupby([sku_group, cust_id])[sku_id].shift(-1)
    sku_wip['keep_article'] = (sku_wip[sku_id]==sku_wip['next_'+sku_id])
    # check manualmente flag True se diversi ma stessa transazione!?!
    if sku_wip.shape[0] == 0:
        # if no customers has enough transactions among items of any group,
        # let us create an empty df with the necessary columns
        sku_loyal = sku_wip
        sku_loyal["loyalty"] = 0
        sku_loyal["num_customer"] = 0
        sku_loyal["avg_trans_cust"] = 0
        sku_loyal = sku_loyal[[sku_group, sku_id, "loyalty", "num_customer", "avg_trans_cust", "num_trans_item"]]
    else:
        # otherwise compute the appropriate numbers
        grp_bckt_size = 50000
        ngroups = sku_wip[[sku_group, cust_id, sku_id]].drop_duplicates().shape[0]
        if ngroups > grp_bckt_size * 2:
            loyal_list = []
            sku_wip["cust_grp"] = sku_wip.groupby([sku_group, cust_id, sku_id]).ngroup() // grp_bckt_size
            print(f"steps: {sku_wip['cust_grp'].max()+1}")
            for this_grp in range(sku_wip["cust_grp"].max()+1):
                #print(this_grp)
                #aa=time.time()
                sku_red = sku_wip[sku_wip.cust_grp == this_grp]
                sku_keep = sku_red.groupby(
                             [sku_group, cust_id, sku_id]
                              ).agg(
                              num_customer=(cust_id, pd.Series.nunique),
                              sum_trans_cust=('num_trans_cust', 'sum'),
                              n_trans_cust = ('num_trans_cust','count'),
                              sum_trans_item=('num_trans_item', 'sum'),
                              n_trans_item = ('num_trans_item','count'),
                              keep_article = ('keep_article','sum')
                             ).reset_index()
                sku_keep['loyalty'] = sku_keep['keep_article']/(sku_keep['sum_trans_cust']/sku_keep['n_trans_cust'])
                sku_keep['weighted_loyalty'] = sku_keep['loyalty']*sku_keep['n_trans_item']
                sku_keep['num_trans_cust']=sku_keep['sum_trans_cust']/sku_keep['n_trans_cust']
                sku_keep['num_trans_item']=sku_keep['sum_trans_item']/sku_keep['n_trans_item']
                sku_keep['weighted_num_trans_cust'] = sku_keep['num_trans_cust']*sku_keep['n_trans_item']
                sku_keep['weighted_num_trans_item'] = sku_keep['num_trans_item']*sku_keep['n_trans_item']
                loyal_list.append(sku_keep.groupby(
                                        [sku_group, sku_id]
                                    ).agg(
                                        loyalty=('loyalty','mean'),
                                        wl_sum=('weighted_loyalty','sum'),
                                        wn_sum =('weighted_num_trans_cust','sum'),
                                        wn_item_sum = ('weighted_num_trans_item','sum'),
                                        num_customer=(cust_id, pd.Series.nunique),
                                        sum_trans_item = ('n_trans_item','sum'),
                                    ).reset_index(
                                )
                            )
            sku_loyal = pd.concat(loyal_list).reset_index()
            sku_loyal['loyalty'] = sku_loyal['wl_sum']/sku_loyal['sum_trans_item']
            sku_loyal['avg_trans_cust'] = sku_loyal['wn_sum']/sku_loyal['sum_trans_item']
            sku_loyal['num_trans_item'] = sku_loyal['wn_item_sum']/sku_loyal['sum_trans_item']
            sku_loyal = sku_loyal[[sku_group, sku_id, 'loyalty', 'num_customer', 'avg_trans_cust','num_trans_item']].sort_values(by='loyalty',ascending=False)
        else:
            sku_keep = sku_wip.groupby(
                         [sku_group, cust_id, sku_id]
                          ).agg(
                          num_customer=(cust_id, pd.Series.nunique),
                          sum_trans_cust=('num_trans_cust', 'sum'),
                          n_trans_cust = ('num_trans_cust','count'),
                          sum_trans_item=('num_trans_item', 'sum'),
                          n_trans_item = ('num_trans_item','count'),
                          keep_article = ('keep_article','sum')
                         ).reset_index()
            sku_keep['loyalty'] = sku_keep['keep_article']/(sku_keep['sum_trans_cust']/sku_keep['n_trans_cust'])
            sku_keep['weighted_loyalty'] = sku_keep['loyalty']*sku_keep['n_trans_item']
            sku_keep['num_trans_cust']=sku_keep['sum_trans_cust']/sku_keep['n_trans_cust']
            sku_keep['num_trans_item']=sku_keep['sum_trans_item']/sku_keep['n_trans_item']
            sku_keep['weighted_num_trans_cust'] = sku_keep['num_trans_cust']*sku_keep['n_trans_item']
            sku_keep['weighted_num_trans_item'] = sku_keep['num_trans_item']*sku_keep['n_trans_item']
            sku_loyal = sku_keep.groupby(
                            [sku_group, sku_id]
                        ).agg(
                            loyalty=('loyalty','mean'),
                            wl_sum=('weighted_loyalty','sum'),
                            wn_sum =('weighted_num_trans_cust','sum'),
                            wn_item_sum = ('weighted_num_trans_item','sum'),
                            num_customer=(cust_id, pd.Series.nunique),
                            sum_trans_item = ('n_trans_item','sum'),
                        ).reset_index(
                    )
            sku_loyal['loyalty'] = sku_loyal['wl_sum']/sku_loyal['sum_trans_item']
            sku_loyal['avg_trans_cust'] = sku_loyal['wn_sum']/sku_loyal['sum_trans_item']
            sku_loyal['num_trans_item'] = sku_loyal['wn_item_sum']/sku_loyal['sum_trans_item']
            sku_loyal = sku_loyal[[sku_group, sku_id, 'loyalty', 'num_customer', 'avg_trans_cust','num_trans_item']].sort_values(by='loyalty',ascending=False)
    return sku_loyal


cat_lookup = smart_load_to_pd(fname=lookup_file, sep=",", decimal= ".", encoding="latin-1")
cat_lookup = cat_lookup[cat_lookup["sales_2y"] > 0]
cat_lookup = cat_lookup.sort_values(by="sales_2y")

nosales_cat = []
nogrp_cat = []
promo_cat = []

def process_single_category(cat: str):

    start_loy = time.time()
    #print("Running loyalty for category: " + str(cat))
    cat_out = workarea_path + re.sub("/", "", str(cat))
    if not os.path.exists(cat_out):
        os.makedirs(cat_out)
    cat_out = cat_out + "/"
    cat_code = cat_lookup[cat_lookup["category"] == str(cat)]["cat_code"].values[0]
    sku_filter = workarea_path + re.sub("/", "", str(cat)) + "/" + sku_filt_file
    cat_group = cat_out + 'grouping' + '_' + str(cat_code).zfill(3) + ".csv"
    cat_loyal = cat_out + 'loyalty' + '_' + str(cat_code).zfill(3) +'.csv'
    sales_files, multi_sales = utl.get_sales_files(sales_path, cat_code)
    # print(sales_files)
    if len(sales_files) == 0 or not os.path.exists(sku_filter):
        nosales_cat.append(cat)
        return
    if not os.path.exists(cat_group):
        nogrp_cat.append(cat)
        return
    #
    print("Loyalty: step 1 - import")
    # with open(log_file, 'a') as f:
    #     f.write("start computing Loyalty for " + str(cat) + "\n")
    ## Import hierarchical clustering results
    group_res = pd.read_csv(cat_group, sep=';', decimal=',', encoding='latin-1')
    group_res[sku_id_focus] = group_res[sku_id_focus].astype(str)
    group_res[sku_id_sub] = group_res[sku_id_sub].astype(str)
    #print(group_res[sku_gkey_focus].unique())
    grp_supp1 = group_res[[sku_id_focus, sku_group]
        ].rename(
            columns={sku_id_focus: sku_id}
        )
    grp_supp2 = group_res.loc[
            group_res[sku_id_sub] != "nan",
            [sku_id_sub, sku_group]
        ].rename(
            columns={sku_id_sub: sku_id}
        )
    grp_supp1[sku_id] = grp_supp1[sku_id].astype(str)
    grp_supp2[sku_id] = grp_supp2[sku_id].astype(str)#.astype(int).astype(str)
    group_supp = pd.concat(
            [grp_supp1, grp_supp2]
        ).drop_duplicates()
    #
    ## Import helper metadata
    sales_cols2keep = [
        sku_id, cust_id, tx_date, qty, amount, promo, fidelity
    ]
    final_cols2keep = [sku_id, cust_id, tx_date]
    hlpr_cols2use = [
        sku_id, sku_desc, category, category_iri, sku_status,
        group_key, 'Settore', 'Marca', 'Fornitore'
        ]
    sku_flt = pd.read_csv(sku_filter, sep=";", decimal= ",")
    sku_flt = sku_flt.rename(columns={ category_meta: category })
    sku_flt = sku_flt[hlpr_cols2use].drop_duplicates()
    #print(sku_flt.shape) #1412
    loyal_res = []
    # Import sales data
    for ff in sales_files:
        print("loading "+ff)
        sku_buy = smart_load_to_pd(ff, sep=';', decimal=",", encoding='latin-1',
                                   apply_loyalty_filters=True)
        sku_buy = sku_buy[sales_cols2keep]
        print("sku_buy shape: ", sku_buy.shape) #63,989,094
        if (sku_buy[~sku_buy[promo].isna()][promo] == 1).all():
            promo_cat.append(cat)
            continue
        # filter promo sales?
        if filter_promo:
            sku_buy = sku_buy[sku_buy[promo]==0]
        tx_bound = 15000000
        if sku_buy.shape[0] > tx_bound:
            grp_bckt_size_1 = 30
            sku_buy["cust_grp"] = sku_buy.groupby([sku_id]).ngroup() // grp_bckt_size_1
            n_bckt = sku_buy["cust_grp"].max()+1
            print(f"steps: {n_bckt}")
            for this_grp in range(n_bckt):
                print(this_grp+1, "/", n_bckt)
                tx_red = sku_buy.loc[sku_buy.cust_grp == this_grp].copy()
                # here we only need sku_flt to keep admissible SKUs from the sales data
                tx_red[sku_id] = tx_red[sku_id].astype(str)
                sku_flt[sku_id] = sku_flt[sku_id].astype(str)

                tx_red = tx_red.merge(
                        sku_flt[[sku_id]],
                        how='inner',
                        on=[sku_id]
                    )
                tx_red = clean_tx_data_red(tx_red)
                tx_red = tx_red[final_cols2keep].astype({sku_id: str})
                tx_red = tx_red.merge(
                    group_supp,
                    on=sku_id,
                    how='inner'
                )
                sku_loyal = compute_loyalty(tx_red, min_count)
                loyal_res.append(sku_loyal)
            del tx_red
        else:
            # here we only need sku_flt to keep admissible SKUs from the sales data
            sku_buy[sku_id]=sku_buy[sku_id].astype(str)
            sku_flt[sku_id]=sku_flt[sku_id].astype(str)
            sku_buy = sku_buy.merge(
                    sku_flt[[sku_id]],
                    how='inner',
                    on=[sku_id]
                )
            #print(sku_buy.shape) #59,165,367
            sku_buy = clean_tx_data_red(sku_buy)
            sku_buy = sku_buy[final_cols2keep].astype({sku_id: str})
            #print(sku_buy.shape) #48,944,466
            sku_buy = sku_buy.merge(
                group_supp,
                on=sku_id,
                how='inner'
            )
            sku_loyal = compute_loyalty(sku_buy, min_count)
            loyal_res.append(sku_loyal)
        del sku_buy
        gc.collect()
    sku_loyal = pd.concat(loyal_res)
    miss_ids = np.setdiff1d(
                    group_res[sku_id_focus],
                    sku_loyal[sku_id])
    miss_len = len(miss_ids)
    # Create output with no substitutes
    miss_loyal = group_res[
        group_res[sku_id_focus].isin(miss_ids)
        ][[sku_id_focus, sku_group]
        ].rename(columns={sku_id_focus:sku_id}).drop_duplicates()
    miss_loyal[sku_loyalty] = 0
    miss_loyal['num_customer'] = 0
    miss_loyal['avg_trans_cust'] = 0
    miss_loyal['num_trans_item'] = 0
    del group_res
    del loyal_res
    out_loyal = pd.concat([sku_loyal, miss_loyal], axis=0)
    del sku_loyal
    gc.collect()
    #print(out_loyal.shape)
    out_loyal = out_loyal.merge(
                sku_flt,
                how='left',
                on=sku_id
                )[
                    [sku_group, sku_id, sku_desc,
                        sku_loyalty, 'num_trans_item', 'num_customer', 'avg_trans_cust']
                ].sort_values(
                    by=[sku_group, sku_loyalty, 'num_customer', sku_id],
                    ascending=(True, False, False, True)
                )
    print("out_loyal shape: ", out_loyal.shape)
    if write_out:
        out_loyal.to_csv(cat_loyal, index=False, sep=";", decimal= ",")
    # with open(log_file, 'a') as f:
    #     f.write("finish computing Loyalty for " + str(cat) + "\n")
    del out_loyal
    del sku_flt


if __name__ == "__main__":

    if len(sys.argv) < 2:
        print("ERRORE: Nessuna categoria fornita.")
        print("Uso: python metadata.py <nome_categoria>")
        sys.exit(1)  # Esce con un codice di errore

    current_category = sys.argv[1]

    process_single_category(current_category)

    sys.exit(0)  # Esce indicando successo
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      