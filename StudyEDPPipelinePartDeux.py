# Generate EDP files but not using bento_mdf
from crdclib import crdclib
import argparse
import pandas as pd
import sys
from collections import Counter
import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
import json
import yaml

def updateCheck(termjson, configs, verbose=0):
    if verbose >= 1:
        print("Checking if update is needed")
    # Check to see if there are any new studies.
    # If there is no URL to Github, read the local file
    if verbose >= 2:
        print(f"URL is {configs['startingtermfileurl']} and type {type(configs['startingtermfileurl'])}")
    if configs['startingtermfileurl'] == 'None':
        originaljson = crdclib.readYAML(configs['startingtermfile'])
    # Otherwise read from GithHub
    else:
        originaljson = getGitHubPortalStudies(configs=configs)
    newterms = list(termjson['Terms'].keys())
    oldterms = list(originaljson['Terms'].keys())
    
    if Counter(newterms) == Counter(oldterms):
        return False
    else:
        return True

def getGitHubPortalStudies(configs, verbose=0):
    try:
        retry = Retry(total=5, backoff_factor=2, status_forcelist=[429, 500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retry)
        session = requests.Session()
        session.mount('https://', adapter)
        headers={"Accept": "application/vnd.github.v4+raw"}
        results = session.get(url=configs['startingtermfileurl'], headers=headers, timeout=180)
    except requests.exceptions.HTTPError as e:
        print(e)
        return None
    if results.status_code == 200:
        content = results.content.decode('utf-8')
        yamlresults = yaml.safe_load(content)
        return yamlresults
    else:
        return None



def getPortalStudies(configs, verbose=0):
    query = """
        {
            listSubmissions(status:["All"]){
            submissions{
                _id
                name
                study{
                studyName
                studyAbbreviation
                dbGaPID
                }
                dataCommons
                modelVersion
                nodeCount
                submitterName
                status
                dataType
            }
            }
        }
        """
    if verbose >= 1:
        print("Obtaining credentials")
    creds = crdclib.dhAPICreds(tier=configs['tier'])
    
    if args.verbose >= 1:
            print("Running query for study information")
    res = crdclib.dhApiQuery(creds['url'], creds['token'], query=query)
    
    if args.verbose >= 1:
        print("Obtaining credentials")
    creds = crdclib.dhAPICreds(tier=configs['tier'])
    
    if args.verbose >= 1:
        print("Running query for study information")
    res = crdclib.dhApiQuery(creds['url'], creds['token'], query=query)

    if args.verbose >= 1:
        print("Creating Dataframe")
    df = pd.json_normalize(res['data']['listSubmissions']['submissions'])
    if args.verbose >= 1:
        print("Deduplicating by study name")
    df.drop_duplicates(subset='study.studyName', keep='last', inplace=True)
    
    return df


def buildTermJSON(configs, df, verbose=0):
    if verbose >= 1:
        print("Creating the individtual term json")
    tempterm = {}
    for index, row in df.iterrows():
        if verbose >= 3:
            print(row)
        definition =""
        if verbose >= 2:
            print(f"dbGaPID value: {row['study.dbGaPID']}\tType: {type(row['study.dbGaPID'])}")
        if row['study.dbGaPID'] is not None:
            definition = row['study.dbGaPID']
        else:
            definition = row['dataCommons']
        
        tempterm[row['study.studyAbbreviation']] = {
            'Origin': 'CRDC',
            'Code': row['study.studyAbbreviation'],
            'Version': configs['terminfo']['version'],
            'Value': row['study.studyName'],
            'Definition': definition
        }
        
    finalterm = {}
    finalterm['Terms'] = tempterm
    
    return finalterm


def buildPropJSON(configs, df, verbose=0):
    if verbose >= 1:
        print("Creating final property/node JSON object")
    final = {}
    final['Nodes'] = {}
    final['Relationships'] = {}
    
    #enumlist = df['study.studyName'].unique().tolist()
    enumlist = df['study.studyAbbreviation'].unique().tolist()
    terminfo = [{'Origin': configs['terminfo']['origin'],
                 'Definition':  configs['terminfo']['definition'],
                 'Code': configs['terminfo']['code'],
                 'Version': configs['terminfo']['version'],
                 'Value':  configs['terminfo']['value']}]
    
    termdef = {}
    termdef[configs['propname']] = {
        'Desc':  configs['terminfo']['termdesc'],
        'Ext': 'true',
        'Term': terminfo,
        'Enum': enumlist
    }
    final['PropDefinitions'] = termdef
    
    return final


def main(args):
    
    configs = crdclib.readYAML(args.configfile)
    
    # Get the study info from the portal
    df = getPortalStudies(configs=configs, verbose=args.verbose)
    
    # Build the Term json
    finalterm = buildTermJSON(configs=configs, df=df, verbose=args.verbose)
    
    # Check agaisnt the bento-eps repo to see if the new names differ from the old names.
    aredifferent = updateCheck(termjson=finalterm, configs=configs, verbose=args.verbose)
    
    #Trigger to force a run, even if there is a match
    if configs['force']:
        if args.verbose >= 1:
            print("Forcing an update")
        aredifferent = True
        
    #It only makes sense to continue if the new and existin are different
    if aredifferent:
        if args.verbose >= 1:
            print("New studies detected, creating new EDP files")
        finalprop = buildPropJSON(configs=configs, df=df, verbose=args.verbose)
        
        # And print them both
    
        filename = f"{configs['outputpath']}{configs['propfile']}"
        crdclib.writeYAML(filename=filename, jsonobj=finalprop)
        
        filename = f"{configs['outputpath']}{configs['termfile']}"
        crdclib.writeYAML(filename=filename, jsonobj=finalterm)
    else:
        if args.verbose >= 1:
            print("No new studies found, no update needed")
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--configfile", required=True,  help="Configuration file containing all the input info")
    parser.add_argument('-v', '--verbose', action='count', default=0, help=("Verbosity: -v main section -vv subroutine messages -vvv data returned shown"))
    parser.add_argument('-f', '--full_data', action='store_true', help="Store the full query output to a file")

    args = parser.parse_args()

    main(args)