# coding: utf-8
# version: py2.7


import re
import urllib2
import codecs
import pymysql.cursors
import datetime
from selenium import webdriver
import pandas as pd
import matplotlib.pyplot as plt

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

def mysql(sql):
    connection = pymysql.connect(host='localhost', port=3306,
                                 user='root', password='admin',
                                 db='how', charset='utf8')
    try:
        with connection.cursor() as cursor:
            cursor.execute(sql)
        connection.commit()
    finally:
        connection.close()

def queryPrice(url):
    options = webdriver.ChromeOptions()
    options.add_argument('lang=en')

    driver = webdriver.Chrome(chrome_options=options)
    driver.set_window_size(1200, 800)
    driver.get(url)
    text = driver.find_element_by_xpath('html').text

    #   $1,203,19 x 10 nights
    pattern = re.compile('.(\d+,)*\d+ x \d+ night')
    match = re.findall(pattern, text)
    if len(match) == 1:
        print match
        price = match[0].split(' ')[0]
    else:
        price = 'No'

    driver.quit()
    return price

def queryRent(url, elapse):
    today = datetime.datetime.now()
    delta0 = datetime.timedelta(days=181)
    today += delta0
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
    delta_min = datetime.timedelta(days=min_nights)

    deltaElapse = datetime.timedelta(days=elapse)
    endday = today + deltaElapse - delta_min

    dayIn = today
    tableName = 'price' + url.split('/')[-1]
    while dayIn < endday:
        dayOut = dayIn + delta_min
        dayInShort = dayIn.strftime('%Y-%m-%d')
        dayOutShort = dayOut.strftime('%Y-%m-%d')

        queryUrl = url + '?checkin=' + dayInShort \
                       + '&checkout=' + dayOutShort
        price =  queryPrice(queryUrl)
        # print dayInShort, price

        if price != 'No':
            for i in range(min_nights):
                sql = "INSERT INTO %s values(null, '%s', '%s')" \
                      % (tableName, dayInShort, price)
                mysql(sql)
                dayIn += delta1
                dayInShort = dayIn.strftime("%Y-%m-%d")
        else:
            sql = "INSERT INTO %s values(null, '%s', '%s')" \
                  % (tableName, dayInShort, 'No')
            mysql(sql)
            dayIn += delta1

def queryAvailable(roomNo, mon):
    tableName = 'price' + str(roomNo)

    connection = pymysql.connect(host='localhost', port=3306,
                                 user='root', password='admin',
                                 db='how', charset='utf8')
    sql = 'SELECT * FROM %s' % tableName
    df = pd.read_sql(sql, connection, index_col='id')

    price = df['price']
    avail = 0
    unavail = 0
    for i in price:
        if i == 'No':
            unavail += 1
        else:
            avail += 1
    sum = avail + unavail
    avail = avail / 1.0 / sum
    unavail = unavail / 1.0 / sum

    fig = plt.figure(2)
    rects = plt.bar(left = (0.3, avail),
                    height = (0.7, unavail),
                    width = 0.2, align = 'center', yerr=0.000001)
    plt.title('Room ' + str(roomNo) + ' Availability in ' + str(mon) + ' Month')
    plt.xticks((0.3, 0.8), ('Available', 'Unavailable'))
    plt.show()


if __name__ == '__main__':
    url = 'https://www.airbnb.com/rooms/18509589'
    roomNo = int(url.split('/')[-1])

    # setProxy()
    # page = download(url)
    # # savePage(roomNo, page)
    # # page = loadPage(roomNo)
    #
    # location = getLocation(page)
    # room_type = getRoomType(page)
    # guest = getLabel('"guest_label"', page)
    # bedroom = getBedroom(page)
    # bed = getLabel('"bed_label"', page)
    # bathroom = getLabel('"bathroom_label"', page)
    #
    # sql = "INSERT INTO airbnb values(null, %d, %f, %f, '%s', %f, %d, %f, %f)" \
    #       % (roomNo, location[0], location[1], room_type, guest,
    #          bedroom, bed, bathroom)
    # mysql(sql)

    elapse = 6 * 30
    queryRent(url, elapse)

    queryAvailable(roomNo, 6)

