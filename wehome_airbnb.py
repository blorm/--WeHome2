# coding: utf-8
# version: py2.7


import re
import urllib2
import codecs
import pymysql.cursors
import datetime
from selenium import webdriver
import pandas as pd

def setProxy():
    proxy_addr = '183.88.195.231:8080'
    proxy_handler = urllib2.ProxyHandler({'https': 'https://' + proxy_addr})
    opener = urllib2.build_opener(proxy_handler)
    urllib2.install_opener(opener)

def download(url):
    # url = 'https://www.baidu.com'
    user_agent = 'Mozilla/5.0'
    headers = {'User-Agent' : user_agent}
    request = urllib2.Request(url, headers = headers)
    page = urllib2.urlopen(request, timeout=10).read().decode('utf-8')
    return page

def savePage(roomNo, page):
    fileName = str(roomNo)
    f = codecs.open(fileName, 'w', 'utf-8')
    f.write(page)
    f.close()

def loadPage(roomNo):
    fileName = str(roomNo)
    f = codecs.open(fileName, 'r', 'utf-8')
    page = f.read()
    return page

def findOnly(pattern, page):
    pattern = re.compile(pattern)
    match = re.findall(pattern, page)
    if len(match) != 1:
        print pattern, 'find error'
        exit()
    return match[0]

def getLocation(page):
    # location: "listing_lat":47.610622889203384
    #           "listing_lng":-122.33106772004382
    keyword = ['"listing_lat"', '"listing_lng"']
    loc = []
    for k in keyword:
        match = findOnly(k + ':-?\d+.\d+', page)
        loc.append( float( match.split(':')[-1] ) )
    return loc

def getLabel(label, page):
    # "bathroom_label":"1 bath", "bed_label":"1 bed",
    # "bedroom_label":"Studio", "guest_label":"2 guests"
    match = findOnly(label + ':"\d+ \w*"', page)
    match = findOnly('\d+', match)
    return float(match)

def getBedroom(page):
    # "bedroom_label":"Studio",
    type = {'Studio': 1,
            }
    match = findOnly('"bedroom_label":"\w*"', page)
    match = match.split(':')[-1][1:-1]
    if match in type:
        return type[match]
    else:
        print 'bedroom type not found'
        exit()

def getRoomType(page):
    # "room_and_property_type":"Entire apartment"
    match = findOnly('"room_and_property_type":"[\w ]*"', page)
    return match.split(':')[-1][1:-1]

def insertRoom(roomNo, location, room_type,
              guest, bedroom, bed, bathroom):
    connection = pymysql.connect(host='localhost', port=3306,
                                 user='root', password='admin',
                                 db='how', charset='utf8')

    sql = "INSERT INTO airbnb values(null, %d, %f, %f, '%s', %f, %d, %f, %f)" \
            %(roomNo, location[0], location[1], room_type, guest,
              bedroom, bed, bathroom)
    # print sql
    try:
        with connection.cursor() as cursor:
            cursor.execute(sql)
        connection.commit()
    finally:
        connection.close()

def price(url):
    headers = {
        'Accept-Language': 'en-US',
        'User-Agent': 'Mozilla/5.0 (Macintosh;) AppleWebKit/603.2.4',
        'Connection': 'keep-alive'
    }
    cap = {}
    for key, value in headers.items():
        cap['phantomjs.page.customHeaders.{}'.format(key)] = value
    driver = webdriver.PhantomJS(desired_capabilities=cap)
    driver.get(url)
    page = driver.page_source
    print page

    # page_source is static page, not dynamic....

    return 1, 1


def queryRent(url, elapse):
    today = datetime.datetime.now()
    todayShort = today.strftime('%Y-%m-%d')

    delta1 = datetime.timedelta(days=1)
    tomorrow = today + delta1
    tomorrowShort = tomorrow.strftime('%Y-%m-%d')

    # find min_nights
    queryUrl = url + '?chekcin=' + todayShort \
                + '&checkout=' + tomorrowShort
    page = download(queryUrl)
    match = findOnly('"min_nights":\d+', page)
    min_nights = int( match.split(':')[-1] )

    deltaElapse = datetime.timedelta(days=elapse)
    endday = today + deltaElapse - min_nights

    dayIn = today
    while dayIn < endday:
        dayOut = dayIn + min_nights
        dayInShort = dayIn.strftime('%Y-%m-%d')
        dayOutShort = dayOut.strftime('%Y-%m-%d')

        queryUrl = url + '?checkin=' + dayInShort \
                       + '?checkout=' + dayOutShort
        price =  price(queryUrl)
        #...

        dayIn += delta1


if __name__ == '__main__':
    url = 'https://www.airbnb.com/rooms/18509589'
    roomNo = int(url.split('/')[-1])

    setProxy()
    page = download(url)
    # savePage(roomNo, page)
    # page = loadPage(roomNo)

    location = getLocation(page)
    room_type = getRoomType(page)
    guest = getLabel('"guest_label"', page)
    bedroom = getBedroom(page)
    bed = getLabel('"bed_label"', page)
    bathroom = getLabel('"bathroom_label"', page)

    insertRoom(roomNo, location, room_type,
              guest, bedroom, bed, bathroom)

    elapse = 6 * 30
    queryRent(url, elapse)
