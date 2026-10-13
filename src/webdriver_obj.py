#!/usr/bin/env python
from selenium.common.exceptions import UnexpectedAlertPresentException
from selenium.webdriver.common.actions.wheel_input import ScrollOrigin
from selenium.webdriver.common.action_chains import ActionChains
import selenium.webdriver.support.expected_conditions as ec
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.select import Select
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from datetime import datetime, timedelta
import pyarrow.parquet as pq
from selenium import webdriver
import pandas as pd
import threading
import platform
import time
import re
import os
import traceback
import numpy as np


class WebDriver_Obj:
    def __init__ (self):
        self.driver = None
        self.show_browser = True
        self.setup_file = "Setup.xlsx"
        self.setup_sheet = "Webdriver"
        self.setup_index = "Parameter"
        self.tables = pd.DataFrame ()
        self.values_taken = {}
        self.actions_dict = {}
        self.roteros = {}
        self.df_setup = pd.DataFrame ()
        self.setup ()

    def __init__ (self, params_dict):
        self.driver = None
        self.show_browser = True
        self.setup_file = params_dict ["Webdriver"]
        self.setup_sheet = "Webdriver"
        self.setup_index = "Parameter"
        self.tables = pd.DataFrame ()
        self.values_taken = {}
        self.actions_dict = {}
        self.roteros = {}
        self.df_setup = pd.DataFrame ()
        self.setup ()

    def setup (self):
        self.df_setup = pd.read_excel (self.setup_file,
                                       sheet_name = self.setup_sheet,
                                       index_col = self.setup_index)

        self.actions_dict ["Go to site"] = {"Function": self.go}
        self.actions_dict ["Load table"] = {"Function": self.load_table}
        self.actions_dict ["Test if element exist"] = {"Function": self.element_exist}
        self.actions_dict ["Set value"] = {"Function": self.set_value}
        self.actions_dict ["Set value from column"] = {"Function": self.set_value}
        self.actions_dict ["Reset value"] = {"Function": self.reset_value}
        self.actions_dict ["Clck over"] = {"Function": self.click_over}
        self.actions_dict ["Press enter"] = {"Function": self.press_enter}
        self.actions_dict ["Take value"] = {"Function": self.take_value}
        self.actions_dict ["Do rotero"] = {"Function": self.do_rotero}
        self.actions_dict ["Wait login"] = {"Function": self.wait_login}
        self.actions_dict ["Do rotero with table"] = {"Function": self.do_rotero_with_table}

    def load_table (self, params_dict):
        index_tb = None
        if "Index" in params_dict.keys ():
            index_tb = params_dict ["Index"]
        columns_tb = None
        if "Columns" in params_dict.keys:
            columns_tb = params_dict ["Columns"]
        # format_tb = params_dict ["Format"]

        # self.tables [params_dict ["Table name"]] = pd.read_excel (params_dict ["Path to table"], index_col = index_tb)
        return pd.read_excel (params_dict ["Path to table"], index_col = index_tb, sheet_name = params_dict ["Sheet table"])

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

    def go (self, params_dict):
        self.driver.get (params_dict ["Url"])

    def close_driver (self):
        self.driver.close ()

    def get_driver (self):
        return self.driver
    
    """
    def wait_element_exist (self, params_dict):
        print (" ==> Test if element exist", params_dict)
        wait_time_aux = 0
        delta_time = 0.1
        while (not self.element_exist (params_dict)) and wait_time_aux < self.df_setup.loc ["Waiting time for response per element"].values[0]:
            time.sleep (delta_time)
            wait_time_aux += delta_time
    """
            
    def element_exist (self, params_dict):
        by_for = None
        path_t = None
        if "Xpath" in params_dict.keys ():
            by_for = By.XPATH
            path_t = params_dict ["Xpath"]
        elif "Selector" in params_dict.keys ():
            by_for = By.CSS_SELECTOR
            path_t = params_dict ["Selector"]
        elif "Contains" in params_dict.keys ():
            by_for = By.XPATH
            path_t = params_dict ["Contains"]
        elif "Iframe" in params_dict.keys ():
            by_for = By.CSS_SELECTOR
            path_t = params_dict ["Iframe"]

        try:

            self.driver.find_element (by_for, path_t)
            return True
        except Exception:
            #print("Element " + path_t + " search by " + by_for + "do not finded")
            return False

    def wait_element (self, params_dict):
        by_for = None
        path_t = ""
        if "Xpath" in params_dict.keys ():
            by_for = By.XPATH
            path_t = params_dict ["Xpath"]
        elif "Selector" in params_dict.keys ():
            by_for = By.CSS_SELECTOR
            path_t = params_dict ["Selector"]
        elif "Contains" in params_dict.keys ():
            by_for = By.XPATH
            path_t = params_dict ["Contains"]
        elif "Iframe" in params_dict.keys ():
            by_for = By.CSS_SELECTOR
            path_t = params_dict ["Iframe"]
        else:
            return None

        wait_time_aux = 0
        delta_time = 0.1
        wait_until = self.df_setup.loc ["Waiting time for response per element"].values[0]
        if "Wait time" in params_dict.keys ():
            wait_until = params_dict ["Wait time"]

        print (" ==> Test if element exist", params_dict, " for ", wait_until, " seconds")
        while (not self.element_exist (params_dict)) and wait_time_aux < wait_until:
            time.sleep (delta_time)
            wait_time_aux += delta_time

        elem = None
        print (" ==> Wait that element is displayed", params_dict, " for ", wait_until, " seconds")
        if "Iframe" in params_dict.keys ():
            elem = WebDriverWait (self.driver, wait_until).until(
                ec.frame_to_be_available_and_switch_to_it ((by_for, path_t))
            )
            self.driver.switch_to.parent_frame ()
        else:
            elem = WebDriverWait(self.driver, wait_until).until(
                ec.presence_of_element_located((by_for, path_t)) and
                ec.element_to_be_clickable((by_for, path_t)))        
        return elem

    """
    def wait_and_get_element (self, params_dict):
        elem = None
        by_for = None
        path_t = ""
        if "Xpath" in params_dict.keys ():
            by_for = By.XPATH
            path_t = params_dict ["Xpath"]
        elif "Selector" in params_dict.keys ():
            by_for = By.CSS_SELECTOR
            path_t = params_dict ["Selector"]
        elif "Contains" in params_dict.keys ():
            by_for = By.XPATH
            path_t = params_dict ["Contains"]
            print ("++++", path_t)
        else:
            return elem
        
        elem = WebDriverWait(self.driver, self.df_setup.loc ["Waiting time for response per element"].values[0]).until(
            ec.presence_of_element_located((by_for, path_t)) and
            ec.element_to_be_clickable((by_for, path_t)))

        print (" ==> Find element", elem.get_property ("id"))

        return elem
    """

    def set_value (self, params_dict):
        elem = self.wait_element (params_dict)
        #elem.click ()
        elem.clear ()
        elem.send_keys("" if params_dict ["Value"] is None else str(params_dict ["Value"]))
        #elem.send_keys (params_dict ["Value"])

    def send_keys (self):
        elem = self.wait_element (params_dict)
        elem.send_keys("" if params_dict ["Value"] is None else str(params_dict ["Value"]))

    def reset_value (self, params_dict):
        elem = self.wait_element (params_dict)
        elem.click ()
        elem.clear ()

    def select_by_text_dropmenu (self, params_dict):
        """
        Selecciona por texto visible. Si el match exacto falla, intenta un match por
        contención (case-insensitive) como respaldo.
        """
        elem = self.wait_element (params_dict)

        #sel_el = WebDriverWait(self.driver, timeout).until(
        #    EC.presence_of_element_located((By.CSS_SELECTOR, css_selector))
        #)
        #sel_el.click()

        sel = Select(elem)
        try:
            sel.select_by_visible_text(params_dict ["Value"])
        except Exception:
            # Fallback: buscar opción que contenga el texto
            #opts = [o.text.strip() for o in sel.options]
            opts = [o.text for o in sel.options]
            match = None
            count_a = 0
            vt_norm = (params_dict ["Value"] or "").strip().lower()
            for o in opts:
                if vt_norm and (vt_norm in o.strip().lower()):
                    match = count_a
                    break
                count_a += 1
            if match is not None:
                #sel.select_by_visible_text(match)
                sel.select_by_index(match)
            else:
                raise ValueError(
                    f"No se encontró opción '{params_dict ["Value"]}' (ni similar). "
                    f"Opciones disponibles: {opts}"
                )
        return sel

    def click_over (self, params_dict):
        elem = self.wait_element (params_dict)
        elem.click ()

    def press_enter (self, params_dict):
        elem = self.wait_element (params_dict)
        elem.send_keys(Keys.RETURN)

    def take_value (self, params_dict, name_vl):
        self.values_taken [name_vl] = self.get_text (params_dict)

    def get_text (self, params_dict):
        elem = self.wait_element (params_dict)
        return elem.text

    """ # Query and select value
    def query_and_select_value (self, elem_xpath_dict, elem_value):

        # Open query
        elem_xpath = elem_xpath_dict['Open query']
        self.click_over (elem_xpath)

        # Set value for query
        elem_xpath = elem_xpath_dict['Cell crit']
        self.set_value (elem_xpath, elem_value)

        # Do the query
        elem_xpath = elem_xpath_dict['Do query']
        self.click_over (elem_xpath)

        # Select element of query
        elem_xpath = elem_xpath_dict['Select cell']
        self.click_over (elem_xpath)
    """
    """ # ScrolHorizoOvertable
    def ScrollHorizOverTable (self, query_cell_xpath, num_col_to):
        cell_xpath = '//*[contains (@id, "' + query_cell_xpath + str(num_col_to) + '"]'
        self.click_over (cell_xpath)

        num_steps = num_col_to - self.now_col_table

        while num_steps > 0:
            ActionChains (self.driver).send_keys(Keys.ARROW_RIGHT).perform()
            num_steps = num_steps - 1

        while num_steps < 0:
            ActionChains (self.driver).send_keys(Keys.ARROW_LEFT).perform()
            num_steps = num_steps + 1
        self.now_col_table = self.now_col_table + num_steps
    """

    def take_parameters_action (self, param_dict):
        print (param_dict ["Index"] + " -> " + param_dict ["Action"])

        # Take parameters
        param_output = {}
        #if self.actions_dict [param_dict ["Action"]] ["Parameters type"] == "Unique":
        for k_dp, v_dp in param_dict ["Action parameters"].iterrows ():
            param_output [k_dp] = v_dp.values[0]
        if param_dict ["Action"] == "Do rotero":
            param_output ["Rotero"] = param_dict ["Rotero"]

        return param_output

    def load_rotero (self, params_dict):
        rotero_name = params_dict ["Rotero"] + " - " + params_dict ["Tab"]
        rotero_df = None
        if rotero_name not in self.roteros:
            dtype_def = {"Id": str, "Action": str, "Input": str, "Parameter": str, "Value": str}
            rotero_df = pd.read_excel (params_dict ["Rotero"],
                                       sheet_name = params_dict ["Tab"],
                                       index_col = [0, 1, 2],
                                       dtype = dtype_def)
            self.roteros [rotero_name] = rotero_df

    def execute_actions (self, params_dict):
        for ind_lv0 in params_dict ["Rotero data"].index.get_level_values(0).unique ():
            # Take parameters
            action_name = params_dict ["Rotero data"].loc [ind_lv0].index.get_level_values (0).unique () [0]
            params_act = {"Action": action_name,
                          "Action parameters": params_dict ["Rotero data"].loc [(ind_lv0, action_name)],
                          "Rotero": params_dict ["Rotero"],
                          "Index": ind_lv0}

            param_func = self.take_parameters_action (params_act)

            # Do action
            use_function = self.actions_dict [params_act ["Action"]] ["Function"]
            use_function (param_func)
            time.sleep (params_dict ["Sleep beteewn actions"])

    def execute_actions_with_table (self, params_dict):
        # List the actions to do
        list_actions_to_do = []
        for ind_lv0 in params_dict ["Rotero data"].index.get_level_values(0).unique ():
            # Take parameters
            action_name = params_dict ["Rotero data"].loc [ind_lv0].index.get_level_values (0).unique () [0]
            params_act = {"Action": action_name,
                          "Action parameters": params_dict ["Rotero data"].loc [(ind_lv0, action_name)],
                          "Rotero": params_dict ["Rotero"],
                          "Index": ind_lv0}

            list_actions_to_do.append ({"Action": action_name,
                                        "Function": self.actions_dict [params_act ["Action"]] ["Function"],
                                        "Parameters": self.take_parameters_action (params_act)})

        # Run over rows and do actions
        for ind_r, row_r in params_dict ["Table"].iterrows ():
            # Run actions for row
            for act_i in list_actions_to_do:
                # If action is Set value from table set the value from the right column
                if act_i ["Action"] == "Set value from table":
                    act_i ["Parametes"] ["Value"] = row_r [act_i ["Parametes"] ["Column"]]

                # Execute the action
                act_i ["Function"] (act_i ["Parameters"])

                time.sleep (params_dict ["Sleep beteewn actions"])

            # param_func = self.take_parameters_action (params_act)
            #
            # # Do action
            # use_function = self.actions_dict [params_act ["Action"]] ["Function"]
            # use_function (param_func)
            # time.sleep (params_dict ["Sleep beteewn actions"])

    def do_rotero (self, params_dict):
        # Load rotero
        self.load_rotero (params_dict)
        rotero_name = params_dict ["Rotero"] + " - " + params_dict ["Tab"]

        # run over actions
        params_func = {"Rotero": params_dict ["Rotero"],
                       "Rotero data": self.roteros [rotero_name],
                       "Sleep beteewn actions": params_dict ["Sleep beteewn actions"]
                       }
        self.execute_actions (params_func)

    def do_rotero_with_table (self, params_dict):
        # Load data table
        params_func = {"Index": params_dict ["Index"],
                       "Columns": params_dict ["Columns"],
                       "Path to table": params_dict ["Path to table"]}

        table_df = self.load_table (params_func)

        # Load rotero
        self.load_rotero (params_dict)

        # run actions
        rotero_name = params_dict ["Rotero"] + " - " + params_dict ["Tab"]
        params_func = {"Rotero": params_dict ["Rotero"],
                       "Rotero data": self.roteros [rotero_name],
                       "Table": table_df,
                       "Sleep beteewn actions": params_dict ["Sleep beteewn actions"]
                       }

        self.execute_actions_with_table (params_func)

    def wait_login_cond (self, params_dict):
        time.sleep (1)
        if self.element_exist ({"Xpath": params_dict ["Do when show element"]}):
            print ("   Have to do login")
            wait_time = timedelta (seconds = int (params_dict ["Wait for"]))
            wait_elem_to_end = params_dict ["Wait element"]

            params_wait = {"Xpath": wait_elem_to_end}
            start_time = datetime.now ()

            time.sleep (1)
            time_now = datetime.now ()
            while (not self.element_exist (params_wait)) and ((time_now - start_time) < wait_time):
                time.sleep (1)
                if (time_now - start_time) >= wait_time:
                    text_output = ("The time for login finished, login unsuceful")
                    exit (text_output)
                time_now = datetime.now ()
        else:
            print ("   Login done")

    def wait_login (self, params_dict):
        """Espera a que el elemento que indica que fez login e esta no site sea clickable"""
        print ("=> Waiting for longin")
        elem = self.wait_element (params_dict)
        """
        by_for = None
        path_t = ""
        elem = None
        if "Xpath" in params_dict.keys ():
            by_for = By.XPATH
            path_t = params_dict ["Xpath"]
        elif "Selector" in params_dict.keys ():
            by_for = By.CSS_SELECTOR
            path_t = params_dict ["Selector"]
        else:
            return False

        try:
            print ("=> Waiting for longin")
            self.wait_element (params_dict)
            
            elem = WebDriverWait(self.driver, params_dict ["Wait time"]).until(           
                lambda d: 
                        ec.presence_of_element_located((by_for, path_t))(d) and
                        ec.element_to_be_clickable((by_for, path_t))(d)
            )
        except UnexpectedAlertPresentException:
            alert = self.driver.switch_to.alert
            print(alert.text)
            alert.accept()  # ou alert.dismiss()
        """
        return elem

    def wait_download (self, params_dict):
        path_file = os.path.join (self.df_setup.loc ["Chrome download directory"].Value, params_dict ["File name"])
        print (self.df_setup.loc ["Chrome download directory"])
        print (path_file)
        delta_time = 0.5
        time_aux = 0
        while (not os.path.exists (path_file)) and (time_aux < params_dict ["Wait time"]):
            time.sleep (delta_time)
            time_aux += delta_time
        if os.path.exists (path_file):
            return True
        else:
            return False

    def set_zoom_after_element (self, params_dict):
        self.wait_element (params_dict)
        self.driver.execute_script(f'document.body.style.zoom="{self.zoom_level}%"')

    def goto_iframe (self, params_dict):
        self.wait_element (params_dict)
        by_for = By.CSS_SELECTOR
        path_t = params_dict ["Iframe"]
        elem = WebDriverWait (self.driver, self.df_setup.loc ["Waiting time for response per element"].values[0]).until(
                ec.frame_to_be_available_and_switch_to_it((by_for, path_t))
            )
        
        return elem

if __name__ == "__main__":
    # print ("Starting")
    current_script_dir = 'c:\\Users\\99848867\\OneDrive - Anheuser-Busch InBev\\My Documents\\RPRA\\Python\\'
    params = {"Geral": os.path.join (current_script_dir,"Setup/Setup.xlsx"),
          "Lista de roteros": os.path.join (current_script_dir,"Setup/Setup.xlsx"),
          "Webdriver": os.path.join (current_script_dir,"Setup/Setup.xlsx")}
    navegator = WebDriver_Obj (params)
    navegator.open_driver ()

    # time.sleep (1)
    params_dict = {"Rotero": 'C:\\Users\\99848867\\OneDrive - Anheuser-Busch InBev\\My Documents\\RPRA\\Exemplo_selenium.xlsx', "Tab": "Main rotero", "Sleep beteewn actions": 0}
    navegator.do_rotero (params_dict)

    print ("End")
    time.sleep (3)
    navegator.close_driver ()
