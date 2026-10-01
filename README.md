# StudyEDPPipeline
Pipeline to query the Submission Portal and create the EDP documents for Study Names

Two programs are in this repo and they do the same thing.

## StudyEDPPipeline.py
This will compare the current study names in EDP0008 to the study names pulled from the Submission portal and create a new set of EDP documents if there is a difference.
 
Usage:  **python StudyEDPPipeline.py -c < full/path/to/config/file > -v < verbosity level >**

Dependencies:
- bento_mdf
- bento_meta
- crdclib
- argparse
- pandas
- collections
- requests
- urllib3.util
- yaml


## StudyEDPPipelinePartDeux.py
This does exactly the same thing as *StudyEDPPipeline.py* only it does it in JSON directly rather than an MDF model.  Should be the secondary choice.

Usage:  **python StudyEDPPipelinePartDeux.py -c < full/path/to/config/file > -v < verbosity level >**

Dependencies:
- crdclib
- argparse
- pandas
- collections
- requests
- urllib3.util
- yaml

## Config File fields
Both programs use the same config file fields.  Must be in YAML format, see **configs/SubmissionNameListConfig.yml** for an example.
| Feild | Values | Description |
|-------|--------|-------------|
| tier | prod | | Tells the script which DataHub tier to use.  Can also be stage, qa, qa2, dev, dev2, but only for testing |
| handle | CRDCSN_EDP | Can be something else if needed, but this was the original value |
| nodename | _EDP | Throwaway node name (not used in * StudyEDPPipelinePartDeux.py*) |
| propname | crdc_study_names | Do not change for this EDP |
|-------|--------|-------------|
| outputfiles | | Start of the stanza for the next four files.  Not currently used so can be left out.  All files are tab separated. |
| studynamesFile:| | Full path to a file that will contain a list of the study names |
| studyabbrevFile| | Full path to a file that will contain a list of the study abbreviations |
| comboFile | | Full path to a file that will contain both study name and abbreviations |
| queryresultsFile | | Full path to a file that will contain the full results from the Submission Portal query |
|-------|--------|-------------|
| terminfo | | Start of the stanza for Term constants.  This contains the following 7 lines.
| termdesc| Official study names for CRDC | Do Not Change |
| ext | True | Do Not Change. Must be True for MDF to understand this is an EDP |
| origin | CRDC | Do Not Change.  Indicates that CRDC is the source of this EDP |
| definition | Official study names for CRDC | Probably not worth changing |
| code | CRDC0008 | **DO NOT CHANGE** This is the ID for the EDP, changing it means you'll break anyone using it |
| version | 1 | Should be incremented by 1 with each update |
| value | Official study names for CRDC | Propbably not worth changing |
|-------|--------|-------------|
| outputpath | | Full path to the **folder** that will contain the output MDF files |
| propfile | crdc-studynames-props.yml | Do Not Change.  Name for the Props file. |
| termfile| terms\crdc-studynames-terms.yml | Do Not Change.  Name for the Terms file |
| startingtermfile | | Full path to a file version of the current EDP Terms file. |
| startingtermfileurl |'https://raw.githubusercontent.com/CBIIT/bento-edps/refs/heads/CRDC-StudyNames/model-desc/terms/crdc-studynames-terms.yml' | URL to the GitHub raw copy of the term file.  Preferred over *startingtermfile* |
| force | True/False | If set to True, EDP files will be generated even if there has been no change in the study names. |