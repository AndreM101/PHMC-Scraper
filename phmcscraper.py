import datetime
from time import sleep
from selenium import webdriver
import pandas as pd


"""
urlOptions is a dictionary specifying url embedded options for retrieval and is of the form
{
        RemoveUndeterminedApplications: True/False,
        ShowOutstandingApplications: True/False,
        ShowExhibitedApplications: True/False,
        IncludeDocuments: True/False
}

daysToScrape is an positive integer specifying the number of days the scrape should request (starting from today)

quiet is a boolean specifying whether to produce progress output whilst rummaging through records. True will suppress output

Return type: Pandas DataFrame consisting of the council_number as index and each attribute found as their relevant name, defaulting to the name given by the council if not specified by PlanningAlerts
"""

def scrape(urlOptions = {}, daysToScrape=30, quiet=True):
    urlOptions = {}
    if type(urlOptions) != dict or type(daysToScrape) != int or daysToScrape < 1:
        print("Invalid parameter(s)")
        return
    
    validOptions= {"RemoveUndeterminedApplications": False,'ShowOutstandingApplications': False,'ShowExhibitedApplications': False,'IncludeDocuments': False}
    
    #Examine the provided options, assign the valid sets and ignore invalid sets
    for op in urlOptions:
        if op in validOptions.keys():
            validOptions[op] = urlOptions[op]

    options = webdriver.FirefoxOptions()
    options.headless = True
    browser = webdriver.Firefox(options=options)

    browser.get("https://datracker.pmhc.nsw.gov.au/")
    #load disclaimer page
    
    browser.find_element_by_id("agree").click()
    #accept disclaimer

    now = datetime.datetime.now()
    DateTo = datetime.datetime.strftime(now, "%d%%2f%m%%2f%Y")
    #format to day%2fmonth%2fyear

    if DateTo[0] == '0':
        DateTo = DateTo[1:]
    #the day's leading zero is not used in the example I found, hance it is removed to be safe
        
    startDate = now - datetime.timedelta(days=30)
    #find the date (roughly) a month before today

    DateFrom = datetime.datetime.strftime(startDate, "%d%%2f%m%%2f%Y")
    #format to day%2fmonth%2fyear

            
    
    requestURL = "https://datracker.pmhc.nsw.gov.au/Application/AdvancedSearchResult?DateFrom=" + DateFrom + "&DateTo=" + DateTo + "&DateType=1&ApplicationType=&"
    #load template and dates
    
    for op in validOptions.keys():
        requestURL += op + "=" + str(validOptions[op]).lower() + "&"
    requestURL = requestURL[:-1]
    #add the options on, then remove the trailing &
    
    sleep(5)
    
    browser.get(requestURL)
    #load the request

    sleep(5)
    #wait for the page to load properly

    data = {}

    table = browser.find_element_by_id("applicationsTable")
    
    labels = [attribute.text for attribute in table.find_elements_by_xpath("thead/tr/th")]
    # fetch column labels from the table

    indexColumn = labels.index("Application Number")
    pageCount = int(browser.find_element_by_id("applicationsTable_paginate").find_element_by_xpath("ul/li[9]/a").text)
    # fetch constants from the webpage

    
    for page in range(pageCount):
        # loop for every page
        if not quiet:
            print("Page",page,"out of",pageCount,"("+str((1+page)/pageCount*100)[:5]+"%)")
        rows = table.find_elements_by_xpath("tbody/tr")
        for row in rows:
            #loop for every row on the current page
            cells = row.find_elements_by_xpath("td")
            index = cells[indexColumn].text
            
            parsedRowData = {}
            for attribute in range(len(labels)):
   
                if labels[attribute] == "Application Number":
                    index = cells[attribute].text
                #the application number is treated as the key rather than as an attribute, so it gets stored separately
                
                elif labels[attribute] == "Show":
                    link = cells[attribute].find_element_by_link_text("Details").get_attribute("href")
                    parsedRowData['info_url'] = link
                    # the info link cannot be gathered from '.text', so an edge case is needed
                    
                elif labels[attribute] == "Details":
                    rawDesc = cells[attribute].text
                    description = rawDesc.split("\n")[-1]
                    address = rawDesc.split("\n")[:-1]
                    address = ", ".join(address)
                    # currently, the details cell holds both description and address - these need to be separated then parsed properly
                    
                    parsedRowData['address'] = address
                    parsedRowData['description'] = description
                    
                else:
                    # any other columns are treated as-is (text) and are stored normally
                    parsedRowData[labels[attribute]] = cells[attribute].text

            parsedRowData['date_scraped'] = datetime.datetime.strftime(datetime.datetime.now(), "%Y-%M-%d")
            data[index] = parsedRowData
            # save the parsed data to the dictionary with the key attached
            
        pageNum = browser.find_element_by_id("applicationsTable_info").text    
        browser.find_element_by_id("applicationsTable_paginate").find_element_by_xpath("ul/li[10]/a").click()                
        while pageNum == browser.find_element_by_id("applicationsTable_info").text:
            sleep(1)
            if pageNum.split(" ")[-2] == pageNum.split(" ")[-4]:
                break
        # go to the next page - if this is the final page (denoted by the entry count equalling the shown top entry number) then break the loop as every page has been accounted for
            
    browser.quit()
    return pd.DataFrame.from_dict(data,orient='index')
    # Selenium and data cleanup beore returning
