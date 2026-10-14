from pathlib import Path

import pandas as pd

from src.clean_cases import CleanCases

import numpy as np


class Analisis:
    """Coordinate the Cases analysis and cleaning process."""

    def __init__ (self, data_dict: dict | None = None, base_dir: Path | str | None = None):
        """Inicializa o processo de análise com os dados e a pasta base informados."""
        self.cleaner = CleanCases (data_dict=data_dict, base_dir=base_dir)
        self.data_dict = self.cleaner.data_dict

    def do_analisis (self) -> pd.DataFrame:
        "Faz o analisis"
        # Clean data
        self.create_cases_cleaned ()

        # Set approval category
        new_data = self.set_approval_category ()

        # Reset quotas for housing
        self.fit_quotas ()
        return self.data_dict ["Cases limpos"]


    def create_cases_cleaned (self) -> pd.DataFrame:
        """Executa a limpeza e retorna a base Cases limpos persistida."""
        # Clean data
        self.cleaner.clean ()

        # Set approval category
        #self.set_approval_category ()

        # Reset quotas for housing
        #self.fit_quotas ()

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
        filter_eval = new_data ["approval_category"] == "Houssing"        

        ## Calculamos a soma dos montos para cada report_reference
        group_amounts = new_data.loc [filter_eval].reset_index ()
        group_amounts = group_amounts.groupby ("report_reference").agg (Total_amount = ('gross_amount_cc', 'sum'), 
                                                                         Quota_housing = ('tope_actual', 'max'), 
                                                                         Num_items = ('Item', 'count'))

        ## Filtramos os casos ultrapassão a quota
        filter_qut = group_amounts ["Total_amount"] > group_amounts ["Quota_housing"]       
        group_amounts = group_amounts [filter_qut]

        new_data ["Reset amount"] = False
        new_data ["New amount"] = np.nan
        if not group_amounts.empty:
            ## Calculamos os novos valores por item
            group_amounts ["Quota_per_item"] = group_amounts ["Quota_housing"]/group_amounts ["Num_items"]

            ## Marcamos em "Cases limpos" as linhas que teram seus montos modificados
            filter_qta = new_data.index.get_level_values ("report_reference") in (group_amounts.index)
            new_data.loc [filter_qta, ["Reset amount"]] = True 

            ## Definimos os novos valores dos montos
            new_data.loc [filter_qta, "New amount"] = new_data.loc [filter_qta].index.get_level_values ("report_reference").map (group_amounts ["Quota_per_item"])

        # Guarda as atualizações
        new_data.to_parquet (self.cleaner.output_path)
        self.data_dict ["Cases limpos"] = new_data

        return self.data_dict ["Cases limpos"]
        #logger.info ("Base limpa salva em %s (%s linhas)", self.output_path, len (cleaned))
