from pathlib import Path

import pandas as pd

from src.clean_cases import CleanCases


class Analisis:
    """Coordinate the Cases analysis and cleaning process."""

    def __init__ (self, data_dict: dict | None = None, base_dir: Path | str | None = None):
        """Inicializa o processo de análise com os dados e a pasta base informados."""
        self.cleaner = CleanCases (data_dict=data_dict, base_dir=base_dir)
        self.data_dict = self.cleaner.data_dict

    def create_cases_cleaned (self) -> pd.DataFrame:
        """Executa a limpeza e retorna a base Cases limpos persistida."""
        # Clean data
        self.cleaner.clean ()

        # Set approval category
        new_data = self.set_approval_category ()

        # Reset quotas for housing

        return new_data

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

        new_data.to_parquet (self.cleaner.output_path)
        self.data_dict ["Cases limpos"] = new_data

        # Otros casos
        filter_eval = (new_data ["can_be_approved"] == "True") & (~ new_data ["aprove_km"]) & (~ new_data ["aprove_housing"]) & (~ new_data ["aprove_guarderia"])
        new_data.loc [filter_eval, ["approval_category"]] = "Other"

        return new_data
        #logger.info ("Base limpa salva em %s (%s linhas)", self.output_path, len (cleaned))

