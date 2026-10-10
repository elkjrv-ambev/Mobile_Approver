import logging
from pathlib import Path
from zipfile import BadZipFile

from openpyxl.utils.exceptions import InvalidFileException
import pandas as pd
from pyarrow.lib import ArrowException


logger = logging.getLogger(__name__)


class CleanCases:
    """Load, clean, and persist the Cases dataset."""

    STRING_COLUMNS = (
        "report_id",
        "report_reference",
        "month_year",
        "daycare_reference_month",
        "customer_category",
        "employee_id",
        "policy",
        "can_be_approved",
    )
    FLOAT_COLUMNS = (
        "gross_amount_cc",
        "net_amount",
        "max_daycare_amount",
        "tope_actual",
    )
    BOOLEAN_COLUMNS = (
        "has_daycare",
        "has_housing",
        "aprove_housing",
        "aprove_edv_housing",
        "aprove_guarderia",
        "aprove_km",
        "rules_approval",
    )
    REQUIRED_COLUMNS = (
        *STRING_COLUMNS,
        "transaction_date",
        *FLOAT_COLUMNS,
        *BOOLEAN_COLUMNS,
        "__insert_utc_ts",
    )

    def __init__(self, data_dict: dict | None = None, base_dir: Path | str | None = None):
        self.base_dir = Path(base_dir) if base_dir is not None else Path(__file__).resolve().parent.parent
        self.input_path = self.base_dir / "bases" / "Cases_sem_limpar.parquet"
        self.output_path = self.base_dir / "bases" / "Cases_limpos.parquet"
        self.data_dict = data_dict if data_dict is not None else {}

        if "Cases sem limpar" not in self.data_dict:
            legacy_input_path = self.input_path.with_suffix(".xlsx")
            try:
                if self.input_path.is_file():
                    logger.info("Carregando base de entrada: %s", self.input_path)
                    self.data_dict["Cases sem limpar"] = pd.read_parquet(self.input_path)
                elif legacy_input_path.is_file():
                    logger.warning("Migrando base legada %s para Parquet", legacy_input_path)
                    self.data_dict["Cases sem limpar"] = pd.read_excel(legacy_input_path)
                    self.data_dict["Cases sem limpar"].to_parquet(self.input_path, index=False)
                else:
                    self.data_dict["Cases sem limpar"] = pd.read_parquet(self.input_path)
            except (ArrowException, BadZipFile, ImportError, InvalidFileException, OSError, ValueError):
                logger.exception("Falha ao carregar a base de entrada Cases")
                raise

    def _format_types(self, cases: pd.DataFrame) -> pd.DataFrame:
        missing_columns = [column for column in self.REQUIRED_COLUMNS if column not in cases.columns]
        if missing_columns:
            raise ValueError(f"Colunas obrigatórias ausentes em Cases: {', '.join(missing_columns)}")

        formatted = cases.copy()
        for column in self.STRING_COLUMNS:
            formatted[column] = formatted[column].astype("string")

        for column in self.FLOAT_COLUMNS:
            formatted[column] = pd.to_numeric(formatted[column], errors="raise").astype("Float64")

        formatted["transaction_date"] = pd.to_datetime(formatted["transaction_date"], errors="raise")
        formatted["__insert_utc_ts"] = pd.to_datetime(formatted["__insert_utc_ts"], errors="raise")

        boolean_values = {
            "true": True,
            "false": False,
            "1": True,
            "0": False,
            "yes": True,
            "no": False,
            "sim": True,
            "nao": False,
            "não": False,
        }

        def parse_boolean(value):
            if pd.isna(value):
                return pd.NA
            if isinstance(value, str):
                return boolean_values.get(value.strip().lower(), pd.NA)
            if value in (True, False):
                return bool(value)
            return pd.NA

        for column in self.BOOLEAN_COLUMNS:
            values = formatted[column].map(parse_boolean)
            invalid = formatted[column].notna() & values.isna()
            if invalid.any():
                bad_values = formatted.loc[invalid, column].drop_duplicates().tolist()
                raise ValueError(f"Valores booleanos inválidos na coluna {column}: {bad_values}")
            formatted[column] = values.astype("boolean")

        if formatted["report_reference"].isna().any():
            raise ValueError("A coluna report_reference não pode conter valores vazios.")
        if formatted["__insert_utc_ts"].isna().any():
            raise ValueError("A coluna __insert_utc_ts não pode conter valores vazios.")

        return formatted

    def clean(self) -> pd.DataFrame:
        """Keep the latest rows for each report reference and save the cleaned dataset."""
        try:
            cases = self._format_types(self.data_dict["Cases sem limpar"])
            group_cases = cases.groupby("report_reference", as_index=False)["__insert_utc_ts"].max()
            cleaned = cases.merge(group_cases, on=["report_reference", "__insert_utc_ts"], how="inner")
            cleaned["Item"] = cleaned.groupby("report_reference", sort=False).cumcount() + 1
            cleaned = cleaned.set_index(["report_reference", "Item"])

            self.output_path.parent.mkdir(parents=True, exist_ok=True)
            cleaned.to_parquet(self.output_path)
            self.data_dict["Cases limpos"] = cleaned
            logger.info("Base limpa salva em %s (%s linhas)", self.output_path, len(cleaned))
            return cleaned
        except (ArrowException, KeyError, OSError, TypeError, ValueError):
            logger.exception("Falha ao limpar e salvar a base Cases")
            raise
