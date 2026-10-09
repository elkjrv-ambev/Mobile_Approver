from datetime import date
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from zipfile import BadZipFile

from openpyxl.utils.exceptions import InvalidFileException
import pandas as pd
from pyarrow.lib import ArrowException
import streamlit as st

from src.clean_cases import CleanCases


BASE_DIR = Path(__file__).resolve().parent
BASES_DIR = BASE_DIR / "bases"


@st.cache_data
def _read_base_file(file_path: str, modified_ns: int, file_size: int) -> pd.DataFrame:
    path = Path(file_path)
    if path.suffix.lower() == ".xlsx":
        return pd.read_excel(path)
    if path.suffix.lower() == ".parquet":
        return pd.read_parquet(path)
    raise ValueError(f"Formato de base não suportado: {path.suffix}")


def _base_key(file_path: Path, existing_keys: set[str]) -> str:
    known_keys = {
        "cases_sem_limpar": "Cases sem limpar",
        "cases_limpos": "Cases limpos",
    }
    normalized_stem = file_path.stem.casefold()
    key = known_keys.get(normalized_stem, file_path.stem)
    if key in existing_keys:
        key = f"{key} ({file_path.name})"
    return key


def _load_data_dict() -> tuple[dict[str, pd.DataFrame], dict[str, str], list[str]]:
    data_dict: dict[str, pd.DataFrame] = {}
    load_errors: dict[str, str] = {}
    unsupported_files: list[str] = []
    base_files = sorted(
        (path for path in BASES_DIR.iterdir() if path.is_file()),
        key=lambda path: path.name.casefold(),
    ) if BASES_DIR.is_dir() else []

    for path in base_files:
        if path.suffix.lower() not in {".xlsx", ".parquet"}:
            unsupported_files.append(path.name)
            continue
        key = _base_key(path, set(data_dict) | set(load_errors))
        try:
            stat = path.stat()
            data_dict[key] = _read_base_file(str(path), stat.st_mtime_ns, stat.st_size)
        except (
            ArrowException,
            BadZipFile,
            ImportError,
            InvalidFileException,
            OSError,
            ValueError,
            pd.errors.ParserError,
        ) as error:
            load_errors[key] = f"Não foi possível abrir {path.name}: {error}"

    return data_dict, load_errors, unsupported_files


def _create_excel(cleaned_cases: pd.DataFrame) -> bytes:
    excel_file = BytesIO()
    has_named_index = any(name is not None for name in cleaned_cases.index.names)
    export_cases = cleaned_cases.reset_index() if has_named_index else cleaned_cases
    with pd.ExcelWriter(excel_file, engine="openpyxl") as writer:
        export_cases.to_excel(writer, sheet_name="Cases limpos", index=False)
    return excel_file.getvalue()


def _filter_cases(
    cases: pd.DataFrame,
    report_references: list[str],
    approval_values: list[str],
    rules_approval_values: list[str],
    insert_date_range: tuple[date, date],
) -> pd.DataFrame:
    filtered_cases = cases.copy()
    if report_references:
        filtered_cases = filtered_cases[filtered_cases["report_reference"].isin(report_references)]
    if approval_values:
        filtered_cases = filtered_cases[filtered_cases["can_be_approved"].astype("string").isin(approval_values)]
    if rules_approval_values:
        filtered_cases = filtered_cases[
            filtered_cases["rules_approval"].astype("string").isin(rules_approval_values)
        ]

    insert_dates = pd.to_datetime(filtered_cases["__insert_utc_ts"], errors="coerce").dt.date
    filtered_cases = filtered_cases[
        insert_dates.between(insert_date_range[0], insert_date_range[1])
    ]
    return filtered_cases


