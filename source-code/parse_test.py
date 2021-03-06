"""
This program/module parses scores from https://wgi.org for the scores from each
competition. Writes each Competition to competitions.json and each Group
to groups.json.
"""
from dataclasses import dataclass
import json
import logging
import os
# import re
import sys
import datetime as dt
# from flask import Flask
import requests
from bs4 import BeautifulSoup as bs

URLS = "./urls.json"
CACHE = {}

# Classes

@dataclass()
class Group:
    """creates a group class object"""
    name: str
    class_level: str
    location: str

@dataclass()
class Competition:
    """creates a competition class object"""
    title: str
    date: str
    scores: str
    recap: str
    groups: list
    scores_by_group: dict




# Functions
def read_json(filepath:str, encoding='utf-8') -> dict:
    """Reads a json file and returns a dictionary of the object
    """
    with open(filepath, 'r', encoding=encoding) as file_obj:
        return json.load(file_obj)

def write_json(filepath:str, data, encoding='utf-8', ensure_ascii=False, indent=4):
    """ Serializes object as JSON. Writes content to the provided filepath.
        Appends to the end of the file. Checks if filepath exists.
        If not, appends file creating a new one if the file does not exists,
        else writes over the file. If add=True, appends to the end of the file.

    Parameters:
        filepath (str): the path to the file
        data (dict)/(list): the data to be encoded as JSON and written to the file
        encoding (str): name of encoding used to encode the file
        ensure_ascii (str): if False non-ASCII characters are printed as is; otherwise
                            non-ASCII characters are escaped.
        indent (int): number of "pretty printed" indention spaces applied to encoded JSON

    Returns:
        None
    """
    if not os.path.exists(filepath):
        with open(filepath, 'a', encoding=encoding) as file_obj:
            json.dump(data, file_obj, ensure_ascii=ensure_ascii, indent=indent)
    else:
        with open(filepath, 'w', encoding=encoding) as file_obj:
            json.dump(data, file_obj, ensure_ascii=ensure_ascii, indent=indent)

def get_content(url:str) -> str:
    """Takes a url and returns the html content

    params:
        url(string): link to html content

    returns:
        response.text: html content
    """
    response = requests.get(url)
    logger.info("Fetching content from %s", url)

    return response.text

def cache_page(url:str) -> str:
    """checks cache for url, returns html content
    """
    logger.info("Checking cache for: %s", url)
    if url not in CACHE:
        CACHE[url] = get_content(url)
        logger.info("Added page to cache: %s", url)

    write_json('./cache/cache.json', CACHE)

    return CACHE[url]


def get_competitions(url:str) -> list:
    """ parses html data and returns a list of Competitions
    """
    html_data = cache_page(url) # get html content
    soup = bs(html_data, 'html.parser')
    logger.info("Parsing page: %s", url)

    table_rows = soup.find_all('tr') # list of table rows

    comps = []

    for t_r in table_rows[:-1]:
        tr_children = [child for child in t_r.children] # find children
        if len(tr_children) == 3: # rows with dates
            date = tr_children[1:-1:1][0].strong.contents[0]
        elif len(tr_children) == 9: # rows with groups and scores
            tr_children_data = tr_children[1::2][1:]
            comp_name = tr_children_data[0].contents # get competition name # list
            if tr_children_data[1].a: # check if there is a link to scores # some don't have scores
                scores = tr_children_data[1].a['href'] # get link to scores
            else:
                scores = "No scores"
            if tr_children_data[-1].a:
                recaps = tr_children_data[-1].a['href'] # get link to recaps
            else:
                recaps = "No recaps"

            # create Competition obj with placeholder for groups and scores_by_group
            comp_data = Competition(comp_name, date, scores, recaps, [], {})
            comps.append(comp_data)
    return comps

def get_groups_scores(comp_obj:Competition):
    """ parses page with scores. Returns a tuple that contains a list of Groups and a dictionary of scores_by_group
    """
    scores_page = comp_obj.scores # url for scores page
    if "https://" not in comp_obj.scores : # == "No scores"
        groups_list = []
        scores_by_group = {}
    else:
        html_data = cache_page(scores_page)
        soup = bs(html_data, 'html.parser')
        logger.info("Parsing page: %s", scores_page)

        groups_list = []
        scores_by_group = {}

        scores_div = soup.find_all('div', attrs={'class': 'table-responsive'}) # list of div elements # len = 1
        scores_table = scores_div[0].table # .table.tbody.tr.td.table
        table_rows = scores_table.find_all('tr')
        for row in table_rows:
            tcells = [child for child in row.children]
            if len(tcells) == 3: # rows with class levels
                class_level = tcells[1].b.contents[0] # group class_level
            elif len(tcells) == 4: # rows with group names
                em = tcells[2].contents[1]
                group_name = tcells[2].contents[0].strip() # group names
                location = em.contents[0].replace('(', '').replace(')', '') # group location

                score = tcells[-1].b.contents[0]

                group = Group(group_name, class_level, location)
                groups_list.append(group)

                scores_by_group[group.name] = score

        return groups_list, scores_by_group





# TODO create graph




if __name__ == '__main__':
    # Configure logger: set format and default level
    logging.basicConfig(
        format='%(levelname)s: %(message)s',
        level=logging.DEBUG
    )

    # Create logger
    logger = logging.getLogger()

    # Create logger filename and path
    LOGPATH = "./wgi_score_parser_log.log"

    # Add logger file and stream handlers
    logger.addHandler(logging.FileHandler(LOGPATH)) # write log to file
    logger.addHandler(logging.StreamHandler(sys.stdout)) # stream log to stdout

    # Start logger
    start_date_time = dt.datetime.now()
    # logger.info(f"Start run: {start_date_time.isoformat()}")
    logger.info("Start run: %s", start_date_time.isoformat()) # log start time

    TEST = 'https://wgi.org/percussion/2019-perc-scores/'
    TEST_SCORES = 'https://wgi.org/wp-content/uploads/wgi_events/static_scores/2019/scores_CG_A_Class_Finals_UD_Arena.html'

    comps_to_write = []
    groups_to_write = []

    for link in read_json('./urls.json'):
        competitions = get_competitions(link) # list of Competitions
        for comp in competitions:
            groups_and_scores = get_groups_scores(comp)
            if isinstance(groups_and_scores, tuple):
                groups, scores = groups_and_scores
                comp.groups = groups # update Competition class obj with groups list
                comp.scores_by_group = scores
                if len(groups) > 1:
                    for group in groups:
                        group_json = {
                            "name": group.name,
                            "class_level": group.class_level,
                            "location": group.location
                        }
                        if group_json not in groups_to_write:
                            groups_to_write.append(group_json)

                comp_json = {
                    "title": comp.title[0],
                    "date": comp.date,
                    "scores": comp.scores,
                    "recaps": comp.recap,
                    "groups": [group.name for group in comp.groups],
                    "scores_by_group": comp.scores_by_group
                }
                if comp_json not in comps_to_write:
                    comps_to_write.append(comp_json)

    write_json('./data/groups.json', groups_to_write)
    logger.info("%s Groups written to file.", len(groups_to_write))
    write_json('./data/competitions.json', comps_to_write)
    logger.info("%s Competitions written to file.", len(comps_to_write))

    logger.info("End run: %s", dt.datetime.now().isoformat()) # log end time
