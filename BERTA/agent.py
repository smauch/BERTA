import re
from PIL.Image import FASTOCTREE
import requests
from bs4 import BeautifulSoup
import logging
import pandas as pd
import json
import os
from typing import Union, List
import base64
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
import urllib.parse as urlparse
from urllib.parse import parse_qs
import time
from ocr import solve_captcha

BASE_URL = 'https://raumbuchung.bibliothek.kit.edu/sitzplatzreservierung/'

period_dict = {
    'vormittags' : 0,
    'nachmittags' : 1,
    'abends' : 2
}

def get_cookie_and_captcha(file_path='admin.php'):
    options = Options()
    options.headless = True 
    driver = webdriver.Firefox(options=options)
    driver.set_script_timeout(10)
    driver.get(BASE_URL + file_path)
    # find the captcha element
    ele_captcha = driver.find_element_by_xpath("//img[contains(./@src, 'genCaptcha.php')]")

    # get the captcha as a base64 string
    img_captcha_base64 = driver.execute_async_script("""
        var ele = arguments[0], callback = arguments[1];
        ele.addEventListener('load', function fn(){
        ele.removeEventListener('load', fn, false);
        var cnv = document.createElement('canvas');
        cnv.width = this.width; cnv.height = this.height;
        cnv.getContext('2d').drawImage(this, 0, 0);
        callback(cnv.toDataURL('image/jpeg').substring(22));
        }, false);
        ele.dispatchEvent(new Event('load'));
        """, ele_captcha)
    # save the captcha to a file
    file_path = 'captcha.jpg'
    with open(file_path, 'wb') as f:
        f.write(base64.b64decode(img_captcha_base64))
    captcha_text = solve_captcha(file_path)
    os.remove('captcha.jpg')
    print(captcha_text)
    cookie = driver.get_cookie('PHPSESSID')
    cookie = {"name": cookie['name'], "value": cookie["value"], "domain":cookie["domain"]}
    driver.quit()
    return cookie, captcha_text


def check_response(r):
    if r.history:
        status = r.history[0].status_code
    else:
        status = r.status_code

    if status == 302:
        return True
    elif status == 200:
        return False
    else:
        print("Unexpected return", r.status_code)