def main() -> None:
    st.set_page_config(page_title="Limpeza de Cases", page_icon="📊", layout="wide")
    st.title("Limpeza da base Cases")
    st.write("Carregue uma planilha Excel, execute a limpeza e baixe os dados tratados.")

    uploaded_file = st.file_uploader(
        "Selecione a base Cases sem limpar",
        type=["xlsx"],
        help="Envie um arquivo Excel (.xlsx) contendo as colunas da base Cases.",
    )
    upload_error = None
    if uploaded_file is not None:
        uploaded_bytes = uploaded_file.getvalue()
        upload_key = f"{uploaded_file.name}:{sha256(uploaded_bytes).hexdigest()}"
        if st.session_state.get("upload_key") != upload_key:
            try:
                pd.read_excel(BytesIO(uploaded_bytes))
                BASES_DIR.mkdir(parents=True, exist_ok=True)
                (BASES_DIR / "Cases_sem_limpar.xlsx").write_bytes(uploaded_bytes)
                st.session_state["upload_key"] = upload_key
            except (BadZipFile, ImportError, InvalidFileException, OSError, ValueError) as error:
                upload_error = f"Não foi possível ler ou salvar a planilha enviada: {error}"

    if upload_error:
        st.error(upload_error)

    data_dict, load_errors, unsupported_files = _load_data_dict()
    for error in load_errors.values():
        st.error(error)
    if unsupported_files:
        st.info(f"Arquivos em formato não suportado para visualização: {', '.join(unsupported_files)}")

    input_cases = data_dict.get("Cases sem limpar")

    if input_cases is not None and st.button("Limpar dados", type="primary"):
        try:
            cleaner = CleanCases(
                data_dict={"Cases sem limpar": input_cases},
                base_dir=BASE_DIR,
            )
            with st.spinner("Limpando os dados..."):
                cleaner.clean()
            _read_base_file.clear()
            data_dict["Cases limpos"] = cleaner.data_dict["Cases limpos"]
            st.success("A base Cases_limpos.parquet foi atualizada.")
        except (ImportError, OSError, TypeError, ValueError) as error:
            st.error(f"Não foi possível limpar a base: {error}")

    if not data_dict:
        st.info("Ainda não há bases salvas na pasta bases. Envie uma planilha .xlsx para começar.")
        return

    base_items = list(data_dict.items())
    base_tabs = st.tabs([key for key, _ in base_items])
    for (base_key, cases), base_tab in zip(base_items, base_tabs):
        with base_tab:
            st.metric("Linhas", f"{len(cases):,}")
            if {
                "report_reference",
                "can_be_approved",
                "__insert_utc_ts",
                "rules_approval",
            }.issubset(cases.reset_index().columns):
                has_named_index = any(name is not None for name in cases.index.names)
                display_cases = cases.reset_index() if has_named_index else cases.copy()
                date_values = pd.to_datetime(display_cases["__insert_utc_ts"], errors="coerce").dt.date.dropna()
                if date_values.empty:
                    st.info("Não há datas válidas em __insert_utc_ts para filtrar esta base.")
                    filtered_cases = display_cases
                else:
                    min_date = date_values.min()
                    max_date = date_values.max()
                    report_options = sorted(display_cases["report_reference"].dropna().astype(str).unique())
                    approval_options = sorted(display_cases["can_be_approved"].dropna().astype(str).unique())
                    rules_approval_options = sorted(
                        display_cases["rules_approval"].dropna().astype(str).unique()
                    )
                    report_filter, approval_filter, date_filter, rules_filter = st.columns(4)
                    with report_filter:
                        selected_reports = st.multiselect(
                            "Filtrar por report_reference",
                            options=report_options,
                            key=f"report_filter_{base_key}",
                        )
                    with approval_filter:
                        selected_approvals = st.multiselect(
                            "Filtrar por can_be_approved",
                            options=approval_options,
                            key=f"approval_filter_{base_key}",
                        )
                    with rules_filter:
                        selected_rules_approval = st.multiselect(
                            "Filtrar por rules_approval",
                            options=rules_approval_options,
                            key=f"rules_approval_filter_{base_key}",
                        )
                    with date_filter:
                        selected_date_range = st.date_input(
                            "Filtrar por __insert_utc_ts",
                            value=(min_date, max_date),
                            min_value=min_date,
                            max_value=max_date,
                            key=f"insert_date_filter_{base_key}",
                        )

                    if not isinstance(selected_date_range, tuple) or len(selected_date_range) != 2:
                        st.info("Selecione uma data inicial e uma data final para aplicar o filtro.")
                        continue
                    filtered_cases = _filter_cases(
                        display_cases,
                        selected_reports,
                        selected_approvals,
                        selected_rules_approval,
                        selected_date_range,
                    )
                st.metric("Cases exibidos", f"{len(filtered_cases):,} de {len(display_cases):,}")
                st.dataframe(filtered_cases, width="stretch", alt=f"Pré-visualização de {base_key}")
                st.download_button(
                    "Baixar Cases filtrados em Excel",
                    data=_create_excel(filtered_cases),
                    file_name="Cases_limpos.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    type="primary",
                    key=f"download_{base_key}",
                )
            else:
                st.dataframe(cases, width="stretch", alt=f"Pré-visualização de {base_key}")


if __name__ == "__main__":
    main()
