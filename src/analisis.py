from pathlib import Path
import pandas as pd
from src.clean_cases import CleanCases
import pyarrow.parquet as pq
import pyarrow as pa
import os
import sys
import numpy as np

# Get the directory of the current script
SCRIPT_DIR = os.path.realpath(os.path.realpath(__file__))
SCRIPT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
three_levels_back = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
sys.path.insert(0, three_levels_back)
SCRIPT_DIR = Path (os.path.abspath(os.path.join(SCRIPT_DIR, "..")))
BASES_DIR = SCRIPT_DIR / "bases"

class Analisis:
    """Coordinate the Cases analysis and cleaning process."""

    def __init__ (self, data_dict: dict | None = None):
        """Inicializa o processo de análise com os dados e a pasta base informados."""
        self.cleaner = CleanCases (data_dict = data_dict, base_dir = BASES_DIR)
        self.data_dict = self.cleaner.data_dict

    def do_analisis (self) -> pd.DataFrame:
        "Faz o analisis"
        # Clean data
        self.create_cases_cleaned ()

        # Set approval category
        self.set_approval_category ()

        # Reset quotas for housing
        self.fit_quotas ()

        # Compara com a base Mobileexpences
        self.compare_cases_mobileexpences ()
        
        return self.data_dict ["Cases limpos"]

    def load_data_parquet (self, params_dict):
        path_file = BASES_DIR / f"{params_dict ["Base"]}.parquet"
        print ("==> Carregando base ", params_dict ["Base"], " in path ", path_file)
        if os.path.exists (path_file):
            self.data_dict [params_dict ["Base"]] = pd.read_parquet (path_file)            
        else:
            if len (self.index_list [params_dict ["Base"]]) > 0:
                self.data_dict [params_dict ["Base"]] = pd.DataFrame (columns = self.columns_used [params_dict ["Base"]] + self.index_list [params_dict ["Base"]])
                self.data_dict [params_dict ["Base"]].set_index (self.index_list [params_dict ["Base"]], inplace = True)
            else:
                self.data_dict [params_dict ["Base"]] = pd.DataFrame (columns = self.columns_used [params_dict ["Base"]] + self.index_list [params_dict ["Base"]])

    def compare_cases_mobileexpences (self):
        # Carrega bases necesarias
        self.load_data_parquet ({"Base": "Open cases mobilexpences"})
        self.load_data_parquet ({"Base": "Cases_limpos"})
        mobileexpences = self.data_dict ["Open cases mobilexpences"]
        cases_limpos = self.data_dict ["Cases_limpos"]

        # Comparamos as bases e deixamos só os casos a aprobar
        filter_1 = cases_limpos.index.get_level_values ("report_reference").isin (mobileexpences ["ReportRef"])
        cases_limpos ["Is open in mobileexpence"] = False
        cases_limpos.loc [filter_1, "Is open in mobileexpence"] = True

        # Guardamos a base atualizada
        self.data_dict ["Cases_limpos"] = cases_limpos
        self.save_to_parquet ({"Base": "Cases_limpos"})
        return cases_limpos

    def save_to_parquet (self, params_dict):
        preserve_index = True
        if "Inore index" in params_dict.keys ():
            preserve_index = params_dict ["Preserve index"]

        path_file = BASES_DIR / f"{params_dict ["Base"]}.parquet"
        print (f"save_to_parquet: Salvando base {params_dict ["Base"]} em {path_file}")
        table_parquet = pa.Table.from_pandas (self.data_dict [params_dict ["Base"]], preserve_index = preserve_index)
        pq.write_table (table_parquet, path_file)


    def create_cases_cleaned (self) -> pd.DataFrame:
        """Executa a limpeza e retorna a base Cases limpos persistida."""
        # Clean data
        self.load_data_parquet ({"Base": "Cases_sem_limpar"})
        input_cases = self.data_dict ["Cases_sem_limpar"]
        data_dict = {"Cases sem limpar": input_cases}
        self.cleaner = CleanCases (data_dict = data_dict, base_dir = BASES_DIR)

        new_cases = self.cleaner.clean ()

        self.data_dict ["Cases limpos"] = new_cases

        return self.data_dict ["Cases limpos"]

    def  set_approval_category (self) -> pd.DataFrame:
        """Asigna una columna nueva para separar por catergoria de aprovación."""
        self.cleaner.output_path.parent.mkdir (parents=True, exist_ok=True)
        new_data = self.data_dict ["Cases limpos"]

        # Casos de kilometragem
        filter_eval = (new_data ["can_be_approved"] == "True") & (new_data ["aprove_km"])
        new_data.loc [filter_eval, ["approval_category"]] = "Kilometer"

        # Casos de Housing
        filter_eval = (new_data ["can_be_approved"] == "True") & (new_data ["aprove_housing"])
        new_data.loc [filter_eval, ["approval_category"]] = "Housing"

        # Casos de Housing
        filter_eval = (new_data ["can_be_approved"] == "True") & (new_data ["aprove_guarderia"])
        new_data.loc [filter_eval, ["approval_category"]] = "Daycare"

        # Otros casos
        filter_eval = (new_data ["can_be_approved"] == "True") & (~ new_data ["aprove_km"]) & (~ new_data ["aprove_housing"]) & (~ new_data ["aprove_guarderia"])
        new_data.loc [filter_eval, ["approval_category"]] = "Other"

        # Guarda as atualizações
        new_data.to_parquet (self.cleaner.output_path)
        self.data_dict ["Cases limpos"] = new_data

        return self.data_dict ["Cases limpos"]
        #logger.info ("Base limpa salva em %s (%s linhas)", self.output_path, len (cleaned))

    def  fit_quotas (self) -> pd.DataFrame:
        """Ajusta quotas para os casos Housing e Daycare"""
        self.cleaner.output_path.parent.mkdir (parents=True, exist_ok=True)
        new_data = self.data_dict ["Cases limpos"]

        # Casos de Housing
        ## Criamos filtro dos casos Housing
        filter_eval = new_data ["approval_category"] == "Housing"        

        ## Calculamos a soma dos montos para cada report_reference
        group_amounts = new_data.loc [filter_eval].reset_index ()
        group_amounts = group_amounts.groupby ("report_reference").agg (Total_amount = ('gross_amount_cc', 'sum'), 
                                                                         Quota_housing = ('tope_actual', 'max'), 
                                                                         Num_items = ('Item', 'count'))

        ## Filtramos os casos ultrapassão a quota
        filter_qta = group_amounts ["Total_amount"] > group_amounts ["Quota_housing"]       
        group_amounts = group_amounts [filter_qta]
        
        new_data ["Reset amount"] = False
        new_data ["New amount"] = np.nan
        if not group_amounts.empty:
            ## Calculamos os novos valores por item
            group_amounts ["Quota_per_item"] = group_amounts ["Quota_housing"]/group_amounts ["Num_items"]

            ## Marcamos em "Cases limpos" as linhas que teram seus montos modificados
            filter_qta = new_data.index.get_level_values ("report_reference"). isin (group_amounts.index)
            new_data.loc [filter_qta, ["Reset amount"]] = True 

            ## Definimos os novos valores dos montos
            new_data.loc [filter_qta, "New amount"] = new_data.loc [filter_qta].index.get_level_values ("report_reference").map (group_amounts ["Quota_per_item"])

        # Guarda as atualizações
        new_data.to_parquet (self.cleaner.output_path)
        self.data_dict ["Cases limpos"] = new_data

        return self.data_dict ["Cases limpos"]
        #logger.info ("Base limpa salva em %s (%s linhas)", self.output_path, len (cleaned))
