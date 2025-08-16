from datetime import datetime



def get_current_date_time_for_folder_name():
    today = datetime.now()

    if today.hour < 12:
        h = "00"
    else:
        h = "12"

    dt = today.strftime('%Y_%m_%d_%H_%M_%S') + h
    # print(dt)
    return dt


def get_today_date():
    today_date = datetime.now().strftime('%d-%m-%Y')
    return today_date