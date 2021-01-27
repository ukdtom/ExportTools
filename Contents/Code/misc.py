##########################################################################
# Helper file for dane22
# This one handles misc functions
#
# Increment version for all new functions and fixes
#
##########################################################################

import re
import datetime
import moviefields
import audiofields
import tvfields
import photofields
import dateutil.parser as parser

import sys
import os
import math
import consts
from textwrap import wrap, fill


from xml.etree import ElementTree

VERSION = '0.0.0.5'


def getVersion():
    ''' This function will return the version of the misc module '''
    return VERSION


def getToken():
    ''' return a valid token from plex.tv '''
    userName = Prefs['Plex_User']
    userPwd = Prefs['Plex_Pwd']
    myUrl = 'https://plex.tv/users/sign_in.json'
    # Create the authentication string
    base64string = String.Base64Encode('%s:%s' % (userName, userPwd))
    # Create the header
    MYAUTHHEADER = {}
    MYAUTHHEADER['X-Plex-Product'] = consts.DESCRIPTION
    MYAUTHHEADER['X-Plex-Client-Identifier'] = consts.APPGUID
    MYAUTHHEADER['X-Plex-Version'] = consts.VERSION
    MYAUTHHEADER['Authorization'] = 'Basic ' + base64string
    MYAUTHHEADER['X-Plex-Device-Name'] = consts.NAME
    # Send the request
    try:
        httpResponse = HTTP.Request(myUrl, headers=MYAUTHHEADER, method='POST')
        myToken = JSON.ObjectFromString(httpResponse.content)[
            'user']['authentication_token']
        Log.Debug('Response from plex.tv was : %s' %
                  (httpResponse.headers["status"]))
    except Exception, e:
        Log.Critical(
            'Exception happend when trying to get a token from plex.tv')
        Log.Critical('Returned answer was %s' % httpResponse.content)
        Log.Critical('Status was: %s' % httpResponse.headers)
        return ''
    return myToken


def GetLoopBack():
    ''' return the loopback address '''
    # For now, simply return the IPV4 LB Addy, until PMS is better with this
    return 'http://127.0.0.1:32400'
    try:
        httpResponse = HTTP.Request(
            'http://[::1]:32400/web', immediate=True, timeout=5)
        return 'http://[::1]:32400'
    except Exception, e:
        return 'http://127.0.0.1:32400'


def GetArrayAsString(Media, Field, default=''):
    ''' return info from an array, defined in an xpath '''
    Fields = Media.xpath(Field)
    if not Fields:
        Fields = ['']
    Field = ''
    for myField in Fields:
        if myField is None:
            myField = default
        if myField == '':
            myField = default
        if Field == '':
            Field = myField
        else:
            Field = Field + Prefs['Seperator'] + myField
    return WrapStr(fixCRLF(Field)).encode('utf8')


def GetExtInfo(ExtInfo, myField, default=''):
    ''' return info from extended page for movies '''
    try:
        myLookUp = WrapStr(ExtInfo.xpath('Media/@' + myField)[0])
        if not myLookUp:
            myLookUp = WrapStr(default)
    except Exception, e:
        myLookUp = WrapStr(default)
    return myLookUp.encode('utf8')


def GetMoviePartInfo(ExtInfo, myField, default=''):
    ''' return info from different parts of a movie '''
    try:
        myLookUp = WrapStr(ExtInfo.get(myField))
        if not myLookUp:
            myLookUp = WrapStr(default)
    except Exception, e:
        myLookUp = WrapStr(default)
    return myLookUp.encode('utf8')


def GetRegInfo(myMedia, myField, default=''):
    ''' Pull's a field from the xml '''
    try:
        if myField in ['rating']:
            myLookUp = "{0:.1f}".format(float(myMedia.get(myField)))
        else:
            myLookUp = WrapStr(fixCRLF(myMedia.get(myField)))
        if not myLookUp:
            myLookUp = WrapStr(default)
    except Exception, e:
        myLookUp = WrapStr(default)
    return myLookUp.encode('utf8')