class Agent:
    def __init__(self, username, password):
        self.username = username
        self.alias = None
        self.password = password
        self.session = None

    def get_logged_in(self):
        if not self.session:
            return False
        r = self.session.get(BASE_URL)
        soup = BeautifulSoup(r.text, 'html.parser')
        soup = soup.find(id='logon_box')
        soup = soup.find('a', href=True)
        if soup.has_attr('href'):
            logon_box_link = soup['href']
            parsed = urlparse.urlparse(logon_box_link)
            username = parse_qs(parsed.query)['creatormatch'][0]
            if self.username != username:
                self.alias = self.username
                self.username = username

        if str(self.username) in soup.text:
            return True
        else:
            return False


    def log_in(self, file_path='admin.php'):
        attempts = 0
        while attempts < 5:
            cookie, captcha_text = get_cookie_and_captcha()
            form_data = {
                'NewUserName' : self.username,
                'NewUserPassword' : self.password,
                'CaptchaText' : captcha_text,
                'Action' : 'SetName',
                'EULA' : 'on'
            }
            with requests.session() as s:
                s.headers.update(
                {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Safari/537.36"
                }
                )
                s.cookies.set(**cookie)
                login_url = BASE_URL + file_path
                r = s.post(login_url, form_data)
                self.session = s
                if check_response(r) and self.get_logged_in():
                    log_str = json.dumps(('LOGIN:',self.username, 302))
                    logging.info(log_str)
                    print('Successfully logged in')
                    return True
                else:
                    attempts += 1
                    log_str = json.dumps(('LOGIN:',self.username, attempts, 200))
                    logging.error(log_str)
                    time.sleep(5)
        raise RuntimeError('The login for the agent failed for 5 times.')

    def get_bookings(self, file_path='report.php'):
        if not self.get_logged_in():
            self.log_in()
        target_url = BASE_URL + file_path
        r = self.session.get(target_url)
        soup_1 = BeautifulSoup(r.text, 'html.parser')
        soup_1 = soup_1.find("form", {'id' : 'report_form'})
        query_params = {}
        for element in soup_1.find_all('input'):
            try:
                query_params[element['name']] = element['value']
            except:
                pass

        query_params['output_format'] = 0
        query_params['output'] = 0
        query_params['match_confirmed'] = 1
        r = self.session.get(target_url, params=query_params)
        soup = BeautifulSoup(r.text, 'html.parser')
        try:
            report_table = soup.find('table', {'id' : 'report_table'})
            tbody = report_table.find('tbody')
            trs = tbody.find_all('tr')
        except:
            return None
        entry_ids = {}
        for tr in range(len(trs)):
            try:
                entry_id = trs[tr].find('a', href=True)['data-id']
                entry_ids[tr] = entry_id
            except:
                entry_ids[tr] = None
        report_df = pd.read_html(report_table.prettify())[0]
        report_df['entry_id'] = report_df.index.map(entry_ids)
        report_df['period'] = report_df['Anfangsdatum'].str.split(',',expand=True)[0]
        report_df['date'] = report_df['Anfangsdatum'].str.split(',',expand=True)[1]
        report_df["date"] = pd.to_datetime(report_df["date"])
        report_df["room"] = report_df["Sitzplatz"]
        report_df["agent"] = report_df["Kurzbeschreibung"]
        report_df['period'].replace(period_dict, inplace=True)
        report_df.set_index('entry_id', inplace=True)
        report_df = report_df.loc[:, ~report_df.columns.str.contains('Kurzbeschreibung|Sitzplatz|Bereich|Enddatum|Anfangsdatum|Unnamed')]
        return report_df


    def find_free_place(self, date, area, periods=3):
        if not self.get_logged_in():
            self.log_in()
        params = {
            "year" : int(date.year),
            "month": int(date.month),
            "day": int(date.day),
            "area": int(area)
        }
        r = self.session.get(BASE_URL + 'day.php', params=params)
        soup = BeautifulSoup(r.text, 'html.parser')
        main_table = soup.find('table', class_="dwm_main")
        thead = main_table.find('thead')
        ths = thead.find_all('th')
        room_dict = {}
        for th in ths:
            try:
                room_name = th.find('a').text
                room_id = th['data-room']
                room_dict[room_name] = room_id
            except:
                pass

        room_df = pd.read_html(main_table.prettify())[0]
        free_places = {}
        for n in range(periods):
            free_places[n] = room_df.columns[room_df.loc[n].isna()].tolist()
        return free_places, room_dict

    def book_entry(self, area, room_id, period, date, file_path="edit_entry.php", file_path_handler="edit_entry_handler.php"):
        if not self.get_logged_in():
            self.log_in()
        params = {
            "area": int(area),
            "room": int(room_id),
            "period": int(period),
            "year" : int(date.year),
            "month": int(date.month),
            "day": int(date.day)
        }
        entry_url = BASE_URL + file_path
        entry_handler_url = BASE_URL + file_path_handler
        r = self.session.get(entry_url, params=params)

        soup_1 = BeautifulSoup(r.text, 'html.parser')
        soup_1 = soup_1.find("form", {'id' : 'main'})

        form_data = {}
        for element in soup_1.find_all('input'):
            try:
                form_data[element['name']] = element['value']
            except:
                pass
        del form_data["back_button"]
        del form_data["all_day"]
        # Policy and coflict check
        check_form = form_data.copy()
        check_form['ajax'] = 1
        r = self.session.post(entry_handler_url, check_form)
        valid_booking = "true"
        if not r.json()['valid_booking']:
            if r.json()['rules_broken']:
                valid_booking = 'rules_broken'
            elif r.json()['conflicts']:
                valid_booking ='conflicts'
            else:
                valid_booking = 'rules_broken_conflicts'
        
        r = self.session.post(entry_handler_url, form_data)
        
        if check_response(r):
            log_str = json.dumps(('BOOKING:',self.username, params, valid_booking, 302))
            logging.info(log_str)
            return True
        else:
            log_str = json.dumps(('BOOKING:',self.username, params, valid_booking, 200))
            logging.warning(log_str)
            return False
    
    def del_entry(self, entry_id, file_path="del_entry.php"):
        if not entry_id:
            return True
        if not self.get_logged_in():
            self.log_in()
        del_entry_url = BASE_URL + file_path
        r = self.session.post(del_entry_url, {'id' : int(entry_id)})
        if check_response(r):
            log_str = json.dumps(('DELETE:', self.username, {'id' : entry_id}, 302))
            logging.info(log_str)
            return True
        else:      
            log_str = json.dumps(('DELETE:', self.username, {'id' : entry_id}, 200))
            logging.warning(log_str)
            return False


class AgentHandler:
    def __init__(self, agents = None):
        self.agents = []
        self._data_len = len(self.agents)
        if agents is None:
            pass
        elif isinstance(agents, Agent):
            self.agents.append(agents)
        elif hasattr(agents, '__iter__'):
            for agent in agents:
                if isinstance(agent, Agent):
                    self.agents.append(agents)
                else:
                    raise TypeError('Obj of type Agent was expected')
        else:
            raise TypeError('Obj of type Agent was expected')
        return
    
    def add(self, agent: Agent):
        if isinstance(agent, Agent):
            self.agents.append(agent)
        else:
            raise TypeError('Obj of type Agent was expected')
        self._data_len = len(self.agents)
        return

    def get(self, username=None) -> Union[Agent,List[Agent]]:
        if username is None:
            return self.agents
        for agent in self.agents:
            if username in agent.username:
                return agent
            elif username in agent.alias:
                return agent
        raise KeyError("No agent with this username was added to handler")

    def __len__(self):
        return self._data_len