#!/usr/bin/env python3
from datetime import datetime, timedelta, time
from pytz import timezone
from random import randrange
from textmagic.rest import TextmagicRestClient
import json

#CONSTANTS
MSGS_PER_DAY = 4
DAYS_OF_MSGS = 7
START_DELAY = 1 #Units: Days
MSG_PERIOD_LENGTH = 12 #Units: Hours
MIN_TIME_BTWN_MSGS = timedelta(minutes = 90)

#Constants from TextMagicConfiguartion.json
with open('textMagicConfiguration.json') as f:
    textMagicConfig = json.load(f)

USERNAME = textMagicConfig['USERNAME']
TEXTMAGIC_API_KEY = textMagicConfig['TEXTMAGIC_API_KEY']
EMA_TEMPLATE_ID = textMagicConfig['EMA_TEMPLATE_ID']

def getRandomTimeDelta(minimum, maximum):
    #min/max are both timedeltas
    timeInSeconds = randrange(minimum.total_seconds(),maximum.total_seconds())
    #Round to nearest minute
    timeInSeconds = round(timeInSeconds/60)*60
    return timedelta(seconds = timeInSeconds)

def getTimeDeltasForOneDay():
    #Returns list of length MSGS_PER_DAY of timedeltas.
    # timedeltas define message times from start of daily messaging window
    hoursPerWindow = MSG_PERIOD_LENGTH/MSGS_PER_DAY
    msgWindows = [timedelta(hours=x*hoursPerWindow) for x in list(range(MSGS_PER_DAY+1))]
    dist = []
    for i in range(MSGS_PER_DAY):
        if not dist:
            minAcceptableTime = msgWindows[i]
        else:
            minAcceptableTime = max(msgWindows[i], dist[-1]+MIN_TIME_BTWN_MSGS)

        dist.append(getRandomTimeDelta(minAcceptableTime, msgWindows[i+1]))
    return dist

def getMsgDates():
    tz = timezone('Canada/Eastern')
    dt = datetime.now(tz).date()
    dates = [dt+timedelta(days=n+START_DELAY) for n in range(DAYS_OF_MSGS)]
    return dates

def findContactId(pNum): #participant number in study
    print('Finding contact information...')
    pageLimit=100
    pageNum=1
    client = TextmagicRestClient(USERNAME, TEXTMAGIC_API_KEY)
    contacts, pager = client.contacts.list(limit=pageLimit,page=pageNum)
    totalPages = pager['pageCount']
    lastNames=[]
    contactIds=[]
    while(pageNum<=totalPages):
        contacts, pager = client.contacts.list(limit=pageLimit,page=pageNum)
        for contact in contacts:
            lastNames.append(contact.lastName)
            contactIds.append(contact.id)
        pageNum += 1

    #print('Last names ('+ str(len(lastNames)) + '):')
    #print(lastNames)
    #print('--')

    numMatches = lastNames.count(str(pNum))
    if numMatches == 1:
        ind = lastNames.index(str(pNum))
    elif numMatches > 1:
        raise ValueError('Multiple matches found for participant number ' + str(pNum) + ' under account name ' +
                         USERNAME + '. Check TextMagic contents for duplicate entries with same participant number as last name.')
    elif numMatches < 1:
        raise ValueError('Participant number: ' + str(pNum) +
                         ' found in the last names of the contacts entered into TextMagic under account name '
                         + USERNAME)

    return contactIds[ind]

def findContactPhoneNumber(id):
    client = TextmagicRestClient(USERNAME, TEXTMAGIC_API_KEY)
    return client.contacts.get(id).phone

def scheduleTemplatedMessage(contactId, msgDateTime):
    client = TextmagicRestClient(USERNAME, TEXTMAGIC_API_KEY)
    #start_time = int(datetime.now().timestamp() + 7200)
    start_time = int(msgDateTime.timestamp())
    message = client.messages.create(#text="text magic test msg",
                                     templateId = EMA_TEMPLATE_ID,
                                     #phones=15193621011,
                                     contacts=contactId,#36936655,
                                     sendingTime=start_time)
    return message



