# -*- coding: utf-8 -*-
"""
Automatización Selenium con pandas
- Lee 'datos.xlsx' -> data_df
- Obtiene fechas únicas -> date_list
- Ingresa a www.test.com, espera 30s para login
- Por cada fecha:
    - Filtra data_df -> filtered_df
    - name_prop = 'Id propuesta' únicos concatenados + fecha
    - Navega y llena formularios por cada fila en filtered_df
"""
import os
import time
import sys
import re
import pandas as pd
import chardet
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.actions.wheel_input import ScrollOrigin
from selenium.webdriver.common.action_chains import ActionChains
import selenium.webdriver.support.expected_conditions as ec
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.select import Select
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from datetime import datetime, timedelta
from selenium import webdriver
import pyarrow.parquet as pq
import pyarrow as pa
from pathlib import Path
import logging
#import re

# Get the directory of the current script
SCRIPT_DIR = os.path.realpath(os.path.realpath(__file__))
SCRIPT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
three_levels_back = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
sys.path.insert(0, three_levels_back)
SCRIPT_DIR = Path (os.path.abspath(os.path.join(SCRIPT_DIR, "..")))
BASES_DIR = SCRIPT_DIR / "bases"

import src.webdriver_obj as wdo

class mobilexpense_obj (wdo.WebDriver_Obj):
    # ----------------------------
    # Parámetros de configuración
    # ----------------------------
    data_df = {}
    file_path = {}
    columns_used = {}
    index_list = {}
 
    def __init__ (self):
        self.name_ = "Mobilexpense"
        # Setup file
        self.setup_path_file = SCRIPT_DIR / "Setup.xlsx"
        
        self.setup_df = pd.read_excel (self.setup_path_file, sheet_name = self.name_, index_col = "Parameter", engine="openpyxl")        
        self.url_begin = self.setup_df.loc ["Url begin"].Value
        #self.url_begin = "https://xp1.mobilexpense.com/Home/login"
        
        # Setup webdriver
        params_funct = {"Webdriver": self.setup_path_file}
        self.zoom_level = self.setup_df.loc ["Zoom level"].Value
        #self.zoom_level = 50

        #'Open cases mobilexpences'
        #aux_name = 'Open cases mobilexpences'
        #self.file_path [aux_name] = self.setup_df.loc ['Base open cases mobilexpences path'].Value
        #self.columns_used [aux_name] = ["ReportId", "Employee", "LOGIN", "ReportName", "GrossAmountCC", "ApprovalStatus", "ReceiptControlStatus", "ReportRef", "ReportDate"]
        #self.index_list [aux_name] = ["Index"]
        #self.data_df [aux_name] = pd.DataFrame (columns = self.index_list [aux_name] + self.columns_used [aux_name])
        #self.data_df [aux_name].set_index (self.index_list [aux_name], inplace = True)

        #'Open cases mobilexpences'
        #aux_name = 'Casos evaluados'
        #self.file_path [aux_name] = self.setup_df.loc ['Base cases evaluated path'].Value
        #self.columns_used [aux_name] = ["report_id", "report_reference", "transaction_date", "month_year", "daycare_reference_month", "gross_amount_cc",
        #                                 "net_amount", "max_daycare_amount", "customer_category", "employee_id", "policy", "has_daycare", "has_housing", 
        #                                 "aprove_housing", "aprove_edv_housing", "aprove_guarderia", "aprove_km", "rules_approval", "can_be_approved",
        #                                 "__insert_utc_ts", "tope_actual"]
        #self.index_list [aux_name] = [""]
        #self.data_df [aux_name] = pd.DataFrame (columns = self.index_list [aux_name] + self.columns_used [aux_name])
        #self.data_df [aux_name].set_index (self.index_list [aux_name], inplace = True)

        logging.basicConfig(filename=os.path.join (SCRIPT_DIR,"app.log"), 
                            filemode='a', # 'a' to append to the file, 'w' to overwrite it each time
                            format='%(asctime)s - %(levelname)s - %(message)s',
                            level=logging.INFO
                            )

        super ().__init__(params_funct)

    def open_driver (self):
        # Set up Chrome options
        #print (self.df_setup)
        #options = webdriver.ChromeOptions()
        options = Options ()
        profile_dir = self.df_setup.loc ["Chrome profile directory"].values[0]
        profile_name = self.df_setup.loc ["Chrome profile name"].values[0]
        options.add_argument(f"--user-data-dir={profile_dir}")
        options.add_argument(f"--profile-directory={profile_name}")

        options.add_argument("--disable-notifications")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")

        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument('--disable-blink-features=AutomationControlled')

        prefs = {"download.default_directory": self.df_setup.loc ["Chrome download directory"].values[0],
                 "download.prompt_for_download": False,
                 "download.directory_upgrade": True,
                 "safebrowsing.enabled": True}

        print ("****************")
        print (prefs)
        print (self.df_setup)
        print("Download dir:", repr(self.df_setup.loc ["Chrome download directory"].values[0]))
        print ("Dir. exists: ", os.path.exists (self.df_setup.loc ["Chrome download directory"].values[0]))
        print ("****************")
 
        options.add_experimental_option("prefs", prefs)

        if not self.df_setup.loc ["Show the browser"].values [0]:
            options.add_argument("--headless=new")

        # Initialize the WebDriver with the specified service and options
        self.driver = webdriver.Chrome (options = options)

        download_dir = self.df_setup.loc["Chrome download directory"].values[0]
        self.driver.execute_cdp_cmd ("Page.setDownloadBehavior", {"behavior": "allow", "downloadPath": download_dir})
        
        self.driver.maximize_window ()

    def load_data_parquet (self, params_dict):
        path_file = BASES_DIR / f"{params_dict ["Base"]}.parquet"
        print ("==> Carregando base ", params_dict ["Base"], " in path ", path_file)
        if os.path.exists (path_file):
            #self.data_df [params_dict ["Base"]] = pq.read_pandas (self.file_path [params_dict ["Base"]], columns = self.columns_used [params_dict ["Base"]]).to_pandas ()            
            self.data_df [params_dict ["Base"]] = pd.read_parquet (path_file)            
            #self.data_df [params_dict ["Base"]] = self.data_df [self.columns_used [params_dict ["Base"]]]
        else:
            if len (self.index_list [params_dict ["Base"]]) > 0:
                self.data_df [params_dict ["Base"]]= pd.DataFrame (columns = self.columns_used [params_dict ["Base"]] + self.index_list [params_dict ["Base"]])
                self.data_df [params_dict ["Base"]].set_index (self.index_list [params_dict ["Base"]], inplace = True)
            else:
                self.data_df [params_dict ["Base"]]= pd.DataFrame (columns = self.columns_used [params_dict ["Base"]] + self.index_list [params_dict ["Base"]])

    # ++++ Carregar a data da última atualização
    def save_to_parquet (self, params_dict):
        preserve_index = True
        if "Inore index" in params_dict.keys ():
            preserve_index = params_dict ["Preserve index"]

        path_file = BASES_DIR / f"{params_dict ["Base"]}.parquet"
        print (f"save_to_parquet: Salvando base {params_dict ["Base"]} em {path_file}")
        table_parquet = pa.Table.from_pandas (self.data_df [params_dict ["Base"]], preserve_index = preserve_index)
        pq.write_table (table_parquet, path_file)

    def goto_page (self):
        # Abre o navegador
        self.open_driver ()

        ## Vai ao portal
        self.go ({"Url": self.url_begin})

        # driver.switch_to.frame(0)

        ## Espera fazer login
        self.wait_login ({"Iframe": "#SessionCheck", "Wait time": 180})

        ## Escolhe o perfil controller
        self.click_over ({"Contains": "//a[contains(@class, sbSelector)]"})
        self.click_over ({"Contains": f"//ul[contains(@class,'sbOptions')]//a[normalize-space()='Controller']"})

        ## Sair do iframe
        self.driver.switch_to.default_content()

    def goto_expenses (self):
        ## Entra no iframe of application
        self.goto_iframe ({"Iframe": "#applicationFrame"})        

        # Set zoom to site
        self.set_zoom_after_element ({"Selector": "#link-1"})

        # Clica em expense note search
        self.click_over ({"Selector": "#link-1"})

        # Seleciona do Approval os casos Closed (dropmenu)
        self.select_by_text_dropmenu ({"Selector": "#XStatus", "Value": "Closed"})
        
        # Seleciona do Control os casos Open-Scanned (dropmenu)
        self.select_by_text_dropmenu ({"Selector": "#YStatus", "Value": "Open-Scanned"})

    def get_and_format_downloaded_data (self):
        # Path to dowloaded file
        path_file = os.path.join (self.df_setup.loc ["Chrome download directory"].Value, self.downloaded_file_name)

        # Test file codification
        codification_file = ""
        with open(path_file, 'rb') as f:
            codification_file = chardet.detect(f.read())

        # Read data
        used_columns = ["ReportId", "Employee", "LOGIN", "ReportName", "GrossAmountCC", "ApprovalStatus", "ReceiptControlStatus", "ReportRef", "ReportDate"]
        downloaded_df= pd.read_csv (path_file, sep = "\t", encoding = codification_file ["encoding"], usecols = used_columns)

        # Limpa a columna login
        downloaded_df ["LOGIN"] = downloaded_df ["LOGIN"].str.replace(r'.*\.(\d{8}).*', r'\1', regex=True).astype ('int64')

        # Set index and add status and Request Approvable requirements columns
        downloaded_df ["Index"] = downloaded_df["ReportId"].astype(str) + downloaded_df["ReportDate"]
        downloaded_df.set_index ("Index", inplace = True)
        downloaded_df ["Approvable requirements"] = ""
        downloaded_df ["All requirements are acceptable"] = False
        self.data_df ["Open cases mobilexpences"] = downloaded_df

        # Guarda o arquivo descarregado e a base de descarregados
        new_file_name = "Cases_downloaded.csv"
        path_file_n = os.path.join (self.df_setup.loc ["Chrome download directory"].Value, new_file_name)
        if os.path.exists (path_file_n):
            os.remove (path_file_n)
        os.rename (path_file, path_file_n)
        self.downloaded_file_name = new_file_name

        # Save in parquet
        self.save_to_parquet ({"Base": "Open cases mobilexpences"})
        
    # ++
    def dowload_cases (self):
        # Abre o site 
        self.goto_page ()
        
        ## Vai ao portal na seção expenses
        self.goto_expenses ()

        # Coleta os dados
        self.click_over ({"Selector": "#csvSearchButton"})

        # Pega o nome do arquivo gerado
        self.downloaded_file_name = self.get_text ({"Selector": "#tdcsv > table > tbody > tr > td:nth-child(3) > a"}) + ".csv"
    
        # Faz click para descarregar
        self.click_over ({"Selector": "#tdcsv > table > tbody > tr > td:nth-child(3) > a"})
    
        # Espera que a descarga seja finalizada
        self.wait_download ({"File name": self.downloaded_file_name, "Wait time": 120})

        # Carrega e Formata os dados descarregados
        self.get_and_format_downloaded_data ()

        # Fecha o chrome
        self.close_driver ()

    # ++
    def wait_end_loading_image (self):
        time.sleep (0.5)
        aux_time = 0
        step_time = 0.1
        try:
            #elem = self.wait_element ({"Selector": "#loadingImageHolder", "Wait time": 1})
            elem = self.wait_element ({"Selector": "#syncOverlay", "Wait time": 1})
        except:
            # Corrigue os casos quando faltou dar um enter
            self.press_enter ({"Selector": "#Reference"})
            try:
                #elem = self.wait_element ({"Selector": "#loadingImageHolder", "Wait time": 1})
                elem = self.wait_element ({"Selector": "#syncOverlay", "Wait time": 1})
            except:
                pass
            time.sleep (0.5)

        end_loaded = False
        while aux_time < 30:
            if elem.is_displayed ():
                aux_time += step_time
                time.sleep (step_time)
            else:
                end_loaded = True
                break
        return end_loaded


    def approval_request (self, cases_df):
        # Filtra da base os casos de kilometer
        # Casos com os valores Open ou Scaned na columna Receipt Controller Status
        #cases_df = self.filter_case_with_user_in_base ()
 
        # Abre o site 
        self.goto_page ()

        # Avalia caso por caso
        for i_ind, row_ind in cases_df.iterrows ():
            self.evaluate_one_case ({"Report ref": row_ind ["ReportRef"], "ID user": row_ind ["LOGIN"]})

    def evaluate_one_case (self, params_dict):
        output_dict = {}
        # Vai ao portal na seção expenses
        self.goto_expenses ()

        # Pego o código do Expense note.
        expenses_note = params_dict ["Report ref"]
        user_ref =  params_dict ["ID user"]

        # Salva no log file as informações do report ref e do usuario
        logging.info ("="*60)
        logging.info ("ReportRef:\n%s", "\t" + expenses_note)
        logging.info ("User ID:\n%s", "\t" + str (user_ref))
        #filter_1 = self.data_df ["User request groups"] ["Legajo"] == user_ref
        #logging.info ("User groups:\n%s", "\t" + self.data_df ["User request groups"].loc [filter_1, "Politica"])

        # Coloca o valor de Report ref na caixa “Expense note” e faz click em Search
        self.set_value ({"Selector": "#Reference", "Value": expenses_note})
        time.sleep (0.5)
        self.press_enter ({"Selector": "#Reference"})

        # Entra para ver a informação do caso
        # Espera carregar
        self.wait_end_loading_image ()
        
        # Entra para ver os detalhes da solicitude
        self.click_over ({"Selector": "#ReportList > tbody > tr.trx > td:nth-child(4) > a"})

        # Vai no final da pagina
        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        
        # Ve os valores nos campos descriptivos
        tabela_sol = self.wait_element ({"Selector": "#tblTransactionList"})

        # Lista as linhas da tabela
        lines_sol = tabela_sol.find_elements(By.TAG_NAME, "tr")


        # Faze a avaliações de todos os requerimentos
        # Lista os valores por columna ignorando as vazias
        #list_request_evaluated = self.do_lines_avaliation ({"Request list": lines_sol, "ID user": user_ref})
        list_request_evaluated = self.take_items_request ({"Request list": lines_sol, "ID user": user_ref})
        #output_dict ["Approvable requirements"] = str (len (list_request_evaluated [list_request_evaluated ["Validation"]])) + "/" + str (len (list_request_evaluated))   
        

        # Save in log file
        logging.info ("Items:\n%s", list_request_evaluated [["Request", "Validation"]].to_string())

        # Ve si todos o items foram aceitos e aprova
        # Se é o caso selecciona os items a aprovar e asigna as cutoas
        #output_dict ["All requirements are acceptable"] = self.aprove_item ({"Request list evaluated": list_request_evaluated})
        self.set_aprove_item ({"Request list evaluated": list_request_evaluated})

        print (list_request_evaluated)
        time.sleep (5)

        ## Sair dos iframe para iniciar o proceso novamente
        self.driver.switch_to.default_content()

        # Save in log file
        logging.info ("")

    def take_items_request (self, params_dict):
        # Lista os requerimentos ignorando os vazios
        Cols_item = ["Request", "Validation", "Element Received", "Element Valid"]
        request_list_evaluated = pd.DataFrame (columns= Cols_item)
        logging.info ("+"*60)
        for line_ind in params_dict ["Request list"]:
            val_sol = line_ind.find_elements(By.TAG_NAME, "td")
            if (len (val_sol) > 8):
                aux_index = val_sol [2].text
                request_list_evaluated.loc  [aux_index] = [re.sub (r"^\d* *\- *(.*)",r"\1",val_sol [6].text.split ("\n")[0]),
                                                    False,
                                                    val_sol [12],
                                                    val_sol [13]
                                                    ]
                # Faze a avaliação
                #request_list_evaluated.at  [aux_index, "Validation"] = self.evaluate_request ({"Request": request_list_evaluated.at  [aux_index, "Request"], "ID user": params_dict ["ID user"]})

        # Save in log file
        logging.info ("+"*60)

        return request_list_evaluated


    def set_aprove_item (self, params_dict):
        ## Colocar If de avaliação
        # Valida received
        for ind_i, row_i in params_dict ["Request list evaluated"].iterrows ():
            checkbox_sol = row_i ["Element Received"].find_elements (By.CSS_SELECTOR, "input[type='checkbox']")
            if not checkbox_sol [0].is_selected():
                checkbox_sol [0].click()
            # Valida Aproval
            checkbox_sol = row_i ["Element Valid"].find_elements (By.CSS_SELECTOR, "input[type='checkbox']")
            if not checkbox_sol [0].is_selected():
                checkbox_sol [0].click()
        return True


    """
    # ++
    def appen_downloaded_to_historical (self):
        # Ver si o historico existe. Caso que não, cria este. Caso contrario, carrega
        self.load_data_parquet ({"Base": self.name_})

        # Filtra os dados novos e agrega no historico
        if  self.data_df [self.name_].empty:
            if not self.data_df ["Cases to treat"].empty:
                self.data_df [self.name_] = self.data_df ["Cases to treat"]
        else:
            if not self.data_df ["Cases to treat"].empty:
                filter_1 = ~ self.data_df ["Cases to treat"].index.isin (self.data_df [self.name_])
                self.data_df [self.name_] = pd.concat ([self.data_df ["Cases to treat"] [filter_1], self.data_df [self.name_]])

        # Guardar parquet
        self.save_to_parquet ({"Base": self.name_, "Preserve index": True})
    """

 
    """
    # ++
    def approvate_kilometer (self):
        # Filtra casos
        # Entra en el portal
        # Ve caso por caso
        # Ve requerimiento por requerimiento
        # Aproba el requrimento
        # Aproba o caso

        # Casos com os valores Open ou Scaned na columna Receipt Controller Status
        cases_df = self.data_df ["Casos por aprobar"]

        # **** Filtrar los kilometers

        #cases_df = self.filter_case_with_user_in_base ()

        # Abre o site 
        self.goto_page ()

        # Avalia caso por caso
        for i_ind, row_ind in cases_df.iterrows ():
            self.evalouate_one_case ({"Report ref": row_ind ["ReportRef"], "ID user": row_ind ["LOGIN"]})
    """

    """
    def update_base_user_groups_request_from_list_df (self, params_dict):
        aux_name = "User request groups"
        self.data_df [aux_name] = pd.DataFrame (columns = self.index_list [aux_name] + self.columns_used [aux_name])
        self.data_df [aux_name].set_index (self.index_list [aux_name], inplace = True)

        list_df = params_dict ["Dataframes"]
        for df_i in list_df:
            if not df_i.empty:
                # Tira espaços no inicio e no final do nome de cada coluna
                df_i.columns = df_i.columns.str.strip ()

                # Tira espaços no inicio e final dos dados tipo Object
                df_i = df_i.apply(lambda x: x.str.strip() if x.dtype == "object" else x)

                # Desconsidera linhas com lejado nan o #N/A
                # *** Revisar ***
                df_i = df_i.dropna (subset = ['Legajo'])
                df_i = df_i [df_i ['Legajo'] != "#N/A"]

                # Agrega a abase
                if self.data_df [aux_name].empty:
                    if not df_i.empty:
                        self.data_df [aux_name] = df_i
                else:
                    if not df_i.empty:
                        self.data_df [aux_name] = df_i
                    else:
                        self.data_df [aux_name] = pd.concat ([self.data_df [aux_name], df_i])

        # Agrupa por usuario e grupo de requerimentos, para eliminar duplicados
        self.data_df [aux_name] = self.data_df [aux_name].groupby (["Legajo", "Politica"]).min ().reset_index ()

        # Deixa só as columnas relevantes
        self.data_df [aux_name] = self.data_df [aux_name] [self.columns_used [aux_name]]

        # Salva a nova base em formato parquet
        table_parquet = pa.Table.from_pandas (self.data_df [aux_name], preserve_index = True)
        pq.write_table (table_parquet, self.file_path [aux_name])
    """

    """
    def update_base_from_excel (self, params_dict):
        name_aux = params_dict ["Base"]
        # Carrega o excel
        input_df = pd.read_excel (params_dict ["File input"])

        # Tira espaços no inicio e no final do nome de cada coluna
        input_df.columns = input_df.columns.str.strip ()

        # Tira espaços no inicio dos dados tipo Object
        input_df = input_df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)

        # Desconsidera linhas com Index nan
        input_df = input_df.dropna (subset = self.index_list [name_aux])

        # Desconsidera linhas com lejado nan o #N/A
        # *** Revisar ***
        input_df = input_df.dropna (subset = ['Legajo'])
        input_df = input_df [input_df ['Legajo'] != "#N/A"]

        # Set index
        input_df.set_index (self.index_list [name_aux], inplace = True)

        # Set base data
        self.data_df [name_aux] = input_df

        # Salva a nova base em formato parquet
        table_parquet = pa.Table.from_pandas (self.data_df [name_aux], preserve_index = True)
        pq.write_table (table_parquet, self.file_path [name_aux])
    """

    """
    def evaluate_request (self, params_dict):
        # Pega os grupos correspondientes ao requerimento
        filter_1 = self.data_df ["Request groups"].index == params_dict ["Request"]
        groups_request = self.data_df ["Request groups"] [filter_1]
        groups_request = groups_request ["Group"]

        # Pega os grupos do usuario
        filter_1 = self.data_df ["User request groups"] ["Legajo"] == params_dict ["ID user"]
        groups_user = self.data_df ["User request groups"] [filter_1]
        groups_user = self.data_df ["User request groups"] ["Politica"].unique ()

        # Ve se o usuario pertence a algum grupo do request e retorna True o False dependendo do caso
        filter_1 = groups_user.isin (groups_request)
        inter_groups = groups_user [filter_1]

        # Save in log file
        logging.info ("-"*60)
        logging.info ("Request and user:\n%s", str (params_dict))
        logging.info ("Request groups:\n%s", groups_request.to_string ())
        logging.info ("User groups:\n%s", ",".join (groups_user))
        logging.info ("Intersection groups:\n%s", inter_groups.to_string ())
        logging.info ("-"*60)
 
        # Se o usuario pertence aum grupo aceita o requerimento
        if inter_groups.empty:
            return False, None
        else:
            return True, inter_groups
    """    
            
    """
    def do_lines_avaliation (self, params_dict):
        # Lista os requerimentos ignorando os vazios
        Cols_item = ["Request", "Validation", "Element Received", "Element Valid"]
        request_list_evaluated = pd.DataFrame (columns= Cols_item)
        logging.info ("+"*60)
        for line_ind in params_dict ["Request list"]:
            val_sol = line_ind.find_elements(By.TAG_NAME, "td")
            if (len (val_sol) > 8):
                aux_index = val_sol [2].text
                request_list_evaluated.loc  [aux_index] = [re.sub (r"^\d* *\- *(.*)",r"\1",val_sol [6].text.split ("\n")[0]),
                                                    False,
                                                    val_sol [12],
                                                    val_sol [13]
                                                    ]
                # Faze a avaliação
                request_list_evaluated.at  [aux_index, "Validation"] = self.evaluate_request ({"Request": request_list_evaluated.at  [aux_index, "Request"], "ID user": params_dict ["ID user"]})

        # Save in log file
        logging.info ("+"*60)

        return request_list_evaluated
    """

    """
    def set_quotas_and_aproved (self, params_dict):
        if params_dict ["Request list evaluated"]["Validation"].all ():

            # Ve se temos casos com quotas
            ## Asigna quotas
            ### Filtro a base user request groups, para os casos de requerimentos com quota
            # Request	Group	Have Quota	Description
            # filter_1 = self.data_df ["Request groups"] ["Have Quota"]
            # req_group = self.data_df ["Request groups"] [filter_1]
        
            ### Evaluo se temos algum requerimento com quota
            # filter_1 = params_dict ["Request list evaluated"] ["Request"].isin (req_group ["Request"])
 
            ## Colocar If de avaliação
            # Valida received
            for ind_i, row_i in params_dict ["Request list evaluated"].iterrows ():
                checkbox_sol = row_i ["Element Received"].find_elements (By.CSS_SELECTOR, "input[type='checkbox']")
                if not checkbox_sol [0].is_selected():
                    checkbox_sol [0].click()
                # Valida Aproval
                checkbox_sol = row_i ["Element Valid"].find_elements (By.CSS_SELECTOR, "input[type='checkbox']")
                if not checkbox_sol [0].is_selected():
                    checkbox_sol [0].click()
            time.sleep (3)
            return True
        else:
            return False
    """

    """
    def filter_case_with_user_in_base (self):
        # Filtra da base os casos de kilometer
        # Casos com os valores Open ou Scaned na columna Receipt Controller Status
        
        # Carrega a base PDD
        self.load_data_parquet ({"Base": "User request groups"})

        # Filtra a base PDD_PPI_B2B para os usuarios a considerar
        filter_1 = self.data_df ["User request groups"]["Legajo"].isin (self.data_df ["Cases to treat"]["LOGIN"])    
        self.data_df ["User request groups"] = self.data_df ["User request groups"][filter_1]

        # Pega os casos a considerar
        filter_1 = self.data_df ["Cases to treat"]["LOGIN"].isin (self.data_df ["User request groups"]["Legajo"])    
        cases_df  = self.data_df ["Cases to treat"][filter_1]

        return cases_df
    """

    """
    def evalouate_one_case (self, params_dict):
        output_dict = {}
        # Vai ao portal na seção expenses
        self.goto_expenses ()

        # Pego o código do Expense note.
        expenses_note = params_dict ["Report ref"]
        user_ref =  params_dict ["ID user"]

        # Salva no log file as informações do report ref e do usuario
        logging.info ("="*60)
        logging.info ("ReportRef:\n%s", "\t" + expenses_note)
        logging.info ("User ID:\n%s", "\t" + str (user_ref))
        filter_1 = self.data_df ["User request groups"] ["Legajo"] == user_ref
        logging.info ("User groups:\n%s", "\t" + self.data_df ["User request groups"].loc [filter_1, "Politica"])

        # Coloca o valor de Report ref na caixa “Expense note” e faz click em Search
        self.set_value ({"Selector": "#Reference", "Value": expenses_note})
        time.sleep (0.5)
        self.press_enter ({"Selector": "#Reference"})

        # Entra para ver a informação do caso
        # Espera carregar
        self.wait_end_loading_image ()
        
        # Entra para ver os detalhes da solicitude
        self.click_over ({"Selector": "#ReportList > tbody > tr.trx > td:nth-child(4) > a"})

        # Vai no final da pagina
        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        
        # Ve os valores nos campos descriptivos
        tabela_sol = self.wait_element ({"Selector": "#tblTransactionList"})

        # Lista as linhas da tabela
        lines_sol = tabela_sol.find_elements(By.TAG_NAME, "tr")

        # Faze a avaliações de todos os requerimentos
        # Lista os valores por columna ignorando as vazias
        list_request_evaluated = self.do_lines_avaliation ({"Request list": lines_sol, "ID user": user_ref})
        output_dict ["Approvable requirements"] = str (len (list_request_evaluated [list_request_evaluated ["Validation"]])) + "/" + str (len (list_request_evaluated))   

        # Save in log file
        logging.info ("Items:\n%s", list_request_evaluated [["Request", "Validation"]].to_string())

        # Ve si todos o items foram aceitos e aprova
        # Se é o caso selecciona os items a aprovar e asigna as cutoas
        output_dict ["All requirements are acceptable"] = self.set_quotas_and_aproved ({"Request list evaluated": list_request_evaluated})
        
        # **** Revisar
        # Salva os status de avaliação
        aux_name = "Cases to treat"
        filter_1 = self.data_df [aux_name] ["LOGIN"] == user_ref
        filter_1 = filter_1 & (self.data_df [aux_name] ["ReportRef"] == expenses_note)
        self.data_df [aux_name].loc [filter_1, ["Approvable requirements"]] = output_dict ["Approvable requirements"]
        self.data_df [aux_name].loc [filter_1, ["All requirements are acceptable"]] = output_dict ["All requirements are acceptable"]
        self.save_to_parquet ({"Base": aux_name})

        ## Sair dos iframe para iniciar o proceso novamente
        self.driver.switch_to.default_content()

        # Save in log file
        logging.info ("")

    """

if __name__ == "__main__":
    try:
        mobi_t = mobilexpense_obj ()
        #mobi_t.update_base_from_excel ({"Base": "Base user request groups path", "File input": "C:/Users/99848867/Downloads/Mobile/PDD_PPI_B2B.xlsx"})
        mobi_t.dowload_cases ()
        #mobi_t.approval_kilometer ()

    except KeyboardInterrupt:
        print("Ejecución interrumpida por el usuario.")
        sys.exit(1)
        