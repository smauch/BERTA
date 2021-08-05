import datetime
import time
import pandas as pd
import logging
import configparser
from agent import Agent
from mail import mail



BASE_URL = 'https://raumbuchung.bibliothek.kit.edu/sitzplatzreservierung/'

logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s',
                    filename='sitz.log', level=logging.INFO, datefmt='%d/%m/%Y %I:%M:%S %p')


def get_my_bookings(agents):
    dfs = []
    for __, agent in agents.items():
        df = agent.get_bookings()
        dfs.append(df)
    df = pd.concat(dfs)
    df.sort_values(by=['date', 'period'], inplace=True)
    return df


def new_day_book(agents, days_delta=3, periods=[0, 1]):
    df = get_my_bookings(agents)
    now = datetime.datetime.now().date()
    delta = datetime.timedelta(days=days_delta)
    future_date = now + delta
    df = df[df['date'] == pd.to_datetime(future_date)]
    booked_periods = df['period'].tolist()
    free_rooms, room_dict = agents[PRIOR_AGENT].find_free_place(
        future_date, AREA)
    for period in periods:
        if period not in booked_periods:
            booked = None
            rooms = free_rooms[period]
            if not rooms:
                logging.warning("No place left")
                break
            for __, agent in agents.items():
                room_id = room_dict[rooms[int(len(rooms) / 2)]]
                booked = agent.book_entry(
                    base_url=BASE_URL, area=AREA, room_id=room_id, period=period, date=future_date)
                if booked:
                    print('Whuuuu booked', room_id, period, future_date)
                    break
            if not booked:
                logging.warning("Booking failed for all agents")


def change_booking_order(agents, days_delta=1):
    df = get_my_bookings(agents)
    now = datetime.datetime.now().date()
    delta = datetime.timedelta(days_delta)
    tomorrow = now + delta
    free_places, room_dict = agents[PRIOR_AGENT].find_free_place(
        tomorrow, AREA)
    tomorrow_df = df[df['date'] == pd.to_datetime(tomorrow)]
    for entry_id, row in tomorrow_df.iterrows():
        _agent_id = str(row['agent'])
        if _agent_id != PRIOR_AGENT:
            # TODO If 
            future_entry_df = df[df["agent"] == int(PRIOR_AGENT)]['date']
            if not future_entry_df.empty:
                future_entry_id = future_entry_df.idxmax()
            else:
                break
            agents[_agent_id].del_entry(
                base_url=BASE_URL, entry_id=entry_id)
            if future_entry_id:
                agents[PRIOR_AGENT].del_entry(
                    base_url=BASE_URL, entry_id=future_entry_id)
            agents[PRIOR_AGENT].book_entry(
                base_url=BASE_URL, area=AREA, room_id=room_dict[row['room']], period=row['period'], date=row['date'])
            agents[_agent_id].book_entry(base_url=BASE_URL, area=AREA, room_id=room_dict[df.loc[future_entry_id]
                                                                                            ['room']], period=df.loc[future_entry_id]['period'], date=df.loc[future_entry_id]['date'])
            df.drop([future_entry_id, entry_id], inplace=True)

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
    PRIOR_AGENT = config['General']['PriorAgent']
    AREA = config['General']["AreaID"]
    change_booking_order(agents, 0)
    new_day_book(agents)
    save_report(agents)
    mail("report.html")