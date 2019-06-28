import urllib.request
import json
import time
from itertools import cycle
import asyncio
from proxybroker import Broker
import datetime

# retrieve proxy
async def retrieve(proxies):
	while True:
		proxy = await proxies.get()
		if proxy is None: break
		return proxy

# define request info with proxy
def use_proxy(url, proxy_addr):
	req = urllib.request.Request(url)
	req.add_header("User-Agent", "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/49.0.2623.221 Safari/537.36 SE 2.X MetaSr 1.0")
	proxy = urllib.request.ProxyHandler({'http': proxy_addr})
	opener = urllib.request.build_opener(proxy, urllib.request.HTTPHandler)
	urllib.request.install_opener(opener)
	data = urllib.request.urlopen(req).read().decode('utf-8', 'ignore')
	return data

# get container id for content crawling
def get_containerid(url, proxy_addr):
	# url = 'https://m.weibo.cn/api/container/getIndex?type=uid&value='+id
	data = use_proxy(url, proxy_addr)
	content = json.loads(data).get('data')
	for data in content.get('tabsInfo').get('tabs'):
		if(data.get('tab_type') == 'weibo'):
			containerid = data.get('containerid')
	return containerid

# get user profile
def get_userInfo(id, proxy_addr):
	url = 'https://m.weibo.cn/api/container/getIndex?type=uid&value='+id
	data = use_proxy(url, proxy_addr)
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

	pass

# get weibo content
def get_weibo(id, proxy_pool, page=1, range=10):
	date_time_in_range=True
	now = datetime.datetime.now()
	year = now.year # int
	while date_time_in_range:
		proxy_addr = next(proxy_pool)
		# construct urls
		url = 'https://m.weibo.cn/api/container/getIndex?type=uid&value='+id
		weibo_url = 'https://m.weibo.cn/api/container/getIndex?type=uid&value='+id+'&containerid='+get_containerid(url, proxy_addr)+'&page='+str(page)
		print(weibo_url)
		try:
			data = use_proxy(weibo_url, proxy_addr)
			content = json.loads(data).get('data')
			raw_file = str(id)+'_page_'+str(page)+'.json'
			with open(raw_file, 'w') as f:
				json.dump(content, f)
			# get weibo content card
			cards = content.get('cards')
			# if this page contains content
			if(len(cards)>0):
				for i, card in enumerate(cards):
					print("第"+str(page)+"页，第"+str(i+1)+"条微博")
					card_type = card.get('card_type')
					# posted weibo
					if(card_type == 9):
						mblog = card.get('mblog') # get post attrs
						created_at = mblog.get('created_at') # creation time
						if '-' in created_at: # with date infomation and not the first one on the first pageon
							if len(created_at.split('-')) == 2: # current year
								created_at = str(year)+'-'+created_at
								created_at_date_obj = datetime.datetime.strptime(created_at, '%Y-%m-%d')
							elif len(created_at.split('-')) == 3: # past years
								created_at_date_obj = datetime.datetime.strptime(created_at, '%Y-%m-%d')
							delta = now - created_at_date_obj
							if delta.days+1>=range:
								if i ==0 and page == 1:
									date_time_in_range = True
								else:
									date_time_in_range = False
									break
						print(created_at)
						attitudes_count = mblog.get('attitudes_count') # like count
						comments_count = mblog.get('comments_count') # comment count
						reposts_count = mblog.get('reposts_count') # repost count
						scheme = card.get('scheme') # address
						text = mblog.get('text') # actual content

						output_dict = {
							"页数":str(page),
							"微博数":str(i),
							"微博地址":str(scheme),
							"发布时间":str(created_at),
							"微博内容":text,
							"点赞数":str(attitudes_count),
							"评论数":str(comments_count),
							"转发数":str(reposts_count)
						}
						file = str(id)+'-'+str(page)+'-'+str(i)+'.json'
						with open(file, 'w', encoding='utf-8') as f:
							json.dump(output_dict, f)
				page += 1
				time.sleep(0.05)
			else:
				break
		except Exception as e:
			print(e)


# main
if __name__ == "__main__":
	# get proxy pool
	proxies = asyncio.Queue()
	broker = Broker(proxies)
	tasks = asyncio.gather(broker.find(types=['HTTP', 'HTTPS'], limit=10), retrieve(proxies))
	# uncomment the following if not using jupyter
	loop = asyncio.get_event_loop()
	loop.run_until_complete(tasks)
	# time.sleep(3) # comment out this if not using jupyter
	proxies = list(map(lambda x: ':'.join(map(str, x)), list(broker.unique_proxies.keys())))
	proxy_pool = cycle(proxies)

	# click on date link to get id
	ids  = ['6465174830']
	# range = date

	profiles = []

	# get profile info:
	for id in ids:
		proxy_addr = next(proxy_pool)
		print('proxy: '+proxy_addr)
		profiles.append(get_userInfo(id, proxy_addr))
		# containerid = get_containerid(id, proxy_addr)
		get_weibo(id, proxy_pool)

	print(profiles[0])
	broker.stop()

