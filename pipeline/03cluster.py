# ## Clusters

import numpy as np
import pandas as pd
import re
import sys
import os
import time
from scipy.spatial.distance import squareform
import scipy.cluster.hierarchy as sch
from matplotlib import pyplot as plt
import utils as utl

# config_file = "./config/configurazioni.yaml"
# with open(config_file, "r") as f:
#     config = yaml.safe_load(f)
config = utl.get_Config()

input_path= config['paths']['input_path']
sales_path = config['paths']['sales_path']
workarea_path= config['paths']['workarea_path']

# files to process
lookup_file = input_path + config['files']['lookup_cats']

# misc options
linkage_method = config['parameters']['grp_linkage']    # "ward", "single", "complete", "average"
cut_threshold = config['parameters']['grp_cut_threshold']
grp_memb_min = config['parameters']['grp_memb_min']
debug_flag = config['parameters']['grp_save_dendro']
sales_flag = config['parameters']['grp_debug_sales']
write_out = True   ## change only when you know what you're doing!

# run_cfg = config['files']['cat_config']
# # categories_to_keep = cat_config['cat_to_run']
#
# with open(run_cfg, "r") as f:
#     cat_config = yaml.safe_load(f)

# Define column names
lista_colonne = utl.get_Config_Colonne()
group_key = lista_colonne['group_key']
category = lista_colonne['category']
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
sku_group = lista_colonne['sku_group']

sku_id_focus = lista_colonne['sku_id_focus']
sku_id_sub = lista_colonne['sku_id_sub']
sku_desc_focus = lista_colonne['sku_desc_focus']
sku_desc_sub = lista_colonne['sku_desc_sub']
sku_sold_focus = lista_colonne['sku_sold_focus']
sku_sold_sub = lista_colonne['sku_sold_sub']
sku_gkey_focus = lista_colonne['sku_gkey_focus']
sku_gkey_sub = lista_colonne['sku_gkey_sub']
sku_subscore = lista_colonne['sku_subscore']
sku_group_focus = lista_colonne['sku_group_focus']
sku_group_sub = lista_colonne['sku_group_sub']

# load_filtered_sales_parquet e smart_load_to_pd sono state centralizzate
# in utils/sales_loader.py e sono accessibili tramite utl.smart_load_to_pd
smart_load_to_pd = utl.smart_load_to_pd


def get_customers_without_fidelity(df_buy):
    # Check customers with and without fidelity flag
    cust_no_fidelity = set(list(df_buy[df_buy[fidelity]==0][cust_id].unique()))
    cust_with_fidelity = set(list(df_buy[df_buy[fidelity]==1][cust_id].unique()))
    cust_never_fidelity = cust_no_fidelity-cust_with_fidelity
    return cust_never_fidelity


def clean_tx_data(df_tx):
    # Clean data
    df_tx[sku_id] = df_tx[sku_id].astype(str)
    df_tx[tx_id] = df_tx[cust_id].astype(str) + "_" + df_tx[pdv_id].astype(str) + "_" + df_tx[tx_date].astype(str)
    #df_tx[qty] = df_tx[qty].apply(lambda x: float(x.replace(',', '.')) if type(x)==str else x)
    #df_tx[amount] = df_tx[amount].apply(lambda x: float(x.replace(',', '.')) if type(x)==str else x)
    df_tx[tx_date] = pd.to_datetime(df_tx[tx_date].astype(str), format='%Y-%m-%d')
    #
    # Filter invalid transactions
    df_tx = df_tx[df_tx[cust_id]!=-1]
    customers_without_fidelity = get_customers_without_fidelity(df_tx)
    df_tx = df_tx[(df_tx[qty]>0) &
                  (df_tx[amount]>0) &
                  (~df_tx[cust_id].isin(customers_without_fidelity)) # customers no fidelity
                 ]
    return df_tx


