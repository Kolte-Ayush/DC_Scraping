import scrapy
from scrapy.loader import ItemLoader
from zipfile import ZipFile
from ..items import CourtScrapItem, StatusScrapItem
from scrapy.http import FormRequest
from scrapy.utils.response import open_in_browser
import re
from .extract_txt_from_pdf import PdfReader
import PyPDF2
import os
import ocrmypdf
import json
import pdfplumber
import urllib


#
# class CaseSpider(scrapy.Spider):
#     name = "Case"
#     custom_settings = {
#         "ITEM_PIPELINES": {
#             'Court_Scrap.pipelines.CasePipeline': 300,
#
#         }
#     }
#     start_urls = [
#         "http://delhihighcourt.nic.in/case.asp"
#     ]
#
#     def parse(self, response, **kwargs):
#         items = CourtScrapItem()
#         case = response.css("form.case-type-form")
#         case_type = case.css("select.pull-left option::attr(value)")[0:134].getall()
#         year = case.css("select#c_year option::text").getall()
#         code = case.css("input::attr(value)").getall()
#
#         items['case_type'] = case_type
#         items['year'] = year
#         items['code'] = code
#
#         yield items
#
#
class Cases(scrapy.Spider):
    name = "status"
    start_urls = [
        "http://delhihighcourt.nic.in/dhc_case_status_list_new.asp"
    ]

    def __init__(self):
        self.items = StatusScrapItem()

    def parse(self, response, **kwargs):
        all_div = response.css("li.clearfix")
        for data in all_div:
            self.items['sno'] = data.css("span.sr-no.width-7.pull-left.ac::text").get()
            case_content = data.css("span.pull-left.width-33.title.al::text")[0].get().strip()
            self.items['case_content'] = case_content
            self.items['caseNumber'] = re.findall(r'[0-9]+', case_content)[0]
            self.items['caseYear'] = re.findall(r'[0-9]+', case_content)[1]
            self.items['caseName'] = re.split('(\d+)', case_content)[0].strip()
            self.items['caseStatus'] = re.sub(r"^[^\w$€]+|[^\w$€]+$", "", data.css("font::text").get())
            self.items['petitioner'] = data.css("span.pull-left.width-30.title.al::text")[0].get().strip()
            self.items['respondent'] = (data.css("span.pull-left.width-30.title.al::text")[1].get().strip())[
                                       3::].strip()
            self.items['petitionerAdvocate'] = (data.css("span.pull-left.width-30.title.al::text")[2].get().strip())[
                                               11::]
            listingdate_CourtNo = ' '.join(
                map(str, (''.join(data.css('span.pull-left.width-30.title.al.last::text').getall()).split())))

            orders_judgement = eval(data.css("button.button.pull-right::attr(onclick)").re('href=(.*)')[0])
            self.items['courtNo'] = ""
            self.items['disposedOff'] = ""
            self.items['listingDate'] = ""
            if re.search('Last Date:', listingdate_CourtNo):
                try:
                    self.items['listingDate'] = (re.findall(r'[0-9/]+', listingdate_CourtNo))[0]
                except IndexError:
                    self.items['listingDate'] = ""
            x = (''.join(data.css('span.pull-left.width-30.title.al.last::text').getall()))
            st1 = re.split(r'\r\n', x)
            if re.search('Court No.', listingdate_CourtNo):
                for z in st1:
                    self.items['courtNo'] = re.findall(r'[0-9]+', (st1[2].strip()))[0]
            if re.search('DISPOSED OFF', listingdate_CourtNo):
                for z in st1:
                    self.items['disposedOff'] = re.findall(r'[0-9/]+', (st1[3].strip()))[0]

            self.items['order_judgement'] = ""
            self.items['respondentAdvocate'] = ""
            yield self.items
            url = f'https://delhihighcourt.nic.in/{orders_judgement}'
            yield response.follow(url, callback=self.parse_second)

        next_page = "https://delhihighcourt.nic.in/dhc_case_status_list_new.asp?ayear=&pyear=&SNo=&SRecNo=8&dno=&dyear=&ctype_29=&cno=&cyear=&party=&adv="
        # # next_page = "https://delhihighcourt.nic.in/" + str(
        # #     response.css("a.archivelink::attr(href)").get())
        #
        yield response.follow(next_page, callback=self.parse)

    def parse_second(self, response):
        global pdf_url
        div = response.css("div#InnerPageContent")
        for data in div:
            sno = data.css("span.sr-no.width-7.pull-left.ac::text").getall()
            caseno = data.css("span.pull-left.width-30.title.al button::text").getall()
            pdf_link = data.css("button.LongCaseNoBtn::attr(onclick)").re('href=(.*)')
            date = ''.join(data.css("ul.clearfix.grid.last span.pull-left.width-20.title.al::text").getall()).split()
            if len(caseno) > 0:
                self.items['order_judgement'] = {"caseno": caseno[0], "pdf_link": []}
                for x in range(len(pdf_link)):
                    self.items['order_judgement']['pdf_link'].append({"link": pdf_link[x], "date": date[x]})
            else:
                pass
            yield self.items
            # for x in range(len(pdf_link)):
            #     pdf_url = eval((pdf_link)[x])
            #     yield response.follow(pdf_url, callback=self.get_pdf)

    def get_pdf(self, response):
        pdf_link = (response.css('iframe::attr(src)').extract())[0]
        yield response.follow(pdf_link, callback=self.save_pdf)

    def save_pdf(self, response, **kwargs):
        path = response.url.split('/')[-1]
        self.logger.info('Saving PDF %s', path)
        with open(path, 'wb') as f:
            f.write(response.body)

        PdfReader.read_pdf(path)
        read_zip = self.read_zip(path)
        # self.__delete__(path)
        # yield read_zip

    def read_zip(self, path):
        try:
            abs_path = path.split('.')[-2]
            zip_file = abs_path + ".zip"
            archive = ZipFile(zip_file, 'r')
            json_data = archive.read('structuredData.json')
            json_load = json.loads(json_data)

            data = []
            for x in range(len(json_load['elements'])):
                z = json_load['elements'][x]['Text']
                data.append(z)
            high_court = data[1]
            slice_data = []
            list1 = []
            for x in range(len(data)):
                if data[x][0] == "+":
                    slice_data.append(x)
            for x in range(len(slice_data)):
                if x == 0:
                    list1.append(data[slice_data[x]:(slice_data[x + 1])])
                    continue
                if x % 2 == 0:
                    list1.append(data[slice_data[x - 1]:(slice_data[x])])
                    list1.append(data[slice_data[x]:(slice_data[x + 1])])
                if x == (len(slice_data) - 1):
                    list1.append(data[slice_data[x]:])
            data_list = []
            for z in range(len(list1)):
                if z == 0 or z % 2 == 0:

                    new_data = {
                        'caseType': list1[z][0],
                        'Petitioner': list1[z][1],
                        'Petitioner_advocates': list1[z][5],
                        'Respondent': list1[z][6],
                        'Respondent_advocates': (' '.join(list1[z][8:]))[9:]

                    }
                elif z == (len(list1) - 1):
                    for ds in range(len(list1[(len(list1) - 1)])):

                        if (list1[(len(list1) - 1)])[ds] == 'CORAM: ':
                            orderInfo = (list1[(len(list1) - 1)])[ds::]

                            data_list.append({
                                "Judge": orderInfo[1],
                                "orderDate": orderInfo[4],
                                "judgementThrough": orderInfo[5],
                                "orderJudgement": orderInfo[6:(len(orderInfo) - 2)]
                            }
                            )
                        else:

                            new_data = {
                                'caseType': list1[z][0],
                                'Petitioner': list1[z][1],
                                'Petitioner_advocates': list1[z][3],
                                'Respondent': list1[z][5],
                                'Respondent_advocates': ' '.join(list1[z][9:13])

                            }
                else:

                    new_data = {
                        'caseType': list1[z][0],
                        'Petitioner': list1[z][1],
                        'Petitioner_advocates': list1[z][3],
                        'Respondent': list1[z][5],
                        'Respondent_advocates': (' '.join(list1[z][7:]))[9:]

                    }

                data_list.append(new_data)
            breakpoint()
            return {
                "CourtName": high_court,
                "data": data_list
            }
        except KeyError:

            print("NO TEXT", path)

    def __delete__(self, pdf_name):
        os.remove(pdf_name + ".zip")
        print("Deleted Successfully")


