import pandas as pd
from pymongo import MongoClient
from atomic_dataframe import DataFrameAtomic  # importa la tua classe
from mongodb_handler import atomic_services_collection

# Recupera tutti i documenti
docs = list(atomic_services_collection.find({}))

# Lista per salvare i dataframe flattati
flatted_dfs = []

for doc in docs:
    payload = {
        'diagram_id': doc['diagram_id'],
        'task_id': doc['task_id'],
        'name': doc['name'],
        'atomic_type': doc['atomic_type'],
        'method': doc['method'],
        'url': doc['url'],
        'owner': doc['owner'],
        'input_params': doc['dataframe_serialized'].get('input_params', []),
        'output_params': doc['dataframe_serialized'].get('output_params', [])
    }
    
    # Usa la classe DataFrameAtomic
    df_atomic = DataFrameAtomic(payload)
    df_atomic.create_main_dataframe()
    df_atomic.create_io_dataframes()
    flatted_df = df_atomic.get_flatted_wide_table()
    
    flatted_dfs.append(flatted_df)

# Unisci tutti i wide table in un unico dataframe
all_flatted = pd.concat(flatted_dfs, ignore_index=True)

# Visualizza
print(all_flatted)

# (Opzionale) Esporta in CSV
#all_flatted.to_csv('all_atomic_services_flatted.csv', index=False)

# (Opzionale) Esporta in Excel
#all_flatted.to_excel('all_atomic_services_flatted.xlsx', index=False)