def prepare_data_for_clustering(df):
    #print(df[df[sku_subscore]!=0].shape)
    df_hlpr = pd.pivot_table(
            df, values=sku_subscore, index=sku_id_focus,
            columns=sku_id_sub, aggfunc="max", fill_value=0
    )

    # 1. Identifica tutte le colonne necessarie prima del ciclo
    unique_skus = np.union1d(
        df[sku_id_focus].values,
        df[~df[sku_id_sub].isna()][sku_id_sub].values
    ).astype(str)

    # 2. Aggiungi le nuove colonne al DataFrame in una singola operazione
    # Usiamo il metodo .reindex() o creiamo un nuovo DataFrame con le colonne aggiuntive
    missing_cols = [col for col in unique_skus if col not in df_hlpr.columns]

    # Crea un nuovo DataFrame con le colonne mancanti inizializzate a 0
    new_cols_df = pd.DataFrame(0, index=df_hlpr.index, columns=missing_cols)

    # Unisci il DataFrame originale con le nuove colonne
    df_hlpr = pd.concat([df_hlpr, new_cols_df], axis=1)

    ##print(np.sum(df_hlpr.values!=0))
    #    # fill missing combination (to create the distance matrix)
    #for cc in np.union1d(
    #    df[sku_id_focus].values,
    #    df[~df[sku_id_sub].isna()][sku_id_sub].values
    #    ).astype(str):
    #    if cc not in df_hlpr.columns:
    #        df_hlpr[cc] = 0
    #



    for cc in np.union1d(
        df[sku_id_focus].values,
        df[~df[sku_id_sub].isna()][sku_id_sub].values
        ).astype(str):
        if cc not in df_hlpr.index:
            df_hlpr = pd.concat([df_hlpr, pd.DataFrame({k: 0 for k in df_hlpr.columns}, index=[cc])])
#            df_hlpr_filtrati = [df for df in df_hlpr if not df.empty]
#            df_hlpr = pd.concat([df_hlpr_filtrati, pd.DataFrame({k:0 for k in df_hlpr.columns }, index=[cc])])

    # create the symmetric distance matrix
    dist_df = (df_hlpr[list(df_hlpr.index)] + df_hlpr[list(df_hlpr.index)].transpose())/2
    dist_df = 1/(1e-3+dist_df**(.2))
    dist_np = dist_df.values
    #print(dist_np.shape)
    dist_np[range(dist_np.shape[0]), range(dist_np.shape[0])] = 0
    return dist_np, df_hlpr.index

#CEGIL riscrita def per eliminare un RuntimeWarning
#def create_clusters(dist, ids, linkage='ward', cut_dist=None, to_file=False, fname="tree_plt.png"):
    #    sqrf = squareform(dist) # convert to a 'triangular' object expected by sch.linkage
    #linked = sch.linkage(sqrf, linkage)
    #if cut_dist is None:
    #    plt.figure(figsize=(10, 7))
    #    sch.dendrogram(linked,
    #        orientation='top',
    #        distance_sort='descending',
    #        show_leaf_counts=True)
    #    if to_file:
    #        plt.savefig(fname, format='png', bbox_inches='tight')
    #    else:
    #        plt.show()
    #    return None
    #
    #res = pd.DataFrame({sku_id:ids, sku_group:sch.fcluster(linked, cut_dist, 'distance')})
    #return res

def create_clusters(dist, ids, linkage='ward', cut_dist=None, to_file=False, fname="tree_plt.png"):

    sqrf = squareform(dist)
    linked = sch.linkage(sqrf, linkage)

    if cut_dist is None:
        plt.figure(figsize=(10, 7))
        sch.dendrogram(linked,
                       orientation='top',
                       distance_sort='descending',
                       show_leaf_counts=True)

        if to_file:
            plt.savefig(fname, format='png', bbox_inches='tight')

        else:
            plt.show()

        # Aggiungi questa linea per chiudere la figura
        plt.close()  # o plt.close('all')

        return None

    res = pd.DataFrame({sku_id: ids, sku_group: sch.fcluster(linked, cut_dist, 'distance')})
    return res



def append_cluster_to_similarity(df_sim, df_clus):
    res = df_sim.merge(df_clus, left_on=sku_id_focus, right_on=sku_id, how='left')\
        .drop(columns=[sku_id]).rename(columns={sku_group:sku_group_focus})\
        .merge(df_clus, left_on=sku_id_sub, right_on=sku_id, how='left')\
        .drop(columns=[sku_id]).rename(columns={sku_group:sku_group_sub})
    return res


cat_lookup = smart_load_to_pd(fname=lookup_file, sep=",", decimal= ".", encoding="latin-1")
cat_lookup = cat_lookup[cat_lookup["sales_2y"] > 0]
cat_lookup = cat_lookup.sort_values(by="sales_2y")

nosims_cat = []
nosales_cat = []
onesims_cat = []


