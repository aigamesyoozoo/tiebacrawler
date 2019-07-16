# Tieba/Weibo Webcrawler

## Setting up

##### 1. Install python and anaconda
- Recommended to use the same versions used to develop this project
- Python 3.7.1 : [Download link for Python as of 15 July 2019](https://www.python.org/downloads/)
- Anaconda (for Python 3.7): [Download link for Anaconda as of 15 July 2019](https://www.anaconda.com/distribution/)


##### 2. Download chromedriver and put in Program Files
- [Download link for chromedriver as of 15 July 2019](http://chromedriver.chromium.org/downloads)
- Place it in _C:\Program Files\Chromedriver\chromedriver.exe_, note the folder/filenames are case-sensitive.


##### 3. _Recommended:_ Setup a virtualenv for this project
- [How to setup virtualenv](https://uoa-eresearch.github.io/eresearch-cookbook/recipe/2014/11/26/python-virtual-env/)


##### 4. Install dependencies listed in requirements.txt
- First, activate your virtualenv, if you are using one e.g. `.\venv\Scripts\activate`
- Then,
```
pip install -r requirements.txt
```
- There may be an error for one of the packages, Twisted, as it requires C++ build tools.
- As such, it is recommended to download Visual Studio on your computer to ensure that C++ build tools is available.


##### 5. Configure host
- Go to _\GTDjango_ sub-folder in the root folder and open _settings.py_ in an editor
- _C:\Users\User\Documents\tiebacrawler\GTDjango\settings.py_
- Under `ALLOWED HOSTS = []`, change to your IP address and `'localhost'`
- To obtain your IP address, open Command Prompt, type: `ipconfig`, find the value for _IPv4 Address_
- This is necessary if your want to allow other computers to access your server. If you are the only user, you can keep `ALLOWED HOSTS = []` as an empty list.

##### 6. Create results folder
- Create two empty folders in the project root directory (case-sensitive). This is where the scraped data will be stored.
- _/results_
- _/weiboresults_



## Deployment


##### 1. Open Anaconda prompt x 2
- First prompt will be used for running the Django web app on a development server
- Second prompt will be used for running Scrapy, the web scraping tool, as a daemon/background process, where Django can run it.
- For *both* prompts,
- cd to the project root folder, e.g.
```
  cd _C:\Users\User\Documents\tiebacrawler_
```
- Activate the correct virutal environment, if you are using one, e.g.
```
conda deactivate
.\venv\Scripts\activate
```
- In this case, the virtual environment is customized for the project and stored in the root directory _C:\Users\User\Documents\tiebacrawler_


##### 2. First prompt - Django
- Run Django server
- The additional argument "0.0.0.0:8000" allows other computers on the network to access the development server
- If you are the only user, you do not need the additional argument, simply `python manage.py runserver` will do

```
python manage.py runserver 0.0.0.0:8000
```


##### 3. Second prompt - Scrapy
- cd to the webcrawler folder in the project root directory
- then run scrapy
```
cd webcrawler
scrapy
```

##### 4. Run on browser
Open your browser, type the following URL: `localhost:8000/main`
