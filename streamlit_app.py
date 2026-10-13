from hashlib import sha256
from io import BytesIO
import logging
from pathlib import Path
from zipfile import BadZipFile

from openpyxl.utils.exceptions import InvalidFileException
import pandas as pd
from pyarrow.lib import ArrowException
import streamlit as st

from src.analisis import Analisis


BASE_DIR = Path (__file__).resolve ().parent
BASES_DIR = BASE_DIR / "bases"

logging.basicConfig (level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger (__name__)


@st.cache_data
def _read_base_file (file_path: str, modified_ns: int, file_size: int) -> pd.DataFrame:
    path = Path (file_path)
    if path.suffix.lower () == ".xlsx":
        return pd.read_excel (path)
    if path.suffix.lower () == ".parquet":
        return pd.read_parquet (path)
    raise ValueError (f"Formato de base não suportado: {path.suffix}")


def _base_key (file_path: Path, existing_keys: set[str]) -> str:
    known_keys = {"cases_sem_limpar": "Cases sem limpar", "cases_limpos": "Cases limpos"}
    normalized_stem = file_path.stem.casefold ()
    key = known_keys.get (normalized_stem, file_path.stem)
    if key in existing_keys:
        key = f"{key} ({file_path.name})"
    return key


def _load_data_dict () -> tuple[dict[str, pd.DataFrame], dict[str, str], list[str]]:
    data_dict: dict[str, pd.DataFrame] = {}
    load_errors: dict[str, str] = {}
    unsupported_files: list[str] = []
    if not BASES_DIR.is_dir ():
        logger.info ("A pasta de bases ainda não existe: %s", BASES_DIR)
    base_files = sorted ((path for path in BASES_DIR.iterdir () if path.is_file ()),
                         key=lambda path: path.name.casefold ()) if BASES_DIR.is_dir () else []

    for path in base_files:
        if path.suffix.lower () not in {".xlsx", ".parquet"}:
            unsupported_files.append (path.name)
            logger.warning ("Arquivo ignorado por formato não suportado: %s", path.name)
            continue
        key = _base_key (path, set (data_dict) | set (load_errors))
        try:
            stat = path.stat ()
            data_dict [key] = _read_base_file (str (path), stat.st_mtime_ns, stat.st_size)
            logger.info ("Base carregada: %s (%s linhas)", path.name, len (data_dict [key]))
        except (
            ArrowException,
            BadZipFile,
            ImportError,
            InvalidFileException,
            OSError,
            ValueError,
            pd.errors.ParserError,
        ) as error:
            load_errors [key] = f"Não foi possível abrir {path.name}: {error}"
            logger.exception ("Falha ao carregar a base %s", path.name)

    return data_dict, load_errors, unsupported_files


def _create_excel (cases_by_name: dict[str, pd.DataFrame]) -> bytes:
    excel_file = BytesIO ()
    with pd.ExcelWriter (excel_file, engine="openpyxl") as writer:
        used_sheet_names: set[str] = set ()
        for base_name, cases in cases_by_name.items ():
            has_named_index = any (name is not None for name in cases.index.names)
            export_cases = cases.reset_index () if has_named_index else cases
            sheet_name = "".join ("_" if character in "[]:*?/\\" else character for character in base_name)
            sheet_name = sheet_name [:31] or "Base"
            unique_sheet_name = sheet_name
            suffix = 2
            while unique_sheet_name.casefold () in used_sheet_names:
                suffix_text = f" ({suffix})"
                unique_sheet_name = f"{sheet_name [:31 - len (suffix_text)]}{suffix_text}"
                suffix += 1
            used_sheet_names.add (unique_sheet_name.casefold ())
            export_cases.to_excel (writer, sheet_name=unique_sheet_name, index=False)
    return excel_file.getvalue ()


def _case_values (cases: pd.DataFrame, column: str) -> pd.Series | None:
    """Retorna valores da coluna ou do nível homônimo do índice, se disponíveis."""
    if column in cases.columns:
        return cases [column]
    if column in cases.index.names:
        return pd.Series (cases.index.get_level_values (column), index=cases.index)
    return None


def _filter_cases (cases: pd.DataFrame, report_references: list[str], approval_values: list[str]) -> pd.DataFrame:
    """Filtra registros sem alterar os níveis do índice original."""
    filtered_cases = cases.copy ()
    if report_references:
        report_values = _case_values (filtered_cases, "report_reference")
        if report_values is not None:
            report_mask = report_values.astype ("string").isin (report_references)
            filtered_cases = filtered_cases.loc [report_mask.to_numpy ()]
    if approval_values:
        approval_values_in_cases = _case_values (filtered_cases, "can_be_approved")
        if approval_values_in_cases is not None:
            approval_mask = approval_values_in_cases.astype ("string").isin (approval_values)
            filtered_cases = filtered_cases.loc [approval_mask.to_numpy ()]

    return filtered_cases


def main () -> None:
    st.set_page_config (page_title = "Mobile Approver", page_icon = "📊", layout = "wide")
    st.title ("Mobile Approver")
    st.write ("Carregue um arquivo Excel ou Parquet, com os casos a tratar.")

    uploaded_file = st.file_uploader ("Selecione a base Cases sem limpar", type=["xlsx", "parquet"],
                                      help="Envie um arquivo Excel (.xlsx) ou Parquet (.parquet) contendo a base Casos a tratar.")
    upload_error = None
    if uploaded_file is not None:
        uploaded_bytes = uploaded_file.getvalue ()
        upload_key = f"{uploaded_file.name}:{sha256 (uploaded_bytes).hexdigest ()}"
        if st.session_state.get ("upload_key") != upload_key:
            try:
                uploaded_stream = BytesIO (uploaded_bytes)
                if Path (uploaded_file.name).suffix.lower () == ".parquet":
                    uploaded_cases = pd.read_parquet (uploaded_stream)
                else:
                    uploaded_cases = pd.read_excel (uploaded_stream)
                BASES_DIR.mkdir (parents=True, exist_ok=True)
                uploaded_cases.to_parquet (BASES_DIR / "Cases_sem_limpar.parquet", index=False)
                st.session_state ["upload_key"] = upload_key
                _read_base_file.clear ()
                logger.info ("Arquivo enviado %s salvo como Cases_sem_limpar.parquet (%s linhas)", uploaded_file.name, len (uploaded_cases))
            except (ArrowException, BadZipFile, ImportError, InvalidFileException, OSError, ValueError) as error:
                upload_error = f"Não foi possível ler ou salvar o arquivo enviado: {error}"
                logger.exception ("Falha ao validar ou salvar o arquivo enviado")

    if upload_error:
        st.error (upload_error)

    data_dict, load_errors, unsupported_files = _load_data_dict ()
    for error in load_errors.values ():
        st.error (error)
    if unsupported_files:
        st.info (f"Arquivos em formato não suportado para visualização: {', '.join (unsupported_files)}")

    input_cases = data_dict.get ("Cases sem limpar")

    if input_cases is not None and st.button ("Limpar dados", type="primary"):
        try:
            analysis = Analisis (data_dict={"Cases sem limpar": input_cases}, base_dir=BASE_DIR)
            with st.spinner ("Limpando os dados..."):
                cleaned_cases = analysis.create_cases_cleaned ()
            _read_base_file.clear ()
            data_dict ["Cases limpos"] = cleaned_cases
            st.success ("A base Cases_limpos.parquet foi atualizada.")
            logger.info ("Limpeza concluída: %s linhas salvas em Cases_limpos.parquet", len (data_dict ["Cases limpos"]))
        except (ImportError, OSError, TypeError, ValueError) as error:
            st.error (f"Não foi possível limpar a base: {error}")
            logger.exception ("Falha ao limpar a base Cases")

    display_data_dict = {
        key: cases for key, cases in data_dict.items ()
        if key.casefold () != "cases sem limpar" and not key.casefold ().startswith ("cases sem limpar (")
    }
    if not display_data_dict:
        st.info ("Nenhuma base processada encontrada na pasta bases. Envie a planilha e execute a limpeza.")
        return

    st.download_button ("Baixar bases processadas em Excel", data=_create_excel (display_data_dict),
                        file_name="Bases_processadas.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        type="primary", key="download_processed_bases")

    base_items = list (display_data_dict.items ())
    base_tabs = st.tabs ([key for key, _ in base_items])
    for (base_key, cases), base_tab in zip (base_items, base_tabs):
        with base_tab:
            #st.metric ("Linhas", f"{len (cases):,}")
            display_cases = cases.copy ()
            report_values = _case_values (display_cases, "report_reference")
            approval_values = _case_values (display_cases, "can_be_approved")
            if report_values is not None and approval_values is not None:
                report_options = sorted (report_values.dropna ().astype (str).unique ())
                approval_options = sorted (approval_values.dropna ().astype (str).unique ())
                report_filter, approval_filter = st.columns (2)
                with report_filter:
                    selected_reports = st.multiselect ("Filtrar por report_reference", options=report_options, key=f"report_filter_{base_key}")
                with approval_filter:
                    selected_approvals = st.multiselect ("Filtrar por can_be_approved", options=approval_options, key=f"approval_filter_{base_key}")

                filtered_cases = _filter_cases (display_cases, selected_reports, selected_approvals)
                st.metric ("Cases exibidos", f"{len (filtered_cases):,} de {len (display_cases):,}")
                st.dataframe (filtered_cases, width="stretch", alt=f"Pré-visualização de {base_key}")
                st.download_button ("Baixar Cases filtrados em Excel", data=_create_excel ({base_key: filtered_cases}),
                                    file_name=f"{base_key.replace (' ', '_')}_filtrados.xlsx",
                                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                    type="primary", key=f"download_{base_key}")
            else:
                st.dataframe (cases, width="stretch", alt=f"Pré-visualização de {base_key}")


if __name__ == "__main__":
    main ()
