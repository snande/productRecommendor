import streamlit as st
from bs4 import BeautifulSoup
import requests
import pandas as pd
import numpy as np
from PIL import Image
from io import BytesIO
import time
from azure.storage.blob import BlobServiceClient
import logging
from io import BytesIO


logger = logging.getLogger('azure.core.pipeline.policies.http_logging_policy').setLevel(logging.WARNING)

connection_string = st.secrets["database_connection"]["connection_string"]
container_name = st.secrets["database_connection"]["container_name"]
masterSearchFileName = st.secrets["database_connection"]["masterSearchFileName"]
blob_service_client = BlobServiceClient.from_connection_string(connection_string)
container_client = blob_service_client.get_container_client(container=container_name)

downlodData = container_client.download_blob(masterSearchFileName).readall()
keydict = pd.read_json(BytesIO(downlodData), dtype={"Search":str, "Time":np.float32, "Key":str})

# search_for_orig = "trimmer"
search_for_orig = st.text_input(label='Search for:', value='')
search_for_orig = search_for_orig.strip().lower()

num_prod_search = 160
displayBox = None

def display_data(df):
    df_rat = df.sort_values(['Scaled Rating', 'Raters', 'Reviewers', 'composite', 'VFM'], axis=0, ascending=False).head(5)
    df_vfm = df.sort_values(['VFM', 'Raters', 'Reviewers', 'composite', 'Scaled Rating'], axis=0, ascending=False).head(5)
    df_com = df.sort_values(['composite', 'Raters', 'Reviewers', 'Scaled Rating', 'VFM'], axis=0, ascending=False).head(5)

    st.subheader("Best Products by Rating")
    for i in range(len(df_rat)):
        col1, col2 = st.columns([4, 1])
        col1.write(f"""{i+1}. [{df_rat.iloc[i, 1]}]({df_rat.iloc[i, 2]})  
                    **Platform** : {df_rat.iloc[i, 0]}  
                    **Price** : {df_rat.iloc[i, 3]} Rs.  
                    **Rating** : {round(df_rat.iloc[i, 8], 2)}  
                    **Value for Money** : {round(df_rat.iloc[i, 9], 2)}  
                    **Composite Rating** : {round(df_rat.iloc[i, 10], 2)}  
        

                """)
        r = requests.get(df_rat.iloc[i, 7])
        img = Image.open(BytesIO(r.content))
        width, height = img.size
        resize_len = width if width >= height else height
        img = img.resize((resize_len, resize_len))
        col2.image(img)
        

    st.subheader("Best Products by Value for Money")
    for i in range(len(df_vfm)):
        col1, col2 = st.columns([4, 1])
        col1.write(f"""{i+1}. [{df_vfm.iloc[i, 1]}]({df_vfm.iloc[i, 2]})  
                    **Platform** : {df_vfm.iloc[i, 0]}                      
                    **Price** : {df_vfm.iloc[i, 3]} Rs.  
                    **Rating** : {round(df_vfm.iloc[i, 8], 2)}  
                    **Value for Money** : {round(df_vfm.iloc[i, 9], 2)}  
                    **Composite Rating** : {round(df_vfm.iloc[i, 10], 2)}  
        

                """)
        r = requests.get(df_vfm.iloc[i, 7])
        img = Image.open(BytesIO(r.content))
        width, height = img.size
        resize_len = width if width >= height else height
        img = img.resize((resize_len, resize_len))
        col2.image(img)

    st.subheader("Best Products by Composite Rating")
    for i in range(len(df_com)):
        col1, col2 = st.columns([4, 1])
        col1.write(f"""{i+1}. [{df_com.iloc[i, 1]}]({df_com.iloc[i, 2]})  
                    **Platform** : {df_com.iloc[i, 0]}  
                    **Price** : {df_com.iloc[i, 3]} Rs.  
                    **Rating** : {round(df_com.iloc[i, 8], 2)}  
                    **Value for Money** : {round(df_com.iloc[i, 9], 2)}  
                    **Composite Rating** : {round(df_com.iloc[i, 10], 2)}  
        

                """)
        r = requests.get(df_com.iloc[i, 7])
        img = Image.open(BytesIO(r.content))
        width, height = img.size
        resize_len = width if width >= height else height
        img = img.resize((resize_len, resize_len))
        col2.image(img)

    st.subheader("Entire Data Extract")
    st.dataframe(df[['platform', 'Desc', 'Link', 'Price', 'Rating', 'Raters', 'Reviewers', 'Scaled Rating', 'VFM', 'composite']])



