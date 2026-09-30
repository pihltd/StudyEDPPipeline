from crdclib import crdclib
import argparse
import pandas as pd
from bento_mdf import MDFWriter
from bento_meta.model import Model, Term
import sys


def mdfWriteModelFiles(mdf, sectionlist, writedir):
    """
    Writes out an mdf model object to one or more YAML files.  Does some sorting to get the YAML in proper order (Handle/Version/Nodes/Properties)

    :param mdf: MDF Model Object
    :type mdf: MDF model
    :param sectionlist: A list of the sections that should be printed.  Allowed value are Model, PropDefinitions, Terms, Relationships.
    :type sectionlist: List
    :param writedir: The direcotory to write the MDF files into
    :type writedir: String
    """

    tempdict = MDFWriter(mdf).mdf
    mdfdict = {}
    allowedsectionlist = ['Handle', 'Version', 'Nodes', 'Relationships', 'PropDefinitions', 'Terms']

    #Sorts keys for order in yaml
    for entry in allowedsectionlist:
        if entry in tempdict.keys():
            mdfdict[entry] = tempdict[entry]
    for key in tempdict.keys():
        if key not in allowedsectionlist:
            mdfdict[key] = tempdict[key]

    if len(sectionlist) > 1:
        for section in sectionlist:
            if section in allowedsectionlist:
                if section != 'Model':
                    filename = f"{writedir}{mdf.handle}-model-{section.lower()}.yml"
                    printnode = {}
                    printnode[section] = mdfdict.pop(section, None)
                    print(f"Writing file {filename}")
                    crdclib.writeYAML(filename=filename, jsonobj=printnode)
    #Now write out whatever is left.  If Model is only section, it all gets printed
    filename = f"{writedir}{mdf.handle}-model.yml"
    crdclib.writeYAML(filename=filename, jsonobj=mdfdict)

# TODO: Build a check to see if the EDP matches what is in the Submission Portal

def main(args):
    
    configs = crdclib.readYAML(args.configfile)
    
    # Get the study info from the portal
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
    
    if args.verbose >= 1:
        print("Creating empty model")
    #edp_mdf = bento_mdf.MDF(handle='StudyNameEDP')
    edp_mdf = Model(handle='StudyNameEDP')
    #edp_mdf = edp_mdf.model
    
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
    
    edp_mdf = crdclib.mdfAddProperty(edp_mdf,{configs['nodename']:[propinfo]})
    
    if args.verbose >= 1:
        print("Annotating the overarching Term")
    terminfo = {'Origin': configs['terminfo']['origin'], 
                'Definition':configs['terminfo']['definition'], 
                'Code': configs['terminfo']['code'],
                'Version': configs['terminfo']['version'],
                'Value': configs['terminfo']['value']}
    
    #edp_mdf = crdclib.mdfAnnotateTerms(mdfmodel=edp_mdf, nodename=configs['nodename'], propname=configs['propname'], termdict=terminfo)
    '''
    if args.verbose >= 1:
        print("Adding the enums")
    ## Get lists of names and abbreviations
    studylist = df['study.studyName'].unique().tolist()
    edp_mdf = crdclib.mdfAddEnums(mdfmodel=edp_mdf, nodename=configs['nodename'], propname=configs['propname'], enumlist=studylist)
    '''
    
    if args.verbose >= 1:
        print("Adding the individual terms")
    for index, row in df.iterrows():
        terminfo = {'Origin': configs['terminfo']['origin'], 
                'Definition':row['study.studyAbbreviation'], 
                'Code': configs['terminfo']['code'],
                'Version': configs['terminfo']['version'],
                'Value': row['study.studyName']}
        print(terminfo)
        propobj = edp_mdf.props[configs['nodename'], configs['propname']]
        termobj = Term(terminfo)
        edp_mdf.add_terms(propobj, termobj)
        
        #edp_mdf = crdclib.mdfAddTerms(mdfmodel=edp_mdf, nodename=configs['nodename'], propname=configs['propname'], termdict=terminfo)
    

    if args.verbose >= 1:
        print(f"Writing files to {configs['outputpath']}")
        print(edp_mdf.nodes)
        print(edp_mdf.props)
        print(edp_mdf.terms)
    sectionlist = ['Model', 'Terms']
    mdfWriteModelFiles(mdf=edp_mdf, sectionlist=sectionlist, writedir=configs['outputpath'])
    
    
    
    
    
    #abbrevlist = df['study.studyAbbreviation'].unique().tolist()
    #if args.verbose >= 2:
    #    print(f"List of all studies:\n{studylist}\n")
    #    print(f"List of all abbreviations:\n{abbrevlist}\n")
    
    #big_kahuna = []
    #for index, row in df.iterrows():
    #    big_kahuna.append({row['study.studyName']:row['study.studyAbbreviation']})
    
    # The append statement creates a tuple, need to cast to a dictionary
    #big_kahuna = [dict(t) for t in {tuple(d.items()) for d in big_kahuna}]
    
    #for entry in big_kahuna:
    #    for name, abbrev in entry.items():
            
    
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--configfile", required=True,  help="Configuration file containing all the input info")
    parser.add_argument('-v', '--verbose', action='count', default=0, help=("Verbosity: -v main section -vv subroutine messages -vvv data returned shown"))
    parser.add_argument('-f', '--full_data', action='store_true', help="Store the full query output to a file")

    args = parser.parse_args()

    main(args)