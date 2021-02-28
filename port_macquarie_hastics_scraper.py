import requests
import urllib
import json
from datetime import datetime
from datetime import timedelta
import re

# MAX_RECORDS_TO_RETRIEVE is a constant for the number of extracted
# applications and is required for the API call. If there are more
# applications available, this number will be increased to accomodate.
MAX_RECORDS_TO_RETRIEVE = 999
URL = 'https://datracker.pmhc.nsw.gov.au/Application/GetApplications'
HEADERS = {
  'Accept': 'application/json',
  'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
  'Cookie': 'User=accessAllowed-MasterView=True',
  'Host': 'datracker.pmhc.nsw.gov.au'
}


def send_request(date_from, date_to):
    """ Creates and sends a request to the PMHC server then returns
    the resulting data in json format

    Positional arguments:
    date_from -- starting date to select applications after, string of
                 the form "dd/mm/yyyy"


    date_to -- ending date to select applications before, string of the
                form "dd/mm/yyyy"

    Returns a dictionary of the form 
    {"draw": None, "recordsTotal": (int), "recordsFiltered": (int), "data": (list)}
    """
    global MAX_RECORDS_TO_RETRIEVE
    form_data = {
        'start': 0,
        'length': MAX_RECORDS_TO_RETRIEVE,
        'json': json.dumps({
            'DateFrom': date_from,
            'DateTo': date_to,
            'RemoveUndeterminedApplications': False,
            'IncludeDocuments': False})
    }
    payload = urllib.parse.urlencode(form_data)    
    response = requests.request('POST', URL, headers=HEADERS, data=payload)
    response_data = response.json()

    # The total number of records may be higher than the constant used.
    # If this is the case, set the constant to the number of records and
    # perform the request again.
    if response_data['recordsTotal'] > MAX_RECORDS_TO_RETRIEVE:
        MAX_RECORDS_TO_RETRIEVE = response_data['recordsTotal']
        return send_request()
    else:
        return response_data


def clean(raw_data):
    """ Accepts the raw data generated from send_request and cleans it
    into a usable format.

    Returns a dictionary of the form seen directly below
    """
    cleaned_data = {
        'council_reference': [],
        'address': [],
        'application_type': [],
        'description': [],
        'info_url': [],
        'date_scraped': [],
        'date_received': [],
    }
    for row in raw_data:
        # The retrieved data contains a reference number, which can be used
        # to generate a link for the relevant details page as seen below
        link_number = row[0]
        link = ('https://datracker.pmhc.nsw.gov.au/Application/'
               'ApplicationDetails/' + link_number + '/')
        index = row[1]
        application_type = row[2]
        date_received = datetime.strptime(row[3], '%d/%m/%Y')
        date_received = datetime.strftime(date_received, '%Y-%m-%d')
        date_scraped = datetime.strftime(datetime.now(), '%Y-%m-%d')
        # The following regex is intended to split on cases of <b>, </b> and <br/>
        # and generates an array with useful information in indexes 0 and 2
        raw_description = re.split('<.{1,5}>',row[4])
        address = raw_description[0].strip()
        description = raw_description[2]

        cleaned_data['council_reference'].append(index)
        cleaned_data['address'].append(address)
        cleaned_data['application_type'].append(application_type)
        cleaned_data['description'].append(description)
        cleaned_data['info_url'].append(link)
        cleaned_data['date_received'].append(date_received)
        cleaned_data['date_scraped'].append(date_scraped)
    return cleaned_data


def scrape(days=30):
    """ Effectively a main function for scraping the PMHC website as required

    Keyword arguments:
    days -- the number of days to scrape, defaulting to 30, integer

    Returns a dictionary of arrays containing cleaned data. See "clean" for return specifications
    """
    date_to = datetime.strftime(datetime.now(), '%d/%m/%Y')
    date_from = datetime.strftime(datetime.now()-timedelta(days=days), '%d/%m/%Y')
    raw_data = send_request(date_from, date_to)
    clean_data = clean(raw_data['data'])
    return clean_data

if __name__ == "__main__":
    clean_data = scrape()
