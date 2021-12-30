import os
import sys
import configparser
import queue
import re
from threading import Thread
# import urllib3
from urllib.request import urlopen
# from urllib3 import response
from twill.commands import *


try:
    import requests
except:
    print('Install qrequests with "pip3 install grequests"')
    quit()
try:
    from bs4 import BeautifulSoup
except:
    print('Install BeautifulSoup with "pip3 install beautifulsoup4"')
    quit()
try:
    import twill
except:
    print('Install BeautifulSoup with "pip3 install twill"')
    quit()


try:
    email = getinput("Gib deine Email ein: ")
    password = getpassword("Gib dein Passwort ein: ")
    log_entry = input("Was soll gepostet werden?: ")
    go('https://www.geocaching.com/my/logs.aspx?s=1')
    fv("1", "UsernameOrEmail", email)
    fv("1", "Password", password)
    submit('0')
    links = showlinks()
    log_list = []
    i = 0
    j = 0
    for link in links:
        if "Log aufrufen" in link.text:
            logs = link.url
            log_list.append(logs)
            i += 1
    print(i, "logeinträge gefunden.")
    if input("Willst du wirklich fortfahren? [j/n]") == "j":
        for log in log_list:
            go(log)
            follow("Logeintrag bearbeiten")
            fv("1", "ctl00$ContentBody$LogBookPanel1$uxLogInfo", log_entry)
            # showforms()
            submit('-2')
            j += 1
            print(j, ". logeintrag geändert.")
        print(j, "logeinträge geändert.")

except:
    print('Irgendwas ist schief gelaufen.')
