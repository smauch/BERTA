import datetime
import pandas as pd
import logging

def get_my_bookings(agents):
    dfs = []
    for __, agent in agents.items():
        df = agent.get_bookings()
        if not df.empty:
            dfs.append(df)
    if not dfs:
        return None
    else:
        all_bookings_df = pd.concat(dfs)
        all_bookings_df.sort_values(by=['date', 'period'], inplace=True)
        return all_bookings_df


def new_day_book(agents, p_agent_id, area, days_delta=3, periods=[0, 1]):
    now = datetime.datetime.now().date()
    delta = datetime.timedelta(days=days_delta)
    future_date = now + delta
    df = get_my_bookings(agents)
    if df is None:
        booked_periods = []
    else:
        df = df[df['date'] == pd.to_datetime(future_date)]
        booked_periods = df['period'].tolist()
    free_rooms, room_dict = agents[p_agent_id].find_free_place(
        future_date, area)
    for period in periods:
        if period not in booked_periods:
            booked = None
            rooms = free_rooms[period]
            if not rooms:
                logging.warning("No place left")
                break
            for __, agent in agents.items():
                room_id = room_dict[rooms[int(len(rooms) / 2)]]
                booked = agent.book_entry(area=area, room_id=room_id, period=period, date=future_date)
                if booked:
                    break
            if not booked:
                logging.warning("Booking failed for all agents")


def change_booking_order(agents, p_agent_id, area, days_delta=0):
    if len(agents) < 2:
        return False
    df = get_my_bookings(agents)
    if df is None:
        logging.warning("No rooms to change")
        return False
    now = datetime.datetime.now().date()
    delta = datetime.timedelta(days_delta)
    tomorrow = now + delta
    _, room_dict = agents[p_agent_id].find_free_place(tomorrow, area)
    tomorrow_df = df[df['date'] == pd.to_datetime(tomorrow)]
    for entry_id, row in tomorrow_df.iterrows():

        _agent_id = str(row['agent'])
        _room_id = room_dict[row['room']]
        _date = row['date']
        _period = row['period']

        if _agent_id != p_agent_id:
            future_entry_df = df[df["agent"] == int(p_agent_id)]['date']
            agents[_agent_id].del_entry(entry_id)
            if not future_entry_df.empty:
                future_entry_id = future_entry_df.idxmax()
                f_date = df.loc[future_entry_id]['date']
                f_room_id = room_dict[df.loc[future_entry_id]['room']]
                f_period = df.loc[future_entry_id]['period']
                if f_date != _date:
                    agents[p_agent_id].del_entry(future_entry_id)
                    agents[_agent_id].book_entry(area=area, room_id=f_room_id, period=f_period, date=f_date)
                df.drop([future_entry_id, entry_id], inplace=True)
            agents[p_agent_id].book_entry(area=area, room_id=_room_id, period=_period, date=_date)
            
            