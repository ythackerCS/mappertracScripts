The following github is built to work with mappertrac library desiged by UCSD 
There are multiple scripts that are used to process and find compatible subjects for mappertrac 

Order of use and Purpose: 
1) batch_get_uniqueseriesdescription.sh - is used for getting each unique series description within a main folder (this is used for dcm2bids converter and provdes a list of unique_series_descriptions used to make the json needed for dcm2bids) 
    1b) getseries.py - similar to above but used for one specific folder 
2) dcm2bidsautomation.sh - uses the json made from above descriptions e.g. dcm2bids_largesample.json to convert every subject within a folder 
    2b) dcm2bidsautomation_avoidDuplicats.sh - same as above but avoids duplicates incase youve run it before 
3) getcompaiblesubjects.sh - will go through the folder of your converted data from above and find a list of compatible subjects (subjects that contain a T1 (anat) and a diffusion scan with bval total > 30) that fit requirements needed for mappertrac 
4) match_familytype2compatiblesubject.py -  will match compatible subjects to their corresponding classification using a csv and their extracted ID from subject folder
5) run_s1_tier1.sh - runs step 1 of mappertrac 
6) run_s2_tier1.sh - runs s2
7) run_s3_tier1.sh - runs s3 


Please note any or all files may need modification for your use case. 