def checkParamsWithUser(pNum, phoneNumber, msgStartTime, msgDates):
    print("Please review data below:")
    print('')
    print(str(MSGS_PER_DAY * DAYS_OF_MSGS) + ' messages to be scheduled.')
    print('Participant #: ' + str(pNum))
    print('Phone Number: ' + phoneNumber)
    print('Messaging Start Time: ' + msgStartTime.strftime('%I:%M %p'))
    print('Messaging Dates: ' + msgDates[0].strftime('%A %B %d, %Y') + ' - ' + msgDates[-1].strftime('%A %B %d, %Y'))
    print('')
    confirmation = input('Is the above information correct? (y/n) ')
    if confirmation is 'y':
        return True
    else:
        print('User input not "y" (lowercase, no spaces). Message scheduling cancelled.')
        return False

def msgsScheduledForContact(contactId):
    #Checks if contact already has scheduled messages pending
    #Returns True/False
    print('Checking contact against scheduled messages...')
    client = TextmagicRestClient(USERNAME, TEXTMAGIC_API_KEY)
    pageLimit = 100
    pageNum=1
    msgs, pager = client.schedules.list(limit=pageLimit, page=pageNum, orderBy='nextSend', direction='asc')
    totalPages = pager['pageCount']
    scheduledContacts=set()
    moreScheduled = True
    while(pageNum<=totalPages and moreScheduled):
        msgs, pager = client.schedules.list(limit=pageLimit, page=pageNum, orderBy='nextSend', direction='asc')
        for msg in msgs:
            if msg.nextSend == None: #Indicates past message rather than future scheduled message
                moreScheduled=False
                break
            else:
                scheduledContacts.update(msg.parameters['recipients']['contacts'])
        pageNum += 1

    #print('Scheduled contacts:')
    #print(scheduledContacts)
    #print('--')

    return contactId in scheduledContacts

def scheduleParticipant(pNum, msg_period_start_hour, msg_period_start_min):
    startTime = datetime.now()
    contactId = findContactId(pNum)

    if msgsScheduledForContact(contactId):
        print('Messages are already scheduled for this participant. Strongly recommend checking Textmagic to avoid '+
              'scheduling errors.')
        override = input('To override and schedule messages anyway, type "bad idea" and press enter: ')
        if not (override == 'bad idea'):
            print('Message scheduling cancelled')
            return False

    phoneNumber = findContactPhoneNumber(contactId)

    msgStartTime = time(hour=msg_period_start_hour, minute=msg_period_start_min)

    msgDates = getMsgDates()

    print('Run time of ' + str(datetime.now()-startTime) + ' seconds')

    if not checkParamsWithUser(pNum,phoneNumber,msgStartTime,msgDates):
        return False

    msgDateTimes = []
    for date in msgDates:
        timeDeltas = getTimeDeltasForOneDay()
        for td in timeDeltas:
            msgDateTimes.append(datetime.combine(date, msgStartTime) + td)
            scheduleTemplatedMessage(contactId, msgDateTimes[-1])
            print(str(msgDateTimes[-1]))

    assert len(msgDateTimes) == MSGS_PER_DAY * DAYS_OF_MSGS

    return True

if __name__ == '__main__':

    participantNum = int(input('Please enter the participant number: '))
    assert 100 <= participantNum and participantNum <= 999, 'participant number must be whole number from 100-999'

    print('Please enter the start time of the daily messaging window in 24 hour time')

    start_hour = int(input('Start hour of messaging: '))
    assert 0 <= start_hour < 24, 'start hour must be from 0-23'

    start_min = int(input('Start minute of messaging: '))
    assert 0 <= start_min < 60, 'start minute must be from 0-59'

    scheduleParticipant(participantNum,start_hour,start_min)
