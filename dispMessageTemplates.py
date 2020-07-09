#!/usr/bin/env python3
from textmagic.rest import TextmagicRestClient
import json

#Constants from TextMagicConfiguartion.json
with open('textMagicConfiguration.json') as f:
    textMagicConfig = json.load(f)

USERNAME = textMagicConfig['USERNAME']
TEXTMAGIC_API_KEY = textMagicConfig['TEXTMAGIC_API_KEY']

client = TextmagicRestClient(USERNAME, TEXTMAGIC_API_KEY)

pageNum = 1
templates, pager = client.templates.list(page=pageNum)
totalPages = pager['pageCount']
while(pageNum<=totalPages):
  templates, pager = client.templates.list(page=pageNum)
  for template in templates:
    print('Name: ' + template.name + ' ID: ' + str(template.id))
  pageNum += 1