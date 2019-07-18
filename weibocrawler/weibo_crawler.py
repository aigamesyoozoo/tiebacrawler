import urllib.request
import json
import time
from itertools import cycle
import datetime
from copy import deepcopy
import re
from GTDjango.settings import WEIBO_RESULTS_PATH,PROXIES_PATH
import os
import subprocess

class WeiboCrawlTask(object):

	ALL_WEIBO_TASKS = set()
	
	def __init__(self, uid, folder_name):
		task = WeiboCrawlTask.get_task(folder_name)
		if task: 
			raise TaskAlreadyExists("A Weibo Task for the same uname/foldername is currently being crawled.")
		else:
			self.uid = uid
			self.folder_name = folder_name
			self.status = 'not finished'
			WeiboCrawlTask.ALL_WEIBO_TASKS.add(self)
			self.crawl_weibo()


	def __str__(self):
		return 'WebioCrawlTask(uid='+self.uid+', folder_name='+self.folder_name+', status='+self.status+')'


	# define request info with proxy
	def use_proxy(self, url, proxy_addr):
		req = urllib.request.Request(url)
		req.add_header("User-Agent", "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/49.0.2623.221 Safari/537.36 SE 2.X MetaSr 1.0")
		proxy = urllib.request.ProxyHandler({'http': proxy_addr})
		opener = urllib.request.build_opener(proxy, urllib.request.HTTPHandler)
		urllib.request.install_opener(opener)
		data = urllib.request.urlopen(req).read().decode('utf-8', 'ignore')
		return data


	# get container id for content crawling
	def get_containerid(self, url, proxy_addr):
		data = self.use_proxy(url, proxy_addr)
		content = json.loads(data).get('data')
		for data in content.get('tabsInfo').get('tabs'):
			if(data.get('tab_type') == 'weibo'):
				containerid = data.get('containerid')
		return containerid


	# get user profile
	def get_userInfo(self, id, proxy_pool):
		proxy_addr = next(proxy_pool)
		url = 'https://m.weibo.cn/api/container/getIndex?type=uid&value='+id
		try:
			data = self.use_proxy(url, proxy_addr)
			content = json.loads(data).get('data')
			profile_image_url = content.get('userInfo').get('profile_image_url')
			description = content.get('userInfo').get('description')
			profile_url = content.get('userInfo').get('profile_url')
			verified = content.get('userInfo').get('verified')
			guanzhu = content.get('userInfo').get('follow_count')
			name = content.get('userInfo').get('screen_name')
			fensi = content.get('userInfo').get('followers_count')
			gender = content.get('userInfo').get('gender')
			urank = content.get('userInfo').get('urank')

			return {
				"微博": name,
				"微博主页": profile_url,
				"微博头像地址":profile_image_url,
				"是否认证":verified,
				"微博说明":description,
				"关注人数":guanzhu,
				"粉丝数":fensi,
				"性别":gender,
				"微博等级":urank
			}
		except Exception as e:
			print('get_userInfo:',e)
			self.get_userInfo(id, proxy_pool)

		pass


	def get_weibo(self, id, proxy_pool, folder_name, page=1, range=-1):
		date_time_in_range=True
		now = datetime.datetime.now()
		year = now.year # int

		url = f"https://m.weibo.cn/api/container/getIndex?type=uid&value={id}"
		print(f"profile page: {url}")

		# if there is weibo content
		exception_count = 0
		while True:
			if(self.status == 'cancel' or exception_count > 10):   # Crawling task will be killed if exception(mainly HTTP Error 418) continously occurs more than 10 times
				break
			try:
				proxy_addr = next(proxy_pool)
				print('proxy addr:',proxy_addr)
				weibo_url = f"{url}&containerid={self.get_containerid(url, proxy_addr)}&page={page}"

				data = self.use_proxy(weibo_url, proxy_addr)		
				content = json.loads(data).get('data')
				
				# get weibo content card
				cards = content.get('cards')
				# if this page contains content
				if(len(cards)>0):
					for i, card in enumerate(cards):
						card_type = card.get('card_type')

						# posted weibo
						if(card_type == 9):
							mblog = card.get('mblog') # get post attrs
							id = mblog.get("id")
							created_at = mblog.get('created_at') # creation time
							attitudes_count = mblog.get('attitudes_count') # like count
							comments_count = mblog.get('comments_count') # comment count
							reposts_count = mblog.get('reposts_count') # repost count
							scheme = card.get('scheme') # address
							text = mblog.get('text') # actual content
							a = re.sub(r"<br\s*\/>", "", text)
							b = re.sub(r"<img alt=\[(.*?)\](.*?)>", r'[\1]', a) # replace emoji
							c = re.sub(r"<a\s+href(.*?)>", "", b) # remove link tag
							d = re.sub(r"<\/\s*a>", "", c) # remove link tag
							e = re.sub(r"<span(.*?)>",'', d) # remove span tag
							f = re.sub(r"<\/\s*span>", '', e) # remove span tag
							g = re.sub(r"<a\s+data-url(.*?)>", "[视频]", f) # remove video
							h = re.sub(r"<img(.*?)>", '', g) # remove video thumbnail
							cleaned = re.sub(r"\\t|:|：", '', h)  #remove : and \t

							output_dict = {
								"页数":str(page),
								"微博数":str(i),
								"微博地址":str(scheme),
								"发布时间":str(created_at),
								"微博id":str(id),
								"微博原内容":text,
								"微博内容精简":cleaned,
								"点赞数":str(attitudes_count),
								"评论数":str(comments_count),
								"转发数":str(reposts_count)
							}
							file = str(id)+'-'+str(page)+'-'+str(i)+'.json'
							curr_path = (WEIBO_RESULTS_PATH / folder_name).resolve()
							try:
								os.chdir(curr_path)
								with open(file, 'w', encoding='utf-8') as f:
									json.dump(output_dict, f)
							except Exception as e:
								print('Writing aborted, Unable to write JSON to path, possibly folder was deleted or did not exist initially. Path:', curr_path)
					page += 1
					time.sleep(0.05)
					exception_count = 0
				else:
					break
			except Exception as e:
				print('get_weibo',e)
				exception_count += 1
				

	def crawl_weibo(self):
		proxy_tool_path = (PROXIES_PATH /'proxy_tool.py').resolve()
		proxies = subprocess.check_output(['python',str(proxy_tool_path)]).decode("utf-8").split()  # bytes
		proxy_pool = cycle(proxies)

		profiles = []
		ids = [self.uid]
		# get profile info:
		for id in ids:
			self.get_weibo(id, proxy_pool, self.folder_name)

		if self.status != 'cancel':
			self.status = 'finished'
			WeiboCrawlTask.ALL_WEIBO_TASKS.remove(self)


	def get_weibo_status(self):
		return self.status


	@classmethod
	def cancel_weibo_crawl(cls, folder_name):
		task = WeiboCrawlTask.get_task(folder_name)
		
		if task: 
			WeiboCrawlTask.ALL_WEIBO_TASKS.remove(task)
			for x in WeiboCrawlTask.ALL_WEIBO_TASKS:
				print(x)
			task.status = 'cancel' # flags for any ongoing process to stop. As killing the process directly is not advised.


	@classmethod
	def get_task(cls, folder_name):
		task = next((x for x in WeiboCrawlTask.ALL_WEIBO_TASKS if x.folder_name == folder_name), None)
		return task


class TaskAlreadyExists(Exception):
	pass