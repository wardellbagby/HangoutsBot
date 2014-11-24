__author__ = 'cbagby'

from bs4 import BeautifulSoup
from urllib import request as urllib2
from urllib import parse as urllib

import re

RAPGENIUS_URL = 'http://rap.genius.com'
GENIUS_URL = 'http://genius.com'
RAPGENIUS_SEARCH_PATH = 'search'
RAPGENIUS_ARTIST_PATH = 'artists'
QUERY_INFIX = '?'

RAPGENIUS_ARTIST_URL = '/'.join((GENIUS_URL, RAPGENIUS_ARTIST_PATH))
RAPGENIUS_SEARCH_URL = '/'.join((GENIUS_URL, RAPGENIUS_SEARCH_PATH))


class Artist:
    """
    Container class for Rap Genius artists
    """

    def __init__(self, name, url):
        self.name = name
        self.url = url

        self._popular_songs = []
        self._songs = []

    def __str__(self):
        return self.name + ' - ' + self.url

    def __unicode__(self):
        return self.name + ' - ' + self.url

    @property
    def popular_songs(self):
        """
        Returns songs in the "popular" section of an artist's page
        """

        if not self._popular_songs:
            self._popular_songs = get_artist_popular_songs(self.url)

        return self.popularSongs

    @property
    def songs(self):
        """
        Returns all songs listed for an artist
        """

        if not self._songs:
            self._songs = get_artist_songs(self.url)

        return self._songs


class Song:
    """
    Container class for Rap Genius songs
    """

    def __init__(self, name, url):
        self.name = name
        self.url = url

        self._artist = ""
        self._featured_artists = ""
        self._raw_lyrics = ""

    #TODO - lyric + annotation stuff

    def __str__(self):
        return self.name + ' - ' + self.url

    def __unicode__(self):
        return self.name + ' - ' + self.url

    @property
    def artist(self):
        """
        Returns this song's artist
        """

        if not self._artist:
            self._artist = get_song_artist(self.url)

        return self._artist

    @property
    def featured_artists(self):
        """
        Returns this song's featured artists
        """

        #don't fetch until it's asked for
        if not self._featured_artists:
            self._featured_artists = get_song_featured_artists(self.url)

        return self._featured_artists

    @property
    def raw_lyrics(self):
        """
        Get this song's raw, un-annotated lyrics
        """
        if not self._raw_lyrics:
            self._raw_lyrics = get_lyrics_from_url(self.url)

        return self._raw_lyrics


def _get_soup(url):
    """
    Fetches a page and returns it as a BeautifulSoup object
    """

    return spoof_open_bs(url)


# Parser functions for _get_results() and _get_paginated_results()
def _parse_search(soup):
    """
    Parses Rap Genius song search results and returns a list of Song ojbects
    """
    songs = []

    for row in soup.find_all('a'):
        if (row.get("class") and "song_link" in row.get("class")):
            name = ''.join(row.findAll(text=True)).strip()

            url = row.get('href')

            song = Song(name, url)

            songs.append(song)

    return songs


def _parse_artists(soup):
    """
    Parses Rap Genius artist search results and returns a list of Artist objects
    """

    results = []

    artist_re = re.compile('/artists/.')

    for row in soup.find_all('a', href=artist_re):
        name = ''.join(row.findAll(text=True))
        url = RAPGENIUS_URL + row.get('href')

        artist = Artist(name, url)

        results.append(artist)

    return results


def _get_next_page(soup):
    """
    Gets the relative URL of the next page of paginated results
    """

    next = None

    pagination = soup.find_all('div', 'pagination', 'rel')

    # Determine if the next relative link is enabled
    relative_name = pagination[0].find_all('span')[-1]
    next_enabled = not 'disabled' in relative_name.get('class')

    # Get the url string of the next page if it's available
    if next_enabled:
        relative_link = pagination[0].find_all('a')[-1]
        query = relative_link.get('href')
        next = RAPGENIUS_URL + query

    return next


def _build_query_url(url, search_string):
    """
    Prepare a query URL
    """

    query_string = urllib.urlencode({'q': search_string})
    query_url = QUERY_INFIX.join((url, query_string))

    return query_url


# Result getters
def _get_results(url, parser):
    """
    Parses a single page Rap Genius result page and returns the resulting set
    """

    soup = _get_soup(url)

    return parser(soup)


def _get_paginated_results(url, parser):
    """
    Parses a paginated Rap Genius result page and returns the resulting set
    """

    results = []

    #get the first set of results
    soup = _get_soup(url)
    parsed = parser(soup)
    results.extend(parsed)

    # if there are more pages, get the rest
    # while next_page:
    #     soup = _get_soup(next_page)
    #     parsed = parser(soup)
    #
    #     results.extend(parsed)
    #     next_page = _get_next_page(soup)

    return results


# Search functions
def search_songs(search):
    """
    Searches Rap Genius for all songs matching search,
    returns the results as a list of Song objects
    """

    url = _build_query_url(RAPGENIUS_SEARCH_URL, search)
    songs = _get_paginated_results(url, _parse_search)

    return songs


def search_artists(artist):
    """
    Searches Rap Genius for all artists matching search,
    returns the results as a list of Artist objects
    """

    url = _build_query_url(RAPGENIUS_SEARCH_URL, artist)
    artists = _get_results(url, _parse_artists)

    return artists


# Artist-specific functions
def get_artist_songs(url):
    songs = _get_paginated_results(url, _parse_search)

    return songs


def get_artist_popular_songs(url):
    """
    Returns a list of an artist's popular songs, given a URL
    """

    soup = _get_soup(url)
    songs = []
    for row in soup.find('ul', {'class': 'song_list'}):
        if type(row.find('span')) != int:
            songs.append(
                Song(''.join(row.find('span').findAll(text=True)).strip(), RAPGENIUS_URL + row.find('a').get('href')))

    return songs


# Song-specific functions
def get_lyrics_from_url(url):
    """
    Returns string of (unannotated) lyrics, given a URL
    """

    #TODO - exeptions
    soup = _get_soup(url)
    ret = ""
    for row in soup('div', {'class': 'lyrics'}):
        text = ''.join(row.findAll(text=True))
        data = text.strip() + '\n'
        ret += data
    return data


def get_song_artist(url):
    """
    Returns a song's artist, given a URL
    """

    soup = BeautifulSoup(urllib2.urlopen(url).read(), 'html.parser')
    #For some reason, html was damaged for http://rapgenius.com/Outkast-git-up-git-out-lyrics
    #other songs from same artist seemed fine without specifying 'html.parser'

    info = soup.find('div', {"class": "song_info_primary"})
    artistInfo = info.find("span", {"class": "text_artist"})
    #print artistInfo.find('a').get('href')
    return Artist(artistInfo.findAll(text=True), RAPGENIUS_URL + artistInfo.find('a').get('href'))


def get_song_featured_artists(url):
    """
    Returns a song's featured artists (if any), given a URL
    returns an empty list if there are none
    """

    artists = []
    soup = _get_soup(url)
    for r in soup('div', {'class': 'featured_artists'}):
        for row in r.find_all('a'):
            artists.append(Artist(''.join(row.findAll(text=True)), RAPGENIUS_URL + row.get('href')))
    return artists


def spoof_open_bs(url):
    #http://stackoverflow.com/questions/13720430/issue-scraping-with-beautiful-soup
    opener = urllib2.build_opener()
    opener.addheaders = [('User-Agent', 'Mozilla/5.0')]
    return BeautifulSoup(opener.open(url).read())