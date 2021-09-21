# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy
from scrapy import Item
from collections import OrderedDict

import scrapy

# class MyItem(scrapy.Item):
#     # ... other item fields ...
#     file_urls = scrapy.Field()
#     files = scrapy.Field()


class CourtScrapItem(scrapy.Item):
    # define the fields for your item here like:
    case_type = scrapy.Field()
    year = scrapy.Field()
    code = scrapy.Field()


class StatusScrapItem(scrapy.Item):
    sno = scrapy.Field()
    case_content = scrapy.Field()
    caseName = scrapy.Field()
    caseNumber = scrapy.Field()
    caseYear = scrapy.Field()
    caseStatus = scrapy.Field()
    petitioner = scrapy.Field()
    respondent = scrapy.Field()
    petitionerAdvocate = scrapy.Field()
    respondentAdvocate = scrapy.Field()
    listingDate = scrapy.Field()
    courtNo = scrapy.Field()
    disposedOff = scrapy.Field()
    order_judgement = scrapy.Field()
    pdf_link = scrapy.Field()
    date = scrapy.Field()
    caseno = scrapy.Field()