def GetRegInfo2(
        myMedia, myField, default=consts.DEFAULT,
        key='N/A', mediaType='movie'):
    ''' Pull's a field from the xml '''
    returnVal = ''
    global retVal
    retVal = ''
    try:
        fieldsplit = myField.rsplit('@', 1)
        # Single attribute lookup
        if fieldsplit[0] == '':
            try:
                if len(fieldsplit) == 2:
                    returnVal = myMedia.get(fieldsplit[1])
                    if returnVal in [None, '']:
                        returnVal = default
                    elif fieldsplit[1] in moviefields.dateTimeFields:
                        returnVal = ConvertDateStamp(returnVal)
                        if returnVal == '01/01/1970':
                            returnVal = default
                    elif fieldsplit[1] in moviefields.timeFields:
                        returnVal = ConvertTimeStamp(returnVal)
                        if returnVal == '01/01/1970':
                            returnVal = default
                    # Plex origen GUID
                    elif fieldsplit[1] == 'guid':
                        try:
                            return metaDBLink(
                                returnVal,
                                mediatype=myMedia.xpath(
                                    '@type')[0]).encode('utf8')
                        except Exception, e:
                            pass
                    if returnVal.startswith('plex://'):
                        returnVal = default
            except Exception, e:
                Log.Critical('Exception on field: ' + myField)
                returnVal = default
                return WrapStr(fixCRLF(returnVal)).encode('utf8')
        else:
            if key in [
                'IMDB ID', 'TMDB ID', 'IMDB Link',
                    'TMDB Link', 'TVDB ID', 'TVDB Link']:
                try:
                    if key == 'IMDB Link':
                        returnVal = ''.join((
                            'https://www.imdb.com/title/',
                            myMedia.xpath(myField)[0].split("//")[1]))
                    elif key == 'TMDB Link':
                        if mediaType == 'movie':
                            returnVal = ''.join((
                                'https://www.themoviedb.org/movie/',
                                myMedia.xpath(myField)[0].split("//")[1]))
                        else:
                            returnVal = ''.join((
                                'https://www.themoviedb.org/tv/',
                                myMedia.xpath(myField)[0].split("//")[1]))
                    elif key == 'TVDB Link':
                        returnVal = ''.join((
                            'https://www.GED.org/TEST/',
                            myMedia.xpath(myField)[0].split("//")[1]))
                    else:
                        returnVal = myMedia.xpath(myField)[0].split("//")[1]
                except Exception, e:
                    returnVal = default
                    pass
            else:
                # Attributes from xpath
                try:
                    retVals = myMedia.xpath(fieldsplit[0][:-1])
                except Exception, e:
                    retVals = []
                    retVals[0] = myField
                    pass
                for retVal2 in retVals:
                    try:
                        # Get attribute
                        retVal = default
                        retVal = String.Unquote(retVal2.get(fieldsplit[1]))
                        # Did it exists?
                        if retVal in [None, '']:
                            retVal = default
                        # Is it a dateStamp?
                        elif fieldsplit[1] in moviefields.dateTimeFields:
                            retVal = ConvertDateStamp(retVal)
                        # Got a timestamp?
                        elif fieldsplit[1] in moviefields.timeFields:
                            retVal = ConvertTimeStamp(retVal)
                        # size conversion?
                        elif key == 'Part Size':
                            retVal = ConvertSize(retVal)
                        if returnVal == '':
                            returnVal = retVal
                        else:
                            returnVal = returnVal + Prefs['Seperator'] + retVal
                    except Exception, e:
                        if returnVal != '':
                            returnVal = returnVal + Prefs['Seperator'] + retVal
                            pass
                        else:
                            returnVal = default
                            pass
        return WrapStr(fixCRLF(returnVal)).encode('utf8')
    except Exception, e:
        returnVal = default


def fixCRLF(myString):
    ''' Fix CR/LF '''
    myString = myString.decode('utf-8').replace('\r\n', ' ')
    myString = myString.decode('utf-8').replace('\n', ' ')
    myString = myString.decode('utf-8').replace('\r', ' ')
    return myString


def WrapStr(myStr, default='N/A'):
    ''' Wraps a string if needed '''
    LineWrap = int(Prefs['Line_Length'])
    if myStr is None:
        myStr = default
    if Prefs['Line_Wrap']:
        return fill(myStr, LineWrap)
    else:
        return myStr


