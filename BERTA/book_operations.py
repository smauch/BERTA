from numpy import empty
from agent import AgentHandler
import datetime
import pandas as pd
import logging

def get_my_bookings(agents: AgentHandler):
    dfs = []
    for agent in agents.get():
        df = agent.get_bookings()
        if not df.empty:
            dfs.append(df)
    if not dfs:
        return pd.DataFrame()
    else:
        all_bookings_df = pd.concat(dfs)
        all_bookings_df.sort_values(by=['date', 'period'], inplace=True)
        return all_bookings_df


def book(agents: AgentHandler, p_agent_id, area, days_delta, reverse_fill, periods, fav_rooms):
    now = datetime.datetime.now().date()
    if reverse_fill:
        print("Bookings for the next", days_delta, "days...")
        deltas = reversed(range(1, days_delta + 1))
    else:
        print("Booking for in ", days_delta, "days...")
        deltas = list(days_delta)

    for day_delta in deltas:
        delta = datetime.timedelta(days=day_delta)
        future_date = now + delta
        df = get_my_bookings(agents)
        if df.empty:
            booked_periods = []
        else:
            df = df[df['date'] == pd.to_datetime(future_date)]
            booked_periods = df['period'].tolist()
        free_rooms, room_dict = agents.get(p_agent_id).find_free_place(
            future_date, area)
        for period in periods:
            if period not in booked_periods:
                booked = None
                p_rooms = free_rooms[period]
                fav_p_rooms = [i for i in p_rooms if i in fav_rooms]
                if len(fav_p_rooms):
                    p_rooms = fav_p_rooms
                if not p_rooms:
                    logging.warning("No place left")
                    continue
                for agent in agents.get():
                    room_id = room_dict[p_rooms[int(len(p_rooms) / 2)]]
                    booked = agent.book_entry(area=area, room_id=room_id, period=period, date=future_date)
                    if booked:
                        break
                if not booked:
                    logging.warning("Booking failed for all agents")
    df = get_my_bookings(agents)
    print("Bookings:", df)
    return

def delete_all_bookings(agents: AgentHandler):
    df = get_my_bookings(agents)
    if df.empty:
        logging.warning("No rooms to delete")
        return False
    print("Delete bookings...")
    for entry_id, row in df.iterrows():
        _agent_id = str(row['agent'])
        agents.get(_agent_id).del_entry(entry_id)
    df = get_my_bookings(agents)
    print("Bookings:", df)
    return

def change_booking_order(agents: AgentHandler, p_agent_id, area, days_delta):
    if len(agents) < 2:
        return False
    df = get_my_bookings(agents)
    if df.empty:
        logging.warning("No rooms to change")
        return False
    print("Change booking order...")
    now = datetime.datetime.now().date()
    delta = datetime.timedelta(days_delta)
    tomorrow = now + delta
    _, room_dict = agents.get(p_agent_id).find_free_place(tomorrow, area)
    tomorrow_df = df[df['date'] == pd.to_datetime(tomorrow)]
    for entry_id, row in tomorrow_df.iterrows():

        _agent_id = str(row['agent'])
        _room_id = room_dict[row['room']]
        _date = row['date']
        _period = row['period']

        if _agent_id != p_agent_id:
            future_entry_df = df[df["agent"] == int(p_agent_id)]['date']
            agents.get(_agent_id).del_entry(entry_id)
            if not future_entry_df.empty:
                future_entry_id = future_entry_df.idxmax()
                f_date = df.loc[future_entry_id]['date']
                f_room_id = room_dict[df.loc[future_entry_id]['room']]
                f_period = df.loc[future_entry_id]['period']
                if f_date != _date:
                    agents.get(p_agent_id).del_entry(future_entry_id)
                    agents.get(_agent_id).book_entry(area=area, room_id=f_room_id, period=f_period, date=f_date)
                df.drop([future_entry_id, entry_id], inplace=True)
            agents.get(p_agent_id).book_entry(area=area, room_id=_room_id, period=_period, date=_date)
    df = get_my_bookings(agents)
    print("Bookings:", df)
            
            