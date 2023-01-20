#!/usr/bin/env python3

import json
from escpos.printer import Usb
from icalendar import Calendar, Event
import textwrap
import urllib.request
import datetime
config = {}
try:
    with open('config.json') as json_file:
        config = json.load(json_file)
except:
    exit("No config file found. Please create a config.json file in the same directory as this script.")
VID = config["printer"].get("VID", 0x416)
PID = config["printer"].get("PID", 0x5011)
model = config["printer"].get("Model", "POS-5890")

from flask import Flask, request, Response
from ref import *


app = Flask(__name__)
ical_url = config.get("ical_url")
p = Usb(VID, PID, profile=model)

def humanDate(date=datetime.date.today()):

    # Get the day of the month as a non-zero-padded number
    day_of_month = date.strftime("%-d")

    # Add the correct ordinal suffix
    if day_of_month == "1":
        ordinal_suffix = "st"
    elif day_of_month == "2":
        ordinal_suffix = "nd"
    elif day_of_month == "3":
        ordinal_suffix = "rd"
    else:
        ordinal_suffix = "th"

    # Use the strftime method to format the date and time
    return date.strftime("%A, %B") + " " + day_of_month + ordinal_suffix + ", " + date.strftime("%Y")

def get_week_of_month(date):
        month = date.month
        week = 0
        while date.month == month:
            week += 1
            date -= datetime.timedelta(days=7)
        return week

def print_lunch():
    # if it's after 1 pm then print tomorrow's lunch
    time_to_print = datetime.datetime.now()
    day_of_week = int(time_to_print.now().strftime("%w")) -1
    header = "Today's Lunch:"
    if datetime.datetime.now().hour >= 13:
        time_to_print += datetime.timedelta(days=1)
        header = "Tomorrow's Lunch:"
        day_of_week += 1
    week_of_month = int(get_week_of_month(time_to_print.now()))

    day_of_week += 1
    if day_of_week == 5:
        day_of_week = 1
    print(day_of_week)
    
    if day_of_week == 6 or day_of_week == 0:
        print_centered("No lunch " + header.split("'")[0] + "!")
        print_line()
        return
    e = meals[str(week_of_month)][str(day_of_week)]["e"]
    s = meals[str(week_of_month)][str(day_of_week)]["s"]

    print_centered(header)
    print_line()
    print_wrapped(f"Entree:")
    print_wrapped(e)
    print_line()
    print_wrapped(f"Sides:")
    for side in s:
        print_wrapped(s[side])
    print_line()


def print_line(text=""):
    p.text(text + "\n")

def print_centered(text):
    # Calculate the amount of space to add to both sides of the text
    spaces = (32 - len(text)) // 2
    print_line(' ' * spaces + text + ' ' * spaces)

def print_wrapped(text):
    # Use the wrap function to word wrap the text
    wrapped_text = textwrap.wrap(text, width=32)
    for line in wrapped_text:
        print_line(line)

def print_bar():
    p.set(density=8, bold=True)
    print_line("-" * 30)
    p.set(density=2, bold=False)

def print_events():
    # Get the current date
    today = datetime.date.today()
    ical = Calendar.from_ical(urllib.request.urlopen(ical_url).read())
    done_today = False
    print_centered(humanDate())
    print_line()
    print_centered("Homework")
    
    lastDate = today - datetime.timedelta(days=1)
    for component in ical.walk():
        # Check if the component is an event
        if component.name == "VEVENT":
            # Get the end date of the event
            end = component.get("DTEND").dt
            start = component.get("DTSTART").dt
            # Check if the event ends on the current date or within the next three days
            if (datetime.date(end.year, end.month, end.day) >= today and datetime.date(end.year, end.month, end.day) <= today + datetime.timedelta(days=3)) or (datetime.date(start.year, start.month, start.day) >= today and datetime.date(start.year, start.month, start.day) <= today + datetime.timedelta(days=3)):
                if datetime.date(end.year, end.month, end.day) == today and lastDate != today or datetime.date(start.year, start.month, start.day) == today and lastDate != today:
                    print_bar()
                    print_centered("Today:")
                    print_line()
                elif datetime.date(end.year, end.month, end.day) and not done_today or datetime.date(start.year, start.month, start.day) and not done_today:
                    done_today = True
                    print_bar()
                    print_centered("Upcoming:")
                    print_line()
                lastDate = datetime.date(start.year, start.month, start.day)
                # The event ends on the current date or within the next three days, so print its summary
                print_wrapped(component.get("SUMMARY"))
                print_line()
    print_line()


@app.route('/run/print')
def api_run():
    try:
        print_events()
        print_bar()
        print_line()
        print_lunch()
        print_line()
        return "OK", 200
    except Exception as e:
        print(e)
        return "Internal Server Error", 500


@app.route('/api/print', methods=['POST'])
def api_print():
    try:
        text = request.json.get("text")
        for line in text.split("\n"):
            print(line)
        return "OK", 200
    except Exception as e:
        print(e)
        return "Internal Server Error", 500

if __name__ == "__main__":
    app.run(host="piprint.local", port=5000)