def process_single_category(cat: str):

    start_grp = time.time()

    print("Running clustering/grouping for category: " + str(cat))
    cat_out = workarea_path + re.sub("/", "", str(cat))
    if not os.path.exists(cat_out):
        os.makedirs(cat_out)
    cat_out = cat_out + "/"
    cat_code = cat_lookup[cat_lookup["category"] == str(cat)]["cat_code"].values[0]
    cat_sim = cat_out + 'similarity' + '_' + str(cat_code).zfill(3) + ".csv"
    cat_chlp = cat_out + 'grp_help' + '_' + str(cat_code).zfill(3) +'.csv'
    cat_clus = cat_out + 'grouping' + '_' + str(cat_code).zfill(3) +'.csv'
    #
    if not os.path.exists(cat_sim):
        nosims_cat.append(cat)
        return
    print("Grouping: step 1 - import")
    # Import data
    sim_res = pd.read_csv(cat_sim, sep=';', decimal=',', encoding='latin-1')
    sim_res = sim_res.astype({
        sku_id_focus: str,
        sku_id_sub: str
    })
    # print("sim_res shape: ", sim_res.shape)
    sim_res.loc[sim_res[sku_subscore] < 1e-3, sku_subscore] = 0
    # # 2. Run hierarchical clustering
    # Prepare distance matrix
    print("Grouping: step 2 - hierarchical clustering")
    dist_mat, idx = prepare_data_for_clustering(sim_res)
    if dist_mat.shape == (1,1):
        onesims_cat.append(cat)
        grp_full = sim_res.copy()
        grp_full[sku_group] = 1
        if write_out:
            grp_full[sku_id_sub]=grp_full[sku_id_sub].astype(int).astype(str)
            grp_full.to_csv(cat_clus, index=False, sep=";", decimal= ",")
            grp_full.to_excel(cat_clus, index=False, sep=";", decimal=",")
        return
    #
    if debug_flag:
        create_clusters(dist_mat, idx, linkage_method, to_file=True, fname=cat_out + "dendro_"+str(cat_code).zfill(3)+".png")
    hier_grp = create_clusters(dist_mat, idx, linkage_method, cut_threshold)
    #
    print("Grouping: step 3 - cleanup")
    hier_cnt = hier_grp[sku_group].value_counts().reset_index()
    hier_cnt.columns=[sku_group,"members"]
    #print(clus_num.sort_values(by="members", ascending=False))
    hier_merge = hier_cnt[hier_cnt["members"] <= grp_memb_min][sku_group].values
    hier_grp.loc[hier_grp[sku_group].isin(hier_merge), sku_group] = 0
    ## here we finally add clusters to similar objects
    grp_res = append_cluster_to_similarity(sim_res, hier_grp[[sku_id, sku_group]])
    print("sim_res shape: ", grp_res.shape)
    ## save partial file with the results (notice we have lost a few items
    ## with no similar SKUs in the same group)
    if write_out:
        # grp_res[sku_id_sub] = grp_res[sku_id_sub].astype(float).astype(int).astype(str)
        grp_res[sku_id_sub]= grp_res[sku_id_sub].astype(float).fillna(0).astype(int)
        grp_res.sort_values(
            by=[sku_group_focus, sku_gkey_focus, sku_id_focus, sku_subscore],
            axis=0,
            ascending=False
            ).to_csv(cat_chlp, index=False, sep=";", decimal= ",")
    ## now we want to complete the list of SKUs, so start with those that have focus group == subst group
    grp_full = grp_res[
            grp_res[sku_group_focus] == grp_res[sku_group_sub]
        ].sort_values(
            by=[sku_group_focus, sku_gkey_focus, sku_id_focus, sku_subscore],
            axis=0,
            ascending=False
        ).drop(
            columns=[sku_group_sub]
        ).rename(
            columns={sku_group_focus:sku_group}
        )
    #print(grp_res[sku_id_focus].nunique())
    #print(grp_full[sku_id_focus].nunique())
    lost_id = grp_res[grp_res[sku_id_sub].isna()][sku_id_focus].values
    lost_id = np.concatenate([
            lost_id,
            grp_res[~grp_res[sku_id_focus].isin(
                np.union1d(grp_full[sku_id_focus].values, lost_id)
                )
            ][sku_id_focus].drop_duplicates().values
        ])
    #print(len(lost_id))
    grp_fill = sim_res[sim_res[sku_id_focus].isin(lost_id)].copy()
    for cc in grp_fill.columns:
        if re.match(r".*\(Substitute\)", cc) is not None:
            grp_fill[cc] = np.nan
    grp_fill[[sku_subscore]] = 0
    grp_fill[[sku_group]] = 999
    grp_fill[[sku_id_sub]] = ["N/A"]
    grp_fill = grp_fill.drop_duplicates()
    grp_full = pd.concat([grp_full, grp_fill])
    #print(grp_full[sku_id_focus].nunique())
    if write_out:
        grp_full= grp_full[grp_full[sku_id_sub] != 'N/A']
        grp_full[sku_id_sub] = grp_full[sku_id_sub].astype(float).astype(int).astype(str)
        grp_full.to_csv(cat_clus, index=False, sep=";", decimal= ",")
    if sales_flag:
        print("Grouping: step 4 - sales debug")
        cat_info = cat_out + 'grp_sales' + '_' + str(cat_code).zfill(3) +'.csv'
        hier_grp.loc[hier_grp[sku_id].isin(lost_id), sku_group] = 999
        dist_helper = []
        for cls in hier_grp[sku_group].sort_values().unique():
            dist_df = pd.DataFrame(dist_mat, columns=idx, index=idx)
            hlpr = dist_df.loc[hier_grp[hier_grp[sku_group] == cls][sku_id].values,
                   hier_grp[hier_grp[sku_group] == cls][sku_id].values]
            info = pd.DataFrame({ sku_group:cls, "elements":hlpr.shape[0],
                         "mean_dist": np.mean(hlpr.values.flatten()),
                         "non_zero":hlpr.shape[0]*(hlpr.shape[0]-1),
                         "valid":np.sum((hlpr.values > 0) & (hlpr.values < 1000)),
                         "ratio":np.round(np.sum((hlpr.values > 0) &
                                                 (hlpr.values < 1000))/(hlpr.shape[0]*(hlpr.shape[0]-1)),4)},
                       index=[cls])
            dist_helper.append(info)
        dist_helper = pd.concat(dist_helper)
        #print(dist_helper)
        sales_files, multi_sales = utl.get_sales_files(sales_path, cat_code)
        print(sales_files)
        if len(sales_files) == 0:
            nosales_cat.append(cat)
            return
        sales_cols2keep = [sku_id, amount]
        grp_res = []
        for ff in sales_files:
            print("loading "+ff)
            sku_buy = smart_load_to_pd(ff, sep=';', decimal= ",", encoding='latin-1')
            sku_buy = clean_tx_data(sku_buy)
            sku_buy = sku_buy[sales_cols2keep].drop_duplicates().astype({sku_id: str})
            grp_sale = grp_full[[sku_id_focus, sku_group]].drop_duplicates()
            grp_sale = grp_sale.merge(
                        sku_buy.rename(columns={sku_id:sku_id_focus}),
                        on=sku_id_focus,
                        how='inner')
            grp_sale = grp_sale.groupby(
                            sku_group
                        ).agg(
                            mean_sku_count=(sku_id_focus, 'nunique'),
                            mean_amount=(amount, 'mean'),
                            q90_amount=(amount, lambda x:x.quantile(.9)),
                            max_amount=(amount, 'max')
                        ).reset_index()
            grp_res.append(grp_sale)
            del sku_buy
        grp_res_final = pd.concat(grp_res)
        grp_res_final = dist_helper.merge(grp_res_final, on=sku_group, how='outer')
        if write_out:
            grp_res_final[sku_id_sub] = grp_res_final[sku_id_sub].astype(int).astype(str)
            grp_res_final.to_csv(cat_info, index=False, sep=";", decimal= ",")
        del grp_res
        del grp_res_final


if __name__ == "__main__":
    # Il programma ora si aspetta un argomento dalla riga di comando.
    # sys.argv è una lista che contiene gli argomenti:
    # sys.argv[0] è il nome dello script ("prefiltering.py")
    # sys.argv[1] è il primo argomento (la nostra categoria)

    if len(sys.argv) < 2:
        print("ERRORE: Nessuna categoria fornita.")
        print("Uso: python metadata.py <nome_categoria>")
        sys.exit(1)  # Esce con un codice di errore

    # Prende la categoria dal primo argomento passato
    current_category = sys.argv[1]

    # Lancia l'elaborazione solo per quella categoria
    process_single_category(current_category)

    # Quando lo script termina, il processo viene distrutto e la memoria liberata.
    sys.exit(0)  # Esce indicando successo
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    