def ConvertTimeStamp(timeStamp):
    ''' return a string in hh:mm from a millisecond timestamp '''
    seconds = str(int(timeStamp) / (1000) % 60)
    if len(seconds) < 2:
        seconds = '0' + seconds
    minutes = str((int(timeStamp) / (1000 * 60)) % 60)
    if len(minutes) < 2:
        minutes = '0' + minutes
    hours = str((int(timeStamp) / (1000 * 60 * 60)) % 24)
    return hours + ':' + minutes + ':' + seconds


def ConvertDateStamp(timeStamp):
    '''
    return a date string in ISO 8601 format from a millisecond timestamp
    '''
    try:
        return Datetime.FromTimestamp(float(timeStamp)).date().isoformat()
    except Exception, e:
        return timeStamp


def getLevelFields(levelFields, fieldnames):
    ''' return fieldnames for a level '''
    fieldnamesList = list(fieldnames)
    for item in levelFields:
        fieldnamesList.append(str(item[0]))
    return fieldnamesList


def getItemInfo(et, myRow, fieldList, mediaType='movie'):
    ''' fetch the actual info for the element '''
    intBehindthescenes = 0
    intDeleted = 0
    intFeaturette = 0
    intInterview = 0
    intScene = 0
    intShort = 0
    intTrailer = 0

    try:
        for item in fieldList:
            try:
                key = str(item[0])
                value = str(item[1])
                # Special deal for Sort Title
                if key in ['Sort title', 'Episode Sort Title']:
                    if Prefs['Sort_title']:
                        if consts.DEFAULT == GetRegInfo2(
                                et,
                                value,
                                consts.DEFAULT,
                                key=key):
                            element = GetRegInfo2(
                                et, '@title', consts.DEFAULT, key='Title',
                                mediaType=mediaType)
                        else:
                            element = GetRegInfo2(
                                et, value, consts.DEFAULT, key=key,
                                mediaType=mediaType)
                    else:
                        element = GetRegInfo2(
                            et, value, consts.DEFAULT, key=key,
                            mediaType=mediaType)
                elif key.startswith('Extras-'):
                    retVals = et.xpath(value)
                    element = str(len(retVals))
                elif key == ('Chapter Count'):
                    retVals = et.xpath(value)
                    element = str(len(retVals))
                elif key in ['Part File Only', 'Part File Path']:
                    element = GetRegInfo2(
                            et,
                            value,
                            consts.DEFAULT,
                            key='Part File Only',
                            mediaType=mediaType)
                    if key == 'Part File Only':
                        element = os.path.split(element)[1]
                    else:
                        element = os.path.split(element)[0]
                elif key == 'Original Title':
                    # Special deal for Original Title
                    if Prefs['Original_Title']:
                        if consts.DEFAULT == GetRegInfo2(
                                et,
                                value,
                                consts.DEFAULT,
                                key=key,
                                mediaType=mediaType):
                            element = GetRegInfo2(
                                et, '@title', consts.DEFAULT, key='Title',
                                mediaType=mediaType)
                        else:
                            element = GetRegInfo2(
                                et, value, consts.DEFAULT, key=key,
                                mediaType=mediaType)
                    else:
                        element = GetRegInfo2(
                            et,
                            value,
                            consts.DEFAULT,
                            key=key,
                            mediaType=mediaType)
                # part file
                elif key.startswith('Part File'):
                    element = GetRegInfo2(
                        et, value, consts.DEFAULT, key=key,
                        mediaType=mediaType)
                    if key == 'Part File':
                        element = os.path.split(element)[1]
                    elif key == 'Part File Path':
                        element = os.path.split(element)[0]
                # Special guid extract of the language code
                elif key == 'MetaData Language':
                    element = et.get('guid')
                    if '?lang=' in element:
                        element = element[element.index('?lang=') + 6:]
                    if element == '':
                        element = consts.DEFAULT
                    if element.startswith('plex://'):
                        element = consts.DEFAULT
                    if element.startswith('local://'):
                        element = consts.DEFAULT
                elif key == 'Total Playcount':
                    element = consts.DEFAULT
                    url = ''.join((
                         GetLoopBack(),
                         '/status/sessions/history/all?metadataItemID=',
                         myRow['Media ID'],
                         '&X-Plex-Container-Start=0&X-Plex-Container-Size=0'))
                    element = XML.ElementFromURL(url).get('totalSize')
                else:
                    element = GetRegInfo2(et, value, consts.DEFAULT, key=key)
                # Empty fields are still present, but with a length of 0
                if element == '':
                    element = consts.DEFAULT
                if key in myRow:
                    myRow[key] = myRow[key] + Prefs['Seperator'] + element
                else:
                    myRow[key] = element
            except Exception, e:
                Log.Exception('Exception in getItemInfo: ' + str(e))
                myRow[key] = 'error'
                continue
        return myRow
    except Exception, e:
        Log.Exception('Exception in getItemInfo: ' + str(e))


