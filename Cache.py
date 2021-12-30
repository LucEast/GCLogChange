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
    email = getinput("Gebe deine Email ein: ")
    password = getpassword("Gebe dein Passwort ein: ")
    log_entry = input("Was soll gepostet werden?: ")
    go('https://www.geocaching.com/my/logs.aspx?s=1')
    fv("1", "UsernameOrEmail", email)
    fv("1", "Password", password)
    submit('0')
    links = showlinks()
    log_list = []
    for link in links:
        if "Visit log" in link.text:
            logs = link.url
            log_list.append(logs)
    # print(log_list)
    for log in log_list:
        go(log)
        follow("Edit Log")
        fv("1", "ctl00$ContentBody$LogBookPanel1$uxLogInfo", log_entry)
        showforms()
        submit('-2')

except:
    print('Irgendwas ist schief gelaufen.')
