import time
import json
import pandas as pd
import logging
import configparser
from agent import Agent
from mail import mail
from book_operations import get_my_bookings
from book_operations import change_booking_order
from book_operations import book



logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s',
                    filename='sitz.log', level=logging.INFO, datefmt='%d/%m/%Y %I:%M:%S %p')

def save_report(agents):
    df = get_my_bookings(agents)
    html = df.to_html()
    with open("report.html", "w") as f:
        f.write(html)
    return

if __name__ == '__main__':
    config = configparser.ConfigParser()
    config.read('config.ini')
    agents={}
    for username, password in config['Agents'].items():
        agents[username] = Agent(username,password)

    prior_agent_id = config['General']['PriorAgent']
    area_id = config['General']["AreaID"]
    periods = json.loads(config['General']["Periods"])
    fav_rooms = json.loads(config['General']["FavRooms"])
    delta_new = int(config['General']["DeltaNewBooking"])
    delta_change = int(config['General']["DeltaChangeBooking"])
    change_booking_order(agents=agents, p_agent_id=prior_agent_id, area=area_id, days_delta=delta_change)
    book(agents=agents, p_agent_id=prior_agent_id, area=area_id, days_delta=delta_new, periods=periods, fav_rooms=fav_rooms)
    save_report(agents)
    mail("report.html")