def getMediaPath(myMedia, myRow):
    ''' return the media path info '''
    # Get tree info for media
    try:
        myMediaTreeInfoURL = GetLoopBack() + '/library/metadata/' + \
            GetRegInfo(myMedia, 'ratingKey') + '/tree'
        TreeInfo = XML.ElementFromURL(myMediaTreeInfoURL).xpath('//MediaPart')
        for myPart in TreeInfo:
            MediaHash = GetRegInfo(myPart, 'hash')
            PMSMediaPath = os.path.join(
                Core.app_support_path,
                'Media',
                'localhost',
                MediaHash[0], MediaHash[1:] + '.bundle',
                'Contents')
            myRow['PMS Media Path'] = PMSMediaPath.encode('utf8')
        return myRow
    except Exception, e:
        Log.Exception('Bad Media Path with error: %s' % (str(e)))
        myRow['PMS Media Path'] = 'Error'
        return myRow


def getMetadataPath(myMedia, myRow):
    ''' return the Metadata path info '''
    # Get tree info for media
    try:
        MediaHash = Hash.SHA1(GetRegInfo(myMedia, 'guid'))
        mediaType = GetRegInfo(myMedia, 'type')
        if mediaType == 'movie':
            mediaType = 'Movies'
        elif mediaType == 'show':
            mediaType = 'TV Shows'
        MetadataPath = os.path.join(
                Core.app_support_path,
                'Metadata',
                mediaType,
                MediaHash[0], MediaHash[1:] + '.bundle'
                )
        myRow['PMS Metadata Path'] = MetadataPath.encode('utf8')
        return myRow
    except Exception, e:
        Log.Exception('Bad Metadata Path with error: %s' % (str(e)))
        myRow['PMS Metadata Path'] = 'Error'
        return myRow


def getPlayCountLevel(myMedia, fieldlist):
    ''' return the playcount info for media '''
    # Playcount level selected
    try:
        myRow = {}
        myRow = getItemInfo(myMedia, myRow, fieldlist)
        return myRow
    except Exception, e:
        Log.Exception('getPlayCountLevel error: %s' % (str(e)))
        myRow['Total Playcount'] = 'N/A'
        return myRow


def ConvertSize(SizeAsString):
    ''' converts Byte to best readable string '''
    size = float(SizeAsString)
    if (size == 0):
        return '0B'
    size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = int(math.floor(math.log(size, 1024)))
    p = math.pow(1024, i)
    s = round(size / p, 2)
    return '%s %s' % (s, size_name[i])


def metaDBLink(guid, mediatype='episode', default='N/A'):
    ''' Returns a MetaDb link from a Guid '''
    if 'local://' in guid:
        sTmp = default
        return sTmp
    linkID = guid[guid.index('://') + 3:guid.index('?lang')]
    if 'com.plexapp.agents.imdb' in guid:
        sTmp = 'http://www.imdb.com/title/' + linkID
    elif 'com.plexapp.agents.themoviedb' in guid:
        if mediatype == 'movie':
            sTmp = 'https://www.themoviedb.org/movie/' + linkID
        elif mediatype == 'episode':
            sTmp = 'https://www.themoviedb.org/tv/' + linkID
    elif 'com.plexapp.agents.thetvdb' in guid:
        sTmp = 'https://thetvdb.com/?tab=series&id=' + linkID
    elif 'com.plexapp.agents.anidb' in guid:
        sTmp = 'https://anidb.net/perl-bin/animedb.pl?show=anime&aid=' + linkID
    elif 'com.plexapp.agents.data18' in guid:
        sTmp = 'http://www.data18.com/movies/' + linkID
    elif guid.startswith('plex://'):
        sTmp = default
    else:
        sTmp = default
    return sTmp