class pdf_download(scrapy.Spider):
    name = "pdf"
    start_urls = ["http://delhihighcourt.nic.in/dhcqrydisp_o.asp?pn=145164&yr=2021"]

    def parse(self, response, **kwargs):
        pdf_link = (response.css('iframe::attr(src)').extract())[0]
        yield response.follow(pdf_link, callback=self.save_pdf)

    def save_pdf(self, response):
        path = response.url.split('/')[-1]

        with open(path, 'wb') as f:
            f.write(response.body)
        PdfReader.read_pdf(path)
        read_zip = self.read_zip(path)
        # self.__delete__(path)
        # yield read_zip

    def read_zip(self, path):
        breakpoint()
        abs_path = path.split('.')[-2]
        zip_file = abs_path + ".zip"
        breakpoint()
        archive = ZipFile(zip_file, 'r')
        json_data = archive.read('structuredData.json')
        json_load = json.loads(json_data)
        data = []
        for x in range(len(json_load['elements'])):
            z = json_load['elements'][x]['Text']
            data.append(z)
        high_court = data[1]
        slice_data = []
        list1 = []
        for x in range(len(data)):
            if data[x][0] == "+":
                slice_data.append(x)
        for x in range(len(slice_data)):
            if x == 0:
                list1.append(data[slice_data[x]:(slice_data[x + 1])])
                continue
            if x % 2 == 0:
                list1.append(data[slice_data[x - 1]:(slice_data[x])])
                list1.append(data[slice_data[x]:(slice_data[x + 1])])
            if x == (len(slice_data) - 1):
                list1.append(data[slice_data[x]:])
        data_list = []
        for z in range(len(list1)):
            if z == 0 or z % 2 == 0:

                new_data = {
                    'caseType': list1[z][0],
                    'Petitioner': list1[z][1],
                    'Petitioner_advocates': list1[z][5],
                    'Respondent': list1[z][6],
                    'Respondent_advocates': (' '.join(list1[z][8:]))[9:]

                }
            elif z == (len(list1) - 1):
                for ds in range(len(list1[(len(list1) - 1)])):

                    if (list1[(len(list1) - 1)])[ds] == 'CORAM: ':
                        orderInfo = (list1[(len(list1) - 1)])[ds::]

                        data_list.append({
                            "Judge": orderInfo[1],
                            "orderDate": orderInfo[4],
                            "judgementThrough": orderInfo[5],
                            "orderJudgement": orderInfo[6:(len(orderInfo) - 2)]
                        }
                        )
                    else:

                        new_data = {
                            'caseType': list1[z][0],
                            'Petitioner': list1[z][1],
                            'Petitioner_advocates': list1[z][3],
                            'Respondent': list1[z][5],
                            'Respondent_advocates': ' '.join(list1[z][9:13])

                        }
            else:

                new_data = {
                    'caseType': list1[z][0],
                    'Petitioner': list1[z][1],
                    'Petitioner_advocates': list1[z][3],
                    'Respondent': list1[z][5],
                    'Respondent_advocates': (' '.join(list1[z][7:]))[9:]

                }

            data_list.append(new_data)

        return {
            "CourtName": high_court,
            "data": data_list
        }

    def __delete__(self, pdf_name):
        os.remove(pdf_name + ".zip")
        print("Deleted Successfully")
    # def open_pdf(self):

    #     path = "ExtractTextInfoFromPDF.json"
    #     with open(path, 'r') as f:
    #         file = f.read()
    #         x = file.strip()
    #         json_load = json.loads(x)
    #         data = []
    #         for x in range(len(json_load['elements'])):
    #             z = json_load['elements'][x]['Text']
    #             data.append(z)
    #     breakpoint()

    # def read_pdf(self, path):
    #     with pdfplumber.open(path) as pdf:
    #         page = pdf.pages[0]
    #         text = page.extract_text(x_tolerance=2)
    #         li = list(text.split("+"))
    #         for x in range(len(li)):
    #             high_court_name = [y for y in (list(li[0].split("\n"))) if not any(x1.isdigit() for x1 in y)]
    #             if x == 2:
    #                 case_type = (li[2].split("....")[0].split("\n"))[0]
    #                 petitioner = (li[2].split("....")[0].split("\n"))[1]
    #                 pt_advocate = (( li[2].split("....")[1].split("versus")[0])[22::].strip()).replace("\n","")
    #                 respondent = (( li[2].split("....")[1].split("versus")[1]).strip()).replace("\n","")
    #                 rs_advocate = (li[2].split("....")[2])[22::].replace("\n", "")
    #         dict_1 = {
    #             "courtName": high_court_name,
    #             "caseType": case_type,
    #             "petitioner": petitioner,
    #             "ptAdvocate": pt_advocate,
    #             "respondent": respondent,
    #             "rs_advocate": rs_advocate
    #         }

    # return dict_1

    # def read_pdf(self, pdf_name):
    #     pdffileobj = open(pdf_name, 'rb')
    #     pdfreader = PyPDF2.PdfFileReader(pdffileobj)
    #     x= pdfreader.numPages
    #     list_content = []
    #     for z in range(0,x):
    #         pageobj =pdfreader.getPage(z)
    #         text = pageobj.extractText()
    #         list_content.append(text)
    #     content = (''.join(list_content[0:])).replace("\n","")
    #     pdffileobj.close()
    #     # self.__delete__(pdf_name)
    #     return content

    # def __delete__(self, pdf_name):
    #     os.remove(pdf_name)
    #     print("Deleted Successfully")

# class pdf_download(scrapy.Spider):
#     name = "pdf"
#     start_urls = ["http://delhihighcourt.nic.in/dhcqrydisp_o.asp?pn=145164&yr=2021"]
#     custom_settings = {
#             "ITEM_PIPELINES": {
#                 'scrapy.pipelines.files.FilesPipeline': 1,
#             },
#         "FILES_STORE": r'H:\LEGAL_PAY\Court_scrap\Court_Scrap\Court_Scrap\spiders\pdf_dw'
#         }
#
#     def parse(self, response, **kwargs):
#         loader = ItemLoader(item=MyItem())
#         pdf_link = (response.css('iframe::attr(src)').extract())[0]
#         loader.add_value('file_urls', pdf_link)
#         yield loader.load_item()
