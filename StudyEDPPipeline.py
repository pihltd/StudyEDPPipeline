#from crdclib import crdclib
import argparse
import pandas as pd
from collections import Counter
from bento_meta.model import Model
import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
import yaml
import logging

import sys
sys.path.append('../')
from CRDCLib.src.crdclib import crdclib

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


def updateCheck(portalstudylist, configs, verbose=0):
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
    oldterms = list(originaljson['Terms'].keys())
    
    if Counter(portalstudylist) == Counter(oldterms):
        return True 
    else:
        return False


def checkDiff(portalstudylist, configs, verbose=0):
    if verbose >= 1:
        print("Generated Diff")
    
    if configs['startingtermfileurl'] == 'None':
        originaljson = crdclib.readYAML(configs['startingtermfile'])
    # Otherwise read from GithHub
    else:
        originaljson = getGitHubPortalStudies(configs=configs)
    oldterms = list(originaljson['Terms'].keys())

    newstudies = []
    for study in portalstudylist:
        if study not in portalstudylist:
            newstudies.append(study)
    return newstudies


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


def main(args):
    
    configs = crdclib.readYAML(args.configfile)
    
    # Set up logging
    logging.basicConfig(filename=configs['logfile'], level=logging.INFO, format='%(asctime)s  - %(levelname)s - %(message)s ')
   
    
    df = getPortalStudies(configs=configs, verbose=args.verbose)
    
    # Look to see if an update is needed
    portalstudylist = df['study.studyAbbreviation'].unique().tolist()
    
    #Check to see if there are any changes
    aredifferent = updateCheck(portalstudylist=portalstudylist, configs=configs, verbose=args.verbose)
    # If set to force, proceed regardles of changes
    if configs['force']:
        logging.info('Forcing new file creation')
        if args.verbose >= 1:
            print("Forcing an update")
        aredifferent = True

    if aredifferent:
        #proceed if True
        if configs['updatediff']:
            newstuff = checkDiff(portalstudylist=portalstudylist, configs=configs, verbose=args.verbose)
            for entry in newstuff:
                logging.info(f"New study {entry} ")
        if args.verbose >= 1:
            print('Changes found in studies, creating update files')
            print("Creating empty model")
        edp_mdf = Model(handle=configs['handle'], version=configs['terminfo']['version'])
        
        # Need a node because you can't have a property without a node.
        if args.verbose >= 1:
            print("Creating sacrificial node")
        edp_mdf = crdclib.mdfAddNodes(edp_mdf, [configs['nodename']])
        
        if args.verbose >= 1:
            print("Creating property")
        propinfo = {'prop':configs['propname'], 
                    'isreq': 'No',
                    'iskey': 'No',
                    'val': 'value_set' ,
                    'desc': 'Official CRDC Study names'}
                    #'is_extended': 'True'}
        
        edp_mdf = crdclib.mdfAddProperty(edp_mdf,{configs['nodename']:[propinfo]})
        
        # So, it turns out that if you use prop.add_term it also populates the Enum section 
        if args.verbose >= 1:
            print("Adding the terms")
        for index, row in df.iterrows():
            definition =""
            # Definition should be dbGaPID if there is one, otherwise use the data commons name
            if row['study.dbGaPID'] is not None:
                definition = row['study.dbGaPID']
            else:
                definition = row['dataCommons']
                
            terminfo = {'handle': row['study.studyAbbreviation'],
                        'value':row['study.studyName'],
                        'origin_version': configs['terminfo']['version'],
                        'origin_name': configs['terminfo']['origin'],
                        'origin_id':row['study.studyAbbreviation'],
                        'origin_definition': definition}
            if args.verbose >= 2:
                print(f"{terminfo}\n")        
            edp_mdf = crdclib.mdfAddTerms(mdfmodel=edp_mdf, nodename=configs['nodename'], propname=configs['propname'], termdict=terminfo)
        

        if args.verbose >= 1:
            print(f"Writing files to {configs['outputpath']}")
        logging.info(f"Writing files to {configs['outputpath']}")
        filenamedict = {'model':configs['propfile'], 'terms':configs['termfile']}
        sectionlist = ['Model', 'Terms']
        crdclib.mdfWriteModelFiles(mdf=edp_mdf, sectionlist=sectionlist, writedir=configs['outputpath'], filenamedict=filenamedict)
    
    else:
        logging.info('No new studies found')
        if args.verbose >= 1:
            print('No change in studies, no update needed')
            
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--configfile", required=True,  help="Configuration file containing all the input info")
    parser.add_argument('-v', '--verbose', action='count', default=0, help=("Verbosity: -v main section -vv subroutine messages -vvv data returned shown"))
    parser.add_argument('-f', '--full_data', action='store_true', help="Store the full query output to a file")

    args = parser.parse_args()

    main(args)