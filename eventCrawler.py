import sys
import os
import requests
import json
import time
import re
from queue import Queue
import threading
from bs4 import BeautifulSoup as bs

urls_queue = Queue()
out_queue = Queue()
lock = threading.Lock()

class ThreadReptile(threading.Thread):
	def __init__(self, urls_queue, out_queue, number):
		threading.Thread.__init__(self)
		self.urls_queue = urls_queue
		self.out_queue = out_queue
		self.taskNumber = number

	def getSoup(self, url): 
		user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.113 Safari/537.36'
		headers = {'User-Agent':user_agent}
		response = requests.get(url, headers=headers)
		#print(response.content)
		#print(response.status_code)
		#print(response.encoding)

		content = response.text

		soup = bs(content, 'lxml')
		#print(soup)
		return soup

		
	def getPageNumber(self, soup):
		#result = soup.find(class_ = 'pagination__navigation-group')
		result = soup.find_all(name = 'a', attrs={"href":re.compile(r"(\W)(page=)(\d)")})
		num = len(result)	
		self.taskNumber = num
		return num
		
	def getEventList(self, soup):
		name = []
		eventLink = [] 
		imageUrl = []
		time = []
		location = []
		tag = []
		eventList = [] 

		parent = soup.find_all(name = 'div', attrs={"class": 'list-card-v2 l-mar-top-2 js-d-poster'})
		#print(parent.contents)
		
		for children in parent:
			#print(children.get('data-share-name'))
			name.append(children.get('data-share-name'))
			#print(children.get('data-share-url'))
			eventLink.append(children.get('data-share-url'))

			#print(children.a.contents[1].div.img.get('src'))
			imageUrl.append(children.a.contents[1].div.img.get('src'))
			#print(children.a.contents[3].time.string.replace(' ', '').strip())
			time.append(children.a.contents[3].time.string.replace(' ', '').strip())
			#print(children.a.contents[3].contents[5].string.strip())
			location.append(children.a.contents[3].contents[5].string.strip())

			#print(children.contents[3].div)
			tagString = ""
			for Tag in children.contents[3].div.children:
				tagString = tagString+Tag.string.strip()+" "
			
			#print(tagString)
			tag.append(tagString)
			

		#process zipping
		for (n, e, i, ti, l, ta) in zip(name, eventLink, imageUrl, time, location, tag):
			eventList.append((n, e, i, ti, l, ta))

		return eventList

	def run(self):	
		while True:	
			url = self.urls_queue.get()
			count = self.taskNumber-self.urls_queue.qsize()
			print("Now is processing page "+str(count))
			eventList = []
			try:
				soup = self.getSoup(url)
				eventList = self.getEventList(soup)
			except Exception as e:
				print(e)
				#raise e.reason
			
			
			self.out_queue.put(eventList)
			self.urls_queue.task_done()

class File:
	def __init__(self, typeString):
		self.filename = "Eventribute "+typeString
	
	def openfile(self):
		#self.file = open(self.filename+'.txt', 'a+')
		self.file = open(self.filename+'.txt', 'w+')
		return self.file

	def writedata(self, eventList):
		for i in range(len(eventList)):
			self.file.write(eventList[i][3]+'\n')
			self.file.write(eventList[i][0]+'\n')
			self.file.write(eventList[i][4]+'\n')
			self.file.write(eventList[i][5]+'\n')
			self.file.write('Event Link: '+eventList[i][1]+'\n')
			self.file.write('Event ImageUrl: '+eventList[i][2]+'\n\n\n\n')



if __name__ == '__main__':

	category = ['film-and-media--events', 'sports-and-fitness--events', \
				'hobbies--events', 'travel-and-outdoor--events', \
				'food-and-drink--events', 'fashion--events', \
				'school-activities--events', 'music--events']
	while True:
		eventTypeInput = input('1.Film and Media\n2.Sports and Fitness\n3.Hobbies\n4.Travel and Outdoor\n5.Food and Drink\n6.Fashion\n7.School Activities\n8.Music\n9.Exit\nPlease select the type of event: ')		
		
		if(int(eventTypeInput) == 9):
			break

		else:
			priceTypeInput = input('\n1.Free\n2.All prices\nPlease select the price of the event: ')		
			fileTypeString = re.sub('[-*]', ' ', category[int(eventTypeInput)-1])
			priceAppend = '(Free)' if int(priceTypeInput) == 1 else '(All Prices)'
			fileTypeString = fileTypeString + priceAppend

			fileObj = File(fileTypeString)
			eventFile = fileObj.openfile()
			num = 0
			repObj = ThreadReptile(urls_queue, out_queue, num)
			

			BaseUrl = 'https://www.eventbrite.com.au/d/'
			areaPart = 'australia--sydney/'
			#priceType = 'free--'
			priceType = 'free--' if int(priceTypeInput) == 1 else ''
			#eventType = 'hobbies--events/'
			eventType = category[int(eventTypeInput)-1]
			crtOption = '?crt=regular'
			pageOption = '&page='
			sortOption = '&sort=best'
			searchUrl = BaseUrl+areaPart+priceType+eventType+crtOption+sortOption
			print('The base serching url is: '+searchUrl)

			
			baseSoup = repObj.getSoup(searchUrl)
			#eventlist = getEvent(soup)
			num = repObj.getPageNumber(baseSoup)
			print("There are "+str(num)+" pages in total")
			

			for i in range(1, num+1):
				searchUrl = BaseUrl+areaPart+priceType+eventType+crtOption+pageOption+str(i)+sortOption
				#print("Now is processing page "+str(i))
				urls_queue.put(searchUrl)

			start = time.time()

			#set the number of thread
			for i in range(4):
				t = ThreadReptile(urls_queue, out_queue, num)
				t.setDaemon(True)
				t.start()
			
			urls_queue.join()
			#out_queue.join()

			print('Synchronization success')
			eventLists = []
			while not out_queue.empty():
				added_list = out_queue.get()
				eventLists.extend(added_list)
			
			end = time.time()
			print(str(end-start)+" seconds needed in total")

			#soup = getSoup(searchUrl)
			#eventLists = getEventList(soup)

			fileObj.writedata(eventLists)
			eventFile.close()
	
	
