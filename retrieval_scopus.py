# Code to download abstract from Scopus API based on keywords or author names or titles or DOIs
import os
from dotenv import load_dotenv
import pandas as pd
import numpy as np
import os
import logging 
from pyscopus import Scopus
import requests
from itertools import chain
"""
Reference: https://dev.elsevier.com/sc_search_tips.html
https://dev.elsevier.com/documentation/ObjectRetrievalAPI.wadl#d1e5005
http://zhiyzuo.github.io/python-scopus/doc/quick-start.html
https://www.scopus.com/results/results.uri?sort=plf-f&src=s&st1=quantum+yield&sid=db4a6db3614be43d78c0c45974b0abcf&sot=b&sdt=b&sl=28&s=TITLE-ABS-KEY%28%27quantum+yield%27+AND+%27rate+constant%27%29&origin=searchbasic&editSaveSearch=&sessionSearchId=db4a6db3614be43d78c0c45974b0abcf&limit=10
Code to automate the download of scopus literatures
"""
#%% Define classes
class search_pub:
    @staticmethod
    def search_by_keyword(lst_key, pub_limit=25):
        """
        Search publications by a list of keywords.

        Args:
            lst_key (list): List of keywords.
            pub_limit (int): Maximum number of publications to retrieve.

        Returns:
            tuple: DataFrame of publications, status message.
        """
        try:
            df = scopus.search(f"KEY({lst_key})", count=pub_limit, view='COMPLETE')
            message = 'IP address recognized by Scopus. Connected with COMPLETE view.'
        except Exception:
            df = scopus.search(f"KEY({lst_key})", count=pub_limit, view='STANDARD')
            message = ('Not accessible to Scopus COMPLETE view. '
                       'Using STANDARD view. See: https://dev.elsevier.com/api_key_settings.html')
        print(message)
        return df, message

    @staticmethod
    def search_by_name(first_name, last_name, affiliation, search_publication=False, pub_limit=20):
        """
        Search for an author by name and affiliation, optionally retrieve their publications.

        Args:
            first_name (str): Author's first name.
            last_name (str): Author's last name.
            affiliation (str): Affiliation name.
            search_publication (bool): Whether to retrieve publications.
            pub_limit (int): Maximum number of publications to retrieve.

        Returns:
            tuple: DataFrame of authors, DataFrame of publications (empty if not requested).
        """
        df = scopus.search_author(
            f"AUTHLASTNAME({last_name}) and AUTHFIRST({first_name}) and AFFIL({affiliation})"
        )
        if search_publication and not df.empty:
            df2 = scopus.search_author_publication(df.loc[0, 'author_id'], count=pub_limit)
        else:
            df2 = pd.DataFrame()
        return df, df2


class retrieve_pub:
    @staticmethod
    def retieve_abstracts(df):
        """
        Retrieve abstracts for each publication in the DataFrame using Scopus ID.

        Args:
            df (pd.DataFrame): DataFrame containing 'scopus_id' column.

        Returns:
            pd.DataFrame: DataFrame with an added 'Abstract' column.
        """
        if 'scopus_id' not in df.columns:
            raise KeyError('Make sure scopus_id is included in df')

        df = df.copy()
        abstracts = []
        for i, sid in enumerate(df['scopus_id']):
            print(f'Retrieving abstract for ref #{i}/{len(df)-1}')
            try:
                abst = scopus.retrieve_abstract(sid, './').get('abstract', None)
            except Exception as e:
                print(f"Failed to retrieve abstract for {sid}: {e}")
                abst = None
            abstracts.append(abst)
        df['Abstract'] = abstracts
        return df

    @staticmethod
    def retrieve_fulltext(df):
        """
        Retrieve full text for each publication in the DataFrame using 'full_text' column.

        Args:
            df (pd.DataFrame): DataFrame containing 'full_text' column.

        Returns:
            pd.DataFrame: DataFrame with an added 'fulltext' column.
        """
        if 'full_text' not in df.columns:
            raise KeyError('Make sure full_text is included in df')

        df = df.copy()
        fulltexts = []
        for i, fid in enumerate(df['full_text']):
            try:
                fulltxt = scopus.retrieve_full_text(fid)
            except Exception as e:
                print(f"Failed to retrieve full text for {fid}: {e}")
                fulltxt = ''
            fulltexts.append(fulltxt)
        df['fulltext'] = fulltexts
        return df

    
class process_pub:
    @staticmethod
    def get_id_from_ref(references):
        """
        Flatten a list of reference lists and remove duplicates.

        Args:
            references (iterable): Iterable of lists of reference IDs.

        Returns:
            list: Unique reference IDs.
        """
        ref_all_id = list(chain.from_iterable(references))
        ref_all_id = list(dict.fromkeys(ref_all_id))  # Remove duplicates, preserve order
        return ref_all_id

    @staticmethod
    def get_doi_from_ref(df):
        """
        Extract DOIs from a DataFrame.

        Args:
            df (pd.DataFrame): DataFrame containing 'doi' column.

        Returns:
            pd.Series: Series of DOIs.
        """
        if 'doi' not in df.columns:
            raise KeyError('Make sure doi is included in df')
        return df['doi']

    @staticmethod
    def get_pub_from_id(scopus_ids):
        """
        Retrieve publication metadata for a list of Scopus IDs.

        Args:
            scopus_ids (iterable): List or Series of Scopus IDs.

        Returns:
            pd.DataFrame: DataFrame of publication metadata.
        """
        ref_all_id = process_pub.get_id_from_ref(scopus_ids)
        print(f'Note: {len(ref_all_id)} papers found. This may take a while...')
        df1 = pd.DataFrame()
        for i, ref_id in enumerate(ref_all_id):
            print(f'Looking for ref #{i+1}/{len(ref_all_id)}')
            try:
                result = scopus.search(f"eid(2-s2.0-{ref_id})", count=1)
            except Exception:
                print('Encountered an error, retrying with STANDARD view...')
                result = scopus.search(f"eid(2-s2.0-{ref_id})", count=1, view='STANDARD')
            df1 = pd.concat([df1, result], ignore_index=True)
        return df1

    @staticmethod
    def get_pub_from_ref(df):
        """
        Retrieve publications based on references in a DataFrame.

        Args:
            df (pd.DataFrame): DataFrame containing 'reference' column.

        Returns:
            pd.DataFrame: DataFrame of referenced publications with abstracts.
        """
        if 'reference' not in df.columns:
            raise KeyError('Make sure reference is included in df')
        df1 = process_pub.get_pub_from_id(df['reference'])
        if 'doi' in df1.columns:
            df1.dropna(subset=['doi'], inplace=True)
        df1.reset_index(drop=True, inplace=True)
        df1 = retrieve_pub.retieve_abstracts(df1)
        # Optionally: df1 = retrieve_pub.retrieve_fulltext(df1)
        # Optionally: df1 = retrieve_pub.retrieve_keywords_references_chemicals(df1)
        return df1

    @staticmethod
    def download_paper(df, formats='pdf'):
        """
        Download papers by Scopus ID.

        Args:
            df (pd.DataFrame): DataFrame containing 'scopus_id' column.
            formats (str): File format to download (default: 'pdf').
        """
        if 'scopus_id' not in df.columns:
            raise KeyError('Make sure scopus_id is included in df')
        for sid in df['scopus_id']:
            url = f'https://api.elsevier.com/content/article/scopus_id/{sid}'
            headers = {
                'Accept': f'application/{formats}',
                'X-ELS-APIKey': key
            }
            r = requests.get(url, headers=headers)
            directory = f'./{formats}'
            os.makedirs(directory, exist_ok=True)
            file_path = os.path.join(directory, f'{sid}.{formats}')
            with open(file_path, 'wb') as f:
                f.write(r.content)
            
#%% main function
def literature(keywords, Lim_nr=5, Lim_lvl=0):
    # set up logging file
    logging.basicConfig(#stream=sys.stdout, 
                        level=logging.INFO, 
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
                        filename='retrieve_papers.log',
                        filemode='a'
                        )
    
    logging.info('To start, reading needed modules...')
    sp, rp, pp = search_pub, retrieve_pub, process_pub
    
    # search by key words or author names
    logging.info('Now searching the first paper with given keywords/authors...')
    try:
        df_publication, message = sp.search_by_keyword(keywords, Lim_nr)
    except Exception as e:
        logging.error(f'Error in searching by keyword: {e}')
        raise
    # df_author, df_publication = sp.search_by_name('DRAGAN', 'SAVIC', 'KWR', search_publication=True, pub_limit=5)
    
    # retrieve abstracts and full texts
    logging.info('Based on found paper(s), retrieving abstracts and full texts now...')
    df_publication = rp.retieve_abstracts(df_publication)
    # df_publication = rp.retrieve_fulltext(df_publication)
    # df_publication = rp.retrieve_keywords_references_chemicals(df_publication)
     
    # define the number of connection layers, starting from 0, do not go for a large: suggestion: 0/1/2
    df_publication['level'] = 0
    logging.info('Looking for more literature based on the reference list if lim_lvl >= 1, taking 2-120 minutes...')
    for i in range(Lim_lvl):
        print(f'being processed at reference level {i+1}')
        if i == 0:
            df_temp = df_publication.copy()
        else:
            # df_temp = df_ref       
            pass
        df_ref = pp.get_pub_from_ref(pp, df_temp)
        df_ref['level'] = i+1
        df_publication = df_publication.append(df_ref, ignore_index=True)
        
    return df_publication


#%% testing 
if __name__ == '__main__':
    """`
    @Elie: This script retrieves the Scopus API key from environment variables.
    """
    load_dotenv()
    key = os.getenv("scopus_api_key_tian") # change to your environment variable name
    if not key:
        raise ValueError("SCOPUS_API_KEY is not set in the environment variables.") 
    else:
        print("SCOPUS_API_KEY is set.")
        scopus = Scopus(key)

    keywords = ['climate']
    print(keywords)

    # just modify the keywords to search for groundwater + WQ   
    df = literature(keywords, Lim_nr=10, Lim_lvl=0)
    df.to_csv('test.csv', index=False)
