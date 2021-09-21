# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
from itemadapter import ItemAdapter
import json
import mysql.connector
import re


class CourtScrapPipeline:

    def __init__(self):
        self.courtName = ""
        self.casetype_ID = int()
        self.create_connection()


    def create_connection(self):
        self.conn = mysql.connector.connect(
            host='localhost',
            user='root',
            password='root',
            database='legalpaycasedb',
        )
        self.curr = self.conn.cursor()

    def process_item(self, item, spider):
        self.update_db_status(item)
        self.update_db_pt(item)
        self.update_db_pt_advocate(item)
        if len(item['order_judgement']) > 0:
            self.get_exsisting(item)
        else:
            self.store_db(item)
        return item

    def update_db_status(self, item):
        self.curr.execute("SELECT * FROM casestatustable")
        status = self.curr.fetchall()
        if len(status) > 0:
            query1 = "Select * From `casestatustable` WHERE `caseStatus` = %s"
            val = [item['caseStatus']]
            self.curr.execute(query1, val)
            status_list = self.curr.fetchall()

            if len(status_list) < 1:
                insert_query = "INSERT into casestatustable(caseStatus) values (%s)"
                insert_val = [item['caseStatus']]
                self.curr.execute(insert_query, insert_val)
        else:
            insert_query = "INSERT into casestatustable(caseStatus) values (%s)"
            insert_val =[item['caseStatus']]
            self.curr.execute(insert_query, insert_val)
        
    def update_db_pt(self, item):
        self.curr.execute("SELECT * FROM petitionername")
        pt = self.curr.fetchall()
        if len(pt) > 0:
            query1 = "Select * From `petitionername` WHERE `petitionerName` = %s"
            val = [item['petitioner']]
            self.curr.execute(query1, val)
            status_list = self.curr.fetchall()

            if len(status_list) < 1:
                insert_query = "INSERT into petitionername(petitionerName) values (%s)"
                insert_val = [item['petitioner']]
                self.curr.execute(insert_query, insert_val)
        else:
            insert_query = "INSERT into petitionername(petitionerName) values (%s)"
            insert_val = [item['petitioner']]
            self.curr.execute(insert_query, insert_val)

    def update_db_pt_advocate(self, item):
        self.curr.execute("SELECT * FROM petitioneradvocate")
        pt = self.curr.fetchall()
        if len(pt) > 0:
            query1 = "Select * From `petitioneradvocate` WHERE `petitionerAdvocate` = %s"
            val =  [item['petitionerAdvocate']]
            self.curr.execute(query1, val)
            status_list = self.curr.fetchall()

            if len(status_list) < 1:
                insert_query = "INSERT into petitioneradvocate(petitionerAdvocate) values (%s)"
                insert_val = [ item['petitionerAdvocate']]
                self.curr.execute(insert_query, insert_val)
        else:
            insert_query = "INSERT into petitioneradvocate(petitionerAdvocate) values (%s)"
            insert_val = [ item['petitionerAdvocate']]
            self.curr.execute(insert_query, insert_val)



    def store_db(self, item):
        self.courtName = "Delhi High Court"

        query = "INSERT into master_table(`S.NO`,courtName,caseType, caseNumber, caseYear, caseStatus, petitioner,petitionerAdvocate, respondent,respondentAdvocate, listingDAte, courtNo, disposedOff,order_judegment) " \
                "values (%s, %s,%s, %s, %s,(SELECT id FROM casestatustable WHERE caseStatus=%s),(SELECT id FROM petitionername WHERE petitionerName=%s), (SELECT id FROM petitioneradvocate WHERE petitionerAdvocate=%s), %s, %s, %s, %s, %s, %s )"
        val = [item['sno'],
               self.courtName,
               # self.casetype_ID,

               item['caseName'],  # field for display name in DB Table
               item['caseNumber'],
               item['caseYear'],
               item['caseStatus'],
               item['petitioner'],
               item['petitionerAdvocate'],
               item['respondent'],
               item['respondentAdvocate'],
               item['listingDate'],
               item['courtNo'],
               item['disposedOff'],
               item['order_judgement'],
               ]
        self.curr.execute(query, val)
        self.conn.commit()

    def get_exsisting(self, item):
        if len(item['order_judgement']) > 0:
            self.curr.execute("SELECT caseNumber,caseYear, caseType FROM legalpaycasedb.casetable")
            list = self.curr.fetchall()
            case_number = re.findall(r'[0-9]+', item['order_judgement']['caseno'])[0]
            case_year = re.findall(r'[0-9]+', item['order_judgement']['caseno'])[1]
            caseName = re.split('(\d+)', item['order_judgement']['caseno'])[0].strip()
            for x in list:
                if x[0] == case_number and x[1] == case_year and caseName == x[2]:
                    data = json.dumps(item['order_judgement'])
                    self.curr.execute("""Update casetable Set order_judegment = (%s) where `caseNumber` = (%s) """, (
                        data, x[0]
                    ))
                    self.conn.commit()

# class CasePipeline:
#
#     def __init__(self):
#         self.create_connection()
#
#     def create_connection(self):
#         self.conn = mysql.connector.connect(
#             host='localhost',
#             user='root',
#             password='root',
#             database='legalpaycasedb',
#         )
#         self.curr = self.conn.cursor()
#
#     def process_item(self, item, spider):
#         self.store_db(item)
#         return item
#
#     def store_db(self, item):
#         for x in item['case_type']:
#             query = "Insert into casetypetable(caseType) values (%s)"
#             val = (x, )
#             self.curr.execute(query, val)
#
#             self.conn.commit()
#
