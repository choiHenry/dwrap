def download(url, file_name):
    from requests import get
    with open(file_name, "wb") as file:   # open in binary mode
        response = get(url)               # get request
        file.write(response.content)      # write to file

class DWrap:

    def __init__(self):
        self._groupList = []
        self._apiKey = ""
        self._corpCode = ""

    @property
    def groupList(self):
        print('getting groupList attr')
        return self._groupList

    @groupList.setter
    def groupList(self, groupList):
        print('setting groupList attr')
        self._groupList = groupList

    def addGroupDict(self, groupDict):
        self._groupList.append(groupDict)

    @property
    def apiKey(self):
        print('getting apiKey attr')
        return self._apiKey

    @apiKey.setter
    def apiKey(self, apiKey):
        print('setting apiKey attr')
        self._apiKey = apiKey

    @property
    def corpCode(self):
        print('getting corpCode attr')
        return self._corpCode

    @corpCode.setter
    def corpCode(self, path):
        self._corpCode = path

    def getCorpcodeFile(self, fileName):

        import zipfile

        url = "https://opendart.fss.or.kr/api/corpCode.xml?crtfc_key=" + self.apiKey
        download(url, fileName)

        with zipfile.ZipFile(fileName, 'r') as zipObj:
            fileList = zipObj.namelist()
            target = fileList[0]
            print(f'Downloaded {fileName}, extracting {target}...')

        with zipfile.ZipFile(fileName, 'r') as zipRef:
            zipRef.extractall(".")

        if (target != None):
            self.corpCode = target

        return target

    def findCorpCode(self, firmname):

        import xml.etree.ElementTree as ET
        from os import path

        if (self.corpCode != ''):
            target = self.corpCode

        elif path.exists('CORPCODE.xml'):
            target = 'CORPCODE.xml'
        else:
            print('There exists no corp_code file. Downloading the file in the current directory...')
            target = self.getCorpcodeFile("CORPCODE.zip")
        xml = ET.parse(target)
        root = xml.getroot()

        lists = root.findall('list')

        codeList = []
        for list in lists:
            if (list.find('corp_name').text == firmname):
                codeList.append(list.find('corp_code').text)
        return codeList

    def findRceptNum(self, firmname, year):

        from requests import get

        codeList = self.findCorpCode(firmname)
        crtfc_key = self.apiKey
        pblntf_ty = "J"
        pblntf_detail_ty = "J004"

        # set begin date and end date regarding each firm's report submit date
        if (((firmname == '롯데지주') & (year == '2020')) | ((firmname == '티케이케미칼') & (year == '2019'))):
            bgn_de = year + "0901"
            end_de = year + "0930"
        elif ((firmname == '농협경제지주') | ((firmname == '금호산업') & (year == '2019')) | (
                (firmname == '티케이케미칼') & (year == '2020')) |
              ((firmname == '넷마블') & (year == '2019')) | ((firmname == '태광산업') & (year == '2019'))):
            bgn_de = year + "0701"
            end_de = year + "0831"
        elif (((firmname == 'CJ') & (year == '2020')) | ((firmname == '아이엠엠인베스트먼트') & (year == '2020'))):
            bgn_de = year + "1001"
            end_de = year + "1031"
        elif ((firmname == '대한항공') & (year == '2019')):
            bgn_de = '20200401'
            end_de = '20200430'
        elif (firmname == '이랜드월드'):
            bgn_de = year + '0801'
            end_de = year + '0930'
        elif ((firmname == '키움증권') & (year == '2019')):
            bgn_de = year + '1101'
            end_de = year + '1130'
        else:
            bgn_de = year + "0515"
            end_de = year + "0731"
        page_count = "50"

        # find the firm that submitted reports to FTC whose name is <firmname>
        i = 0
        json = {}
        while (i < len(codeList)):
            corp_code = codeList[i]
            url = "https://opendart.fss.or.kr/api/list.json?corp_code=" + corp_code + "&crtfc_key=" + crtfc_key + "&bgn_de=" + \
                  bgn_de + "&end_de=" + end_de + "&last_reprt_at=Y" + "&pblntf_ty=" + pblntf_ty + "&pblntf_detail_ty=" + \
                  pblntf_detail_ty + "&page_count=" + page_count
            response = get(url)
            json = response.json()
            if 'list' in json:
                break
            i += 1

        # find all the reports whose names contain the string '대규모기업집단현황공시[연1회공시및1/4분기용' and save as a list
        # and return rcept_no of the last report in the list
        outputDict = [x for x in json['list'] if ('대규모기업집단현황공시[연1회공시및1/4분기용' in x['report_nm'])]
        rcept_no = outputDict[0]["rcept_no"]

        return rcept_no

    def getSharesURL(self, firmname, year):
        # this function uses selenium
        from selenium import webdriver

        # get recept_no of the firm and use it to go to the first page of the report
        rcept_no = self.findRceptNum(firmname, year)
        driver = webdriver.Chrome('./chromedriver')
        driver.implicitly_wait(3)
        url = "http://dart.fss.or.kr/dsaf001/main.do?rcpNo=" + rcept_no
        driver.get(url)

        # In the navigation menu click the link that contains the string '소유지분'
        driver.find_element_by_partial_link_text('소유지분').click()

        # get the url of the '소유지분현황' page and return it
        sharesURL = driver.find_element_by_id('ifrm').get_attribute('src')

        return sharesURL

    def getRawCBData(self, firmname, year):

        import numpy as np
        import pandas as pd
        import os

        # parse raw html table with designated headers

        url = self.getSharesURL(firmname, year)
        tables = pd.read_html(url, header=[0, 1])
        df = tables[1]  # 소유지분현황 page contains empty table so skip this table

        # save the raw data in the raw folder
        if not os.path.exists('raw'):
            os.makedirs('raw')
        df.to_csv(f'./raw/{firmname}_{year}_raw.csv')

        # reset column names
        header = []
        if (len(df.columns) == 12):
            header = ['소속회사명1', '소속회사명2', '동일인과의 관계1', '동일인과의 관계2', '동일인과의 관계3', '성명',
                      '보통주 주식수', '보통주 지분율', '우선주 주식수', '우선주 지분율', '합계 주식수', '합계 지분율']
        elif (len(df.columns) == 11):
            header = ['소속회사명1', '소속회사명2', '동일인과의 관계1', '동일인과의 관계2', '성명',
                      '보통주 주식수', '보통주 지분율', '우선주 주식수', '우선주 지분율', '합계 주식수', '합계 지분율']
        df.columns = header

        # 동일한 행이 반복되는 경우 제외
        df.drop_duplicates()

        # '성명' 변수에 '해당사항 없음'이 기재되어 있는 경우 제외
        dropList = list(df[df['성명'].str.contains('해당사항\s+없음', na=False)].index)
        df.drop(dropList, axis=0, inplace=True)

        # (주)나 ㈜를 데이터셋에서 제거
        df.replace('\(주\)', '', regex=True, inplace=True)
        df.replace('㈜', '', regex=True, inplace=True)

        # 합계 주식수에 숫자가 아닌 다른 문자가 입력되어 있는 경우 제거
        # 신세계(신세계)2019의 에스에스지닷컴은 0.8주의 자기주식을 보유함.
        if ((firmname == '신세계') & (year == '2019')):
            df['합계 주식수'].replace('[^0-9.]*', '', regex=True, inplace=True)
        else:
            df['합계 주식수'].replace('[^0-9]*', '', regex=True, inplace=True)


        # 동일인과의 관계3(또는 2)에 ① - ⑨이 포함되어 있으면(+좌우로 공백이 있는 경우 포함) 제거
        if (len(df.columns) == 12):
            df['동일인과의 관계3'].replace(' *[\u2460-\u2468] *', '', regex=True, inplace=True)
        else:
            df['동일인과의 관계2'].replace(' *[\u2460-\u2468] *', '', regex=True, inplace=True)

        # 동원(동원엔터프라이즈)2019 data cleansing
        # 부산신항다목적터미널의 경우 기타에 기타총계 50%가 추가로 입력됨
        if ((firmname == '동원엔터프라이즈') & (year == '2019')):
            df.drop([107], axis=0, inplace=True)

        # 애경(AK홀딩스)2019 data cleansing
        if ((firmname == 'AK홀딩스') & (year == '2019')):
            # 에이케이스앤에디 합계 주식수와 합계 지분율이 잘못 입력되어 있음: 보통주 자료를 이용하여 채우기
            df.loc[[354, 355, 356, 357], ['합계 주식수', '합계 지분율']] = df.loc[
                [354, 355, 356, 357], ['보통주 주식수', '보통주 지분율']]

            # 퍼시픽제3호전문사모부동산투자유한회사 합계 주식수가 미입력: 보통주 주식수 자료를 이용하여 합계 주식수 채우기
            df.loc[[330], '보통주 주식수'] = int(df.loc[324, '보통주 주식수']) + int(df.loc[329, '보통주 주식수'])
            df.loc[[324, 327, 329, 330], '합계 주식수'] = df.loc[[324, 327, 329, 330], '보통주 주식수']

            # 평택역사 기타주주에 성명이 '합계'인 행이 있음: 필요한 정보가 아니므로 제외
            drop_list2 = list(df[df['성명'].str.contains('합계', na=False)].index)
            df.drop(drop_list2, axis=0, inplace=True)

        # 애경(AK홀딩스)2020 data cleansing
        if ((firmname == 'AK홀딩스') & (year == '2020')):

            # 퍼시픽제3호전문사모부동산투자유한회사 합계 주식수가 미입력: 보통주 주식수 자료를 이용하여 합계 주식수 채우기
            df.loc[[309], '보통주 주식수'] = int(df.loc[303, '보통주 주식수']) + int(df.loc[308, '보통주 주식수'])
            df.loc[[303, 306, 308, 309], '합계 주식수'] = df.loc[[303, 306, 308, 309], '보통주 주식수']

            # 평택역사 기타주주에 성명이 '합계'인 행이 있음: 필요한 정보가 아니므로 제외
            drop_list2 = list(df[df['성명'].str.contains('합계', na=False)].index)
            df.drop(drop_list2, axis=0, inplace=True)



        # 한국타이어(한국앤컴퍼니)2019, 2020 data cleansing
        # 두원홀딩스 자료가 중복 입력됨: 제거
        if ((firmname == '한국앤컴퍼니') & (year == '2020')):
            df.drop([116, 117, 118, 119], axis=0, inplace=True)

        # 신세계(신세계)2019, data cleansing
        if ((firmname == '신세계') & (year == '2019')):

            # 신세계 친족 합계 합계 주식수에 동일인 합계 주식수가 포함됨: 제거
            for firm in ('신세계',):
                id = df[(df['소속회사명2'] == firm) & (df['동일인과의 관계3'] == '친족 합계')].index
                id2 = df[(df['소속회사명2'] == firm) & (df['동일인과의 관계3'] == '동일인')].index
                val = int(df.loc[id, '합계 주식수'])
                val2 = int(df.loc[id2, '합계 주식수'])
                df.loc[id, '합계 주식수'] = val - val2
            # 신세계디에프글로벌 기타 동일인관련자 항목에 합계 주식수가 중복되어 입력됨: 제거
            df[(df['소속회사명2'] == '신세계디에프글로벌') & (df['동일인과의 관계3'] == '기타 동일인관련자')]['합계 주식수'] = '0'

        # 한국앤컴퍼니 친족 합계에 동일인이 포함됨: 제외
        if (((firmname == '한국앤컴퍼니') & (year == '2020')) | ((firmname == '한국앤컴퍼니') & (year == '2019'))):
            for firm in ('한국테크놀로지그룹', '한국타이어앤테크놀로지', '신양월드레저'):
                id = df[(df['소속회사명2'] == firm) & (df['동일인과의 관계3'] == '친족 합계')].index
                id2 = df[(df['소속회사명2'] == firm) & (df['동일인과의 관계3'] == '동일인')].index
                val = int(df.loc[id, '합계 주식수'])
                val2 = int(df.loc[id2, '합계 주식수'])
                df.loc[id, '합계 주식수'] = val - val2

        # 태광(태광산업)2019, 2020 data cleansing
        if (((firmname == '태광산업') & (year == '2020'))):
            # 태광산업 기타 합계 주식수에 총계 합계 주식수가 입력되어 있음: 기타 합계 주식수를 계산하여 변경
            df.loc[22, '합계 주식수'] = int(df.loc[23, '합계 주식수']) - int(df.loc[19, '합계 주식수'])
            df.drop([136], axis=0, inplace=True)

            # 티시스 친족 합계에 동일인이 포함됨: 제외
            id = df[(df['소속회사명2'] == '티시스') & (df['동일인과의 관계3'] == '친족 합계')].index
            id2 = df[(df['소속회사명2'] == '티시스') & (df['동일인과의 관계3'] == '동일인')].index
            val = int(df.loc[id, '합계 주식수'])
            val2 = int(df.loc[id2, '합계 주식수'])
            df.loc[id, '합계 주식수'] = val - val2

        if (((firmname == '키움증권') & (year == '2019'))):
            df.loc[166, '합계 주식수'] = '50000000'


        if (((firmname == '태광산업') & (year == '2019'))):
            id = list(df[(df['소속회사명2'] == '한국케이블텔레콤') & (df['동일인과의 관계3'] == '기타')].index)[0]
            print(id)
            id2 = list(df[(df['소속회사명2'] == '한국케이블텔레콤') & (df['동일인과의 관계3'] == '동일인측이 아닌 최다주주')].index)[0]
            val = int(df.loc[id, '합계 주식수'])
            val2 = int(df.loc[id2, '합계 주식수'])
            df.loc[id, '합계 주식수'] = val - val2

        # 중흥건설(중흥건설)2019, 2020 data cleansing
        # shift data by 1 period
        if ((firmname == '중흥건설') & (year == '2020')):
            df.iloc[428, 4:] = df.iloc[428, 4:].shift(1)
            df.loc[428, '동일인과의 관계2'] = '계열회사'
            df.loc[428, '동일인과의 관계3'] = '계열회사'
        elif ((firmname == '중흥건설') & (year == '2019')):
            df.iloc[500, 4:] = df.iloc[500, 4:].shift(1)
            df.loc[500, '동일인과의 관계2'] = '계열회사'
            df.loc[500, '동일인과의 관계3'] = '계열회사'

        # 삼양(삼양홀딩스)2020 data cleansing
        if ((firmname == '삼양홀딩스') & (year == '2020')):
            df[(df['소속회사명2'] == '삼양에프앤비') & (df['동일인과의 관계3'] == '기타')]['합계 주식수'] = '0'

        # 태영(태영건설)2019 data cleansing
        if ((firmname == '태영건설') & (year == '2019')):
            # 디엠씨미디어 기타 합계 주식수 중복 입력: 제거
            df[(df['소속회사명2'] == '디엠씨미디어') & (df['동일인과의 관계3'] == '기타')]['합계 주식수'] = '0'

            # 유니시티 합계 주식수, 지분율 미입력
            id = list(df[(df['소속회사명2'] == '유니시티') & (df['동일인과의 관계3'] == '기타')].index)[0]
            df.loc[[id], ['합계 주식수', '합계 지분율']] = df.loc[[id], ['보통주 식수', '보통주 지분율']]

        if (((firmname == '엔엑스씨') & (year == '2019'))):



            # 엔엑스씨 친족 합계에 동일인이 포함됨: 제외
            id = df[(df['소속회사명2'] == '엔엑스씨') & (df['동일인과의 관계3'] == '친족 합계')].index
            id2 = df[(df['소속회사명2'] == '엔엑스씨') & (df['동일인과의 관계3'] == '동일인')].index
            val = int(df.loc[id, '합계 주식수'])
            val2 = int(df.loc[id2, '합계 주식수'])
            df.loc[id, '합계 주식수'] = val - val2


        if ((df['합계 주식수'].dtype == 'float64') | (df['합계 주식수'].dtype == 'int64')):
            pass
        else:
            # fill missing value and with zero or np.nan and convert the dtype of '합계 주식수' column to int
            df.fillna('0')
            df.replace('^\s*$', np.nan, regex=True, inplace=True)
            df['합계 주식수'] = df['합계 주식수'].astype(float)




        # save the data in the after_cleansing folder
        if not os.path.exists('after_cleansing'):
            os.makedirs('after_cleansing')
        df.to_csv(f'./after_cleansing/{firmname}_{year}_after_cleansing.csv')

        return df

    def parseCBTable(self, df, firmname, year):

        import numpy as np
        import pandas as pd
        import os

        # extract, make, merge, and calculate
        sum = df[(df['동일인과의 관계1'].str.contains('총\s*계', regex=True) | df['동일인과의 관계1'].str.contains(
            '합계'))]  # extract rows whose value for '동일인과의 관계1' is '총계'
        sum_reduced = pd.DataFrame(
            {'소속회사명2': sum['소속회사명2'], 'divisor': sum['합계 주식수']})  # make a new df with only '소속회사명2' and '합계 주식수'
        df = pd.merge(df, sum_reduced)  # merge with the original dataset
        df['shares'] = df['합계 주식수'] / df['divisor']  # calculate 'shares' column

        # save the data in the after_sum folder
        if not os.path.exists('after_sum'):
            os.makedirs('after_sum')
        df.to_csv(f'./after_sum/{firmname}_{year}_after_sum.csv')

        # make 'type' and 'type2' variable
        # categorize '동일인과의 관계3' column if it exists.
        if ('동일인과의 관계3' in df):
            df['type'] = df['동일인과의 관계3']
            df['type2'] = df['동일인과의 관계3']
            # df.to_csv('checkout.csv')
            # print(df.index[df['type'] ].tolist())
            df['type'] = df['type'].apply(DWrap.rel3_categorize)
            df['type2'] = df['type2'].apply(DWrap.rel3_categorize2)

        # Else cat '동일인과의 관계2' column.
        elif ('동일인과의 관계2' in df):
            df['type'] = df['동일인과의 관계2']
            df['type2'] = df['동일인과의 관계2']
            df['type'] = df['type'].apply(DWrap.rel2_categorize)
            df['type2'] = df['type2'].apply(DWrap.rel2_categorize2)

        # save the data in the after_cat folder
        if not os.path.exists('after_cat'):
            os.makedirs('after_cat')
        df.to_csv(f'./after_cat/{firmname}_{year}_after_cat.csv')

        # calc values 'own', 'own2', and 'ownername' variable
        own = df.groupby(['소속회사명2', 'type'])['shares'].sum().rename('own').reset_index()
        df = pd.merge(df, own, how='left')

        own2 = df.groupby(['소속회사명2', 'type2'])['shares'].sum().rename('own2').reset_index()
        df = pd.merge(df, own2, how='left')

        for i in df.index:
            val = df.loc[i, 'type']
            if (val == '1'):
                df.loc[i, 'own'] = df.loc[i, 'shares']
            elif (val == '-1'):
                df.loc[i, 'own'] = df.loc[i, 'shares']
            elif (val == '50'):
                df.loc[i, 'own'] = np.nan
            elif (val == '-1'):
                df.loc[i, 'own'] = df.loc[i, 'shares']
            elif (val == '-2'):
                df.loc[i, 'own'] = df.loc[i, 'shares']

        for i in df.index:
            val = df.loc[i, 'type2']
            if (val == '1'):
                df.loc[i, 'own2'] = df.loc[i, 'shares']
            elif (val == '-1'):
                df.loc[i, 'own2'] = df.loc[i, 'shares']
            elif (val == '50'):
                df.loc[i, 'own2'] = np.nan
            elif (val == '-1'):
                df.loc[i, 'own2'] = df.loc[i, 'shares']
            elif (val == '-2'):
                df.loc[i, 'own2'] = df.loc[i, 'shares']

        df['ownername'] = ''

        for i in df.index:
            val = df.loc[i, 'type2']
            if (val == '1'):
                df.loc[i, 'ownername'] = df.loc[i, '성명']

        # save the data in the after_ownername folder
        if not os.path.exists('after_ownername'):
            os.makedirs('after_ownername')
        df.to_csv(f'./after_ownername/{firmname}_{year}_after_ownername.csv')

        # discard unwanted rows
        discard = []
        appeared0 = False
        appeared99 = False
        for i in df.index:
            # print(i)
            if (i == 0):
                appeared0 = False
                appeared99 = False
            elif ((i > 0) & (df.loc[i, '소속회사명2'] != df.loc[i - 1, '소속회사명2'])):
                appeared0 = False
                appeared99 = False
            val = df.loc[i, 'type2']
            if (val == '0'):
                if appeared0:
                    discard.append(i)
                else:
                    appeared0 = True
            elif (val == '50'):
                discard.append(i)
            elif (val == '99'):
                if appeared99:
                    discard.append(i)
                else:
                    appeared99 = True

        df.drop(discard, axis=0, inplace=True)

        # discard unwated columns and change the column names
        df = df[['소속회사명2', 'own', 'own2', 'type2', 'ownername']]
        df.columns = ['firmname', 'own', 'own2', 'type', 'ownername']

        # save the data in the after_discard folder
        if not os.path.exists('after_discard'):
            os.makedirs('after_discard')
        df.to_csv(f'./after_discard/{firmname}_{year}_after_discard.csv')

        return df

    def rel3_categorize(rel3):
        # import math
        import pandas as pd
        if (pd.isnull(rel3)):
            print("missing null value occured making type variable")
            return '-2'
        elif ((rel3 == '동일인') | (rel3 == '친족 합계') | (rel3 == '친족합계') | ('친족 합계' in rel3) | ('친족 합계' in rel3)):
            return '0'
        elif ('계열회사' in rel3):
            return '1'
        elif ('국내+해외' in rel3):
            return '1'
        elif ((rel3 == '기타') | (rel3 == '기 타') | (rel3 == '동일인측이 아닌 최다주주') | (rel3 == '최다주주') | (rel3 == '동일인측이아닌 최다주주') | (
                rel3 == '동일인측이 아닌최다주주')):
            return '99'
        elif (rel3 == '기타 동일인관련자'):
            return '-1'
        else:
            return '50'

    def rel3_categorize2(rel3):
        import pandas as pd
        if (pd.isnull(rel3)):
            print("missing null value occured making type2 variable")
            return '-2'
        elif ((rel3 == '동일인') | (rel3 == '친족 합계') | (rel3 == '친족합계') | ('친족 합계' in rel3) | ('친족 합계' in rel3) | (
                rel3 == '비영리법인') | (rel3 == '등기된 임원') | (rel3 == '등기된임원') | (rel3 == '자기주식') | (rel3 == '친족합계')):
            return '0'
        elif ('계열회사' in rel3):
            return '1'
        elif ('국내+해외' in rel3):
            return '1'
        elif ((rel3 == '기타') | (rel3 == '기 타') | (rel3 == '동일인측이 아닌 최다주주') | (rel3 == '최다주주') | (rel3 == '동일인측이아닌 최다주주') | (
                rel3 == '동일인측이 아닌최다주주')):
            return '99'
        elif (rel3 == '기타 동일인관련자'):
            return '-1'
        else:
            return '50'

    def rel2_categorize(rel2):
        # import math
        import pandas as pd
        if (pd.isnull(rel2)):
            print("missing null value occured making type variable")
            return '-2'
        elif ((rel2 == '동일인') | (rel2 == '친족 합계') | (rel2 == '친족합계')):
            return '0'
        elif ('계열회사' in rel2):
            return '1'
        elif ('국내+해외' in rel2):
            return '1'
        elif ((rel2 == '기타') | (rel2 == '기 타') | (rel2 == '동일인측이 아닌 최다주주') | (rel2 == '최다주주') | (rel2 == '동일인측이아닌 최다주주') | (
                rel2 == '동일인측이 아닌최다주주')):
            return '99'
        elif (rel2 == '기타 동일인관련자'):
            return '-1'
        else:
            return '50'

    def rel2_categorize2(rel2):
        import pandas as pd
        if (pd.isnull(rel2)):
            print("missing null value occured making type2 variable")
            return '-2'
        elif ((rel2 == '동일인') | (rel2 == '친족 합계') | (rel2 == '비영리법인') | (rel2 == '등기된 임원') | (rel2 == '등기된임원') | (
                rel2 == '자기주식') | (rel2 == '친족합계')):
            return '0'
        elif ('국내+해외' in rel2):
            return '1'
        elif ('계열회사' in rel2):
            return '1'
        elif ((rel2 == '기타') | (rel2 == '기 타') | (rel2 == '동일인측이 아닌 최다주주') | (rel2 == '최다주주') | (rel2 == '동일인측이아닌 최다주주') | (
                rel2 == '동일인측이 아닌최다주주')):
            return '99'
        elif (rel2 == '기타 동일인관련자'):
            return '-1'
        else:
            return '50'

    def getCBData(self, firmname: str, year: str):

        import os

        df = self.parseCBTable(self.getRawCBData(firmname, year), firmname, year)
        checkData = df.groupby(['firmname']).sum('own2')

        # save the confirm data in the confirm folder
        if not os.path.exists('confirm'):
            os.makedirs('confirm')
        checkData.to_csv(f'./confirm/{firmname}_{year}_confirm.csv')

        print(checkData)

        # save the output data in the out folder
        if not os.path.exists('out'):
            os.makedirs('out')
        df.to_csv(f'./out/{firmname}_{year}.csv')

    def getCBDataAll(self):
        for year in (2019, 2020):
            match = self.groupList[year-2019]
            for firmname in match['대표회사']:
                self.getCBData(firmname, str(year))

    def getCBDataof(self, year: int):

        match = self.groupList[year-2019]
        for firmname in match['대표회사']:
            self.getCBData(firmname, str(year))

    def getCBDataCont(self, start: str, year: int):
        match = self.groupList[year-2019]
        id = match['대표회사'].index(start)
        for firmname in match['대표회사'][id:]:
            self.getCBData(firmname, str(year))

    def saveGroupListData(self):

        if (len(self.groupList) > 0):
            import pandas as pd
            import os
            for i in range(len(self.groupList)):
                groupList = pd.DataFrame(self.groupList[i])
                if not os.path.exists('group_list'):
                    os.makedirs('group_list')
                groupList.to_csv(f'./group_list/{i+2019}_group_list.csv')

        else:
            print("No group list available. Set up group list data first.")