if search_for_orig != '':

    key = (keydict.loc[keydict["Search"]==search_for_orig, "Key"].iloc[0] 
            if search_for_orig in keydict["Search"].values else "None")


    if ((key != "None")):

        epochtime, num_prod1, num_prod2, page1, page2 = key.split("_")
        restime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(int(epochtime)))
        currtime = time.time()
        numdays = int((currtime - int(epochtime))/(24*60*60))
        displayBox = st.empty()
        with displayBox.container():
            col1, col2 = st.columns([4, 1])
            col1.write(f"Showing result as of {restime} ({numdays} days ago)")
            refresh = col2.button("Refresh")

            if refresh == False:
                resultFileName = "projects/productRecommendor/data/result/"+key+".json"
                downlodData = container_client.download_blob(resultFileName).readall()
                df = (pd.read_json(BytesIO(downlodData), 
                                    dtype={"platform":str,"Desc":str,"Link":str,"Price":int,"Rating":float,
                                            "Raters":int,"Reviewers":int,"img_url":str,
                                            "Scaled Rating":float,"VFM":float,"composite":float}))

                st.write(f"Amazon : searched for {num_prod1} products in {page1} pages")
                st.progress(100)
                st.write(f"Flipkart : searched for {num_prod2} products in {page2} pages")
                st.progress(100)
                display_data(df)

    if ((key == "None") or (refresh==True)):

        platform = "Amazon"
        search_for = search_for_orig.replace(' ', '+')
        base_link = ("https://www.amazon.in/s?k=" + search_for + 
                    "&rh=p_72%3A1318476031")

        df_list = []
        progress = 0.0
        page1 = 0
        num_prod1 = 0
        restime = time.time()
        formatime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(restime))
        if refresh==True:
            displayBox.empty()
        st.write(f"Showing result as of {formatime} (now)")
        amz_write = st.empty()
        amz_write.write("Amazon : ")
        my_bar1 = st.progress(int(progress))
        while progress < 100:
            page1 = page1 + 1
            if page1 == 10:
                my_bar1.progress(100)
                break
            link = base_link+"&page="+str(page1)
            headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Safari/605.1.15", "Accept-Encoding":"gzip, deflate", "Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8", "DNT":"1","Connection":"close", "Upgrade-Insecure-Requests":"1"} 
            html_text = requests.get(link, headers=headers).text
            soup = BeautifulSoup(html_text, "html.parser")
            # print("\n\nPage :", page)
            # print("link:")
            # print(link, "\n\n")

            prods = soup.find_all("div", class_="s-card-container s-overflow-hidden aok-relative puis-expand-height puis-include-content-margin puis s-latency-cf-section s-card-border")
            if len(prods) != 0:
                for prod in prods:
                    desc_box1 = prod.find("h5", class_="s-line-clamp-1")
                    desc_box2 = prod.find("span", class_="a-size-base-plus a-color-base a-text-normal")
                    descrs = ""
                    if (desc_box1 == None) and (desc_box2 == None):
                        continue
                    if desc_box1 != None:
                        descrs = desc_box1.text + " | "
                    if desc_box2 != None:
                        descrs = descrs + desc_box2.text
                    prodLink = "https://www.amazon.in" + (prod.find("a", class_="a-link-normal s-underline-text s-underline-link-text s-link-style a-text-normal")['href'].split("/ref=")[0])
                    pricebox = prod.find("span", class_="a-price-whole")
                    if pricebox == None:
                        continue
                    price = int(round(float(pricebox.text.replace(',', '')), 0))
                    ratebox = prod.find("span", class_="a-icon-alt")
                    if ratebox == None:
                        continue
                    rating = float(ratebox.text.split()[0])
                    raters = int(prod.find("span", class_="a-size-base s-underline-text").text.replace(',', '').replace('(', '').replace(')', ''))
                    if raters < 30:
                        continue
                    img_url = prod.find("img", class_="s-image")['src']
                    df_list.append([platform, descrs, prodLink, price, rating, raters, np.nan, img_url])
                    num_prod1 = num_prod1 + 1
                    amz_write.write(f"Amazon : searched for {num_prod1} products in {page1} pages")
                    progress = progress + (100/(num_prod_search))
                    my_bar1.progress(int(progress) if int(progress)<100 else 100)
                    continue

            else:
                prods = soup.find_all("div", class_="s-card-container s-overflow-hidden aok-relative puis-include-content-margin puis s-latency-cf-section s-card-border")    
                for prod in prods:
                    descrs = prod.find("span", class_="a-size-medium a-color-base a-text-normal").text
                    prodLink = "https://www.amazon.in" + prod.find("a", class_="a-link-normal s-underline-text s-underline-link-text s-link-style a-text-normal")['href'].split("/ref=")[0]
                    pricebox = prod.find("span", class_="a-price-whole")
                    if pricebox == None:
                        continue
                    price = int(round(float(pricebox.text.replace(',', '')), 0))
                    ratebox = prod.find("span", class_="a-icon-alt")
                    if ratebox == None:
                        continue
                    rating = float(ratebox.text.split()[0])
                    raters = int(prod.find("span", class_="a-size-base s-underline-text").text.replace(',', '').replace('(', '').replace(')', ''))
                    if raters < 30:
                        continue
                    img_url = prod.find("img", class_="s-image")['src']
                    df_list.append([platform, descrs, prodLink, price, rating, raters, np.nan, img_url])
                    num_prod1 = num_prod1 + 1
                    amz_write.write(f"Amazon : searched for {num_prod1} products in {page1} pages")
                    progress = progress + (100/(num_prod_search))
                    my_bar1.progress(int(progress) if int(progress)<100 else 100)
                    continue

        
        platform = "Flipkart"
        search_for = search_for_orig.replace(' ', '%20')
        base_link = ("https://www.flipkart.com/search?q=" + search_for + 
                    "&sort=popularity&p%5B%5D=facets.fulfilled_by%255B%255D%3DPlus%2B%2528FAssured%2529" +
                    "&p%5B%5D=facets.rating%255B%255D%3D4%25E2%2598%2585%2B%2526%2Babove" +
                    "&p%5B%5D=facets.availability%255B%255D%3DExclude%2BOut%2Bof%2BStock")

        style = ''
        progress = 0.0
        page2 = 0
        num_prod2 = 0
        flp_write = st.empty()
        flp_write.write("Flipkart : ")
        my_bar2 = st.progress(int(progress))
        while progress < 100:
            page2 = page2 + 1
            if page2 == 10:
                my_bar2.progress(100)
                break
            link = base_link+"&page="+str(page2)
            headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Safari/605.1.15", "Accept-Encoding":"gzip, deflate", "Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8", "DNT":"1","Connection":"close", "Upgrade-Insecure-Requests":"1"} 
            html_text = requests.get(link, headers=headers).text
            soup = BeautifulSoup(html_text, "html.parser")

            for row in soup.find_all('div', class_='_13oc-S'):
                if style == '':
                    style = row.find('div')['style']
                
                if style == 'width:100%':
                    descrs = row.find('div', class_='_4rR01T').text
                    prodLink = 'https://www.flipkart.com' + (row.find('a', class_='_1fQZEK')['href'].split('?')[0])
                    price = int(row.find('div', class_='_30jeq3 _1_WHN1').text[1:].replace(',', ''))
                    ratebox = row.find('div', class_='_3LWZlK')
                    if ratebox == None:
                        continue
                    rating = float(ratebox.text)
                    rateData = row.find('span', class_="_2_R_DZ").text
                    raters = int(rateData.split()[0].replace(',',''))
                    if raters < 30:
                        continue
                    reviewers = int(rateData.split()[3].replace(',',''))
                    img_url = row.find('img', class_="_396cs4")['src']
                    df_list.append([platform, descrs, prodLink, price, rating, raters, reviewers, img_url])
                    num_prod2 = num_prod2 + 1
                    flp_write.write(f"Flipkart : searched for {num_prod2} products in {page2} pages")
                    progress = progress + (100/(num_prod_search))
                    my_bar2.progress(int(progress) if int(progress)<100 else 100)
                    continue
                    
                elif style == 'width:25%':
                    prods = row.find_all('div', class_='_4ddWXP')
                    if len(prods) > 0:
                        for prod in prods:
                            header = prod.find('a', class_='s1Q9rs')
                            descrs = header['title']
                            prodLink = 'https://www.flipkart.com' + (header['href'].split('?')[0])
                            pricebox = prod.find('div', class_='_30jeq3')
                            if pricebox == None:
                                continue
                            price = int(pricebox.text[1:].replace(',', ''))
                            ratebox = prod.find('div', class_="_3LWZlK")
                            if ratebox == None:
                                continue
                            rating = float(ratebox.text)
                            raters = int(prod.find('span', class_="_2_R_DZ").text[1:-1].replace(',',''))
                            if raters < 30:
                                continue
                            img_url = prod.find('img', class_="_396cs4")['src']
                            df_list.append([platform, descrs, prodLink, price, rating, raters, np.nan, img_url])
                            num_prod2 = num_prod2 + 1
                            flp_write.write(f"Flipkart : searched for {num_prod2} products in {page2} pages")
                            progress = progress + (100/(num_prod_search))
                            my_bar2.progress(int(progress) if int(progress)<100 else 100)
                    else:
                        prods = row.find_all('div', class_='_1xHGtK _373qXS')
                        for prod in prods:
                            header = prod.find('a', class_='IRpwTa')
                            descrs = header['title']
                            prodLink = 'https://www.flipkart.com' + (header['href'].split('?')[0])
                            price = int(prod.find('div', class_='_30jeq3').text[1:].replace(',', ''))
                            # sleep(1.5)
                            prod_text = requests.get(prodLink).text
                            prod_soup = BeautifulSoup(prod_text, "html.parser")
                            ratebox = prod_soup.find('div', class_='_3LWZlK _3uSWvT')
                            if ratebox == None:
                                continue
                            rating = float(ratebox.text)
                            rateData = prod_soup.find('span', class_="_2_R_DZ")
                            if rateData == None:
                                continue
                            raters = int(rateData.text.split()[0].replace(',',''))
                            if raters < 30:
                                continue
                            reviewers = int(rateData.text.split()[3].replace(',',''))
                            img_url = prod.find('img', class_="_2r_T1I")['src']
                            df_list.append([platform, descrs, prodLink, price, rating, raters, reviewers, img_url])
                            num_prod2 = num_prod2 + 1
                            flp_write.write(f"Flipkart : searched for {num_prod2} products in {page2} pages")
                            progress = progress + (100/(0.3*num_prod_search))
                            my_bar2.progress(int(progress) if int(progress)<100 else 100)
                    
                    
        df = pd.DataFrame(df_list, columns=['platform', 'Desc', 'Link', 'Price', 'Rating', 'Raters', 'Reviewers', 'img_url'])
        df = df.drop_duplicates(subset=['Price', 'Rating', 'Raters'])
        df = df[(df["Price"] > df["Price"].quantile(0.025)) & (df["Price"] < df["Price"].quantile(0.975))]
        df['Scaled Rating'] = df['Rating']*(1 - np.power(1.25, -1*np.sqrt(df['Raters'])))
        df['VFM'] = (df['Scaled Rating']/(df['Scaled Rating'].median()))*(np.sqrt(df['Price'].median()))/np.sqrt(df['Price'])
        df['composite'] = ((df['Scaled Rating']/(df['Scaled Rating'].median())) * (np.sqrt(df['VFM'])/(np.sqrt(df['VFM'].median()))))

        display_data(df)

        key = "_".join([str(restime).split(".")[0], str(num_prod1), str(num_prod2), str(page1), str(page2)])
        keydict.loc[len(keydict), ["Search", "Time", "Key"]] = [search_for_orig, restime, key]
        keydict = keydict.sort_values(["Time", "Search"], ascending=False)
        
        resultFileName = "projects/productRecommendor/data/result/"+key+".json"
        blob_client = blob_service_client.get_blob_client(container=container_name, blob=resultFileName)
        _ = blob_client.upload_blob(df.to_json(), overwrite=True)
        
        blob_client = blob_service_client.get_blob_client(container=container_name, blob=masterSearchFileName)
        _ = blob_client.upload_blob(keydict.to_json(), overwrite=True)
        