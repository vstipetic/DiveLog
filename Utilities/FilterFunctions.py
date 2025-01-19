
from Utilities.ClassUtils.DiveClass import Dive
import datetime

def dive_was_deeper_than(dive_data: Dive, depth: float) -> bool:
    return max(dive_data.timeline.depths) > depth

def dive_was_shallower_than(dive_data: Dive, depth: float) -> bool:
    return max(dive_data.timeline.depths) < depth

def dive_was_longer_than(dive_data: Dive, time: float) -> bool:
    return dive_data.basic_information.duration > time

def dive_was_shorter_than(dive_data: Dive, time: float) -> bool:
    return dive_data.basic_information.duration < time

def dive_was_after_date(dive_data: Dive, date: datetime.datetime) -> bool:
    return dive_data.basic_information.start_time > date

def dive_was_before_date(dive_data: Dive, date: datetime.datetime) -> bool:
    return dive_data.basic_information.start_time < date

def dive_was_between_dates(dive_data: Dive, start_date: datetime.datetime, end_date: datetime.datetime) -> bool:
    return dive_data.basic_information.start_time > start_date and dive_data.basic_information.start_time < end_date

def dive_was_between_times(dive_data: Dive, start_time: datetime.datetime, end_time: datetime.datetime) -> bool:
    return dive_data.basic_information.start_time > start_time and dive_data.basic_information.start_time < end_time

def dive_was_deeper_than_for_duration(dive_data: Dive, depth: float, duration: float) -> bool:
    return max(dive_data.timeline.depths) > depth and dive_data.basic_information.duration > duration

def dive_was_longer_than(dive_data: Dive, time: float) -> bool:
    return dive_data.basic_information.duration > time
