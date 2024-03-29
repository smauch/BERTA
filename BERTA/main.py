import os
import errno
import argparse
import json
import logging
import configparser
from agent import Agent, AgentHandler
from mail import mail
from book_operations import get_my_bookings
from book_operations import change_booking_order
from book_operations import book
from book_operations import delete_all_bookings

dirname = os.path.dirname(__file__) 
log_path = os.path.join(dirname, 'berta.log')
logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s',
                    filename=log_path, level=logging.INFO, datefmt='%d/%m/%Y %I:%M:%S %p')

def save_report(agent_handler):
    df = get_my_bookings(agent_handler, True)
    if df.empty:
        return None
    df['is_prior_agent'] = False
    df.loc[df.agent == int(prior_agent_id), "is_prior_agent"] = True
    html = df.to_html()
    report_path = os.path.join(dirname,"report.html")
    with open(report_path, "w") as f:
        f.write(html)
    return report_path

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('config', nargs='?', default='config.ini', help="Use your <custom_config.ini> file")           
    args = parser.parse_args()
    config_path = os.path.join(dirname, args.config)
    if not os.path.isfile(config_path):
        raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), config_path)
    config = configparser.ConfigParser()
    config.read(config_path)
    agent_handler = AgentHandler(0)
    for username, password in config['Agents'].items():
        agent_handler.add(Agent(username,password))
    prior_agent_id = config['General']['PriorAgent']
    area_id = config['General']["AreaID"]
    periods = json.loads(config['General']["Periods"])
    fav_rooms = json.loads(config['General']["FavRooms"])
    delta_new = int(config['General']["DeltaNewBooking"])
    delta_change = int(config['General']["DeltaChangeBooking"])
    reverse_fill = config.getboolean('General', "ReverseFill")
    #delete_all_bookings(agent_handler)
    book(agent_handler=agent_handler, p_agent_id=prior_agent_id, area=area_id, days_delta=delta_new, periods=periods, reverse_fill=reverse_fill, fav_rooms=fav_rooms)
    change_booking_order(agent_handler=agent_handler, p_agent_id=prior_agent_id, area=area_id, days_delta=delta_change)
    report_path = save_report(agent_handler)
    mail(report_path, config_path)