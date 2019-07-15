# Tieba/Weibo Webcrawler

## Setting up

##### 1. Download chromedriver and put in Program Files

- [Download link for chromedriver as of 15 July 2019](http://chromedriver.chromium.org/downloads)
- Place it in _C:\Program Files\Chromedriver\chromedriver.exe_, note the folder/filenames are case-sensitive.


##### 2. _Recommended:_ Setup a virtualenv for this project


##### 3. Install dependencies listed in requirements.txt

- Activate your virtualenv e.g. `.\venv\Scripts\activate`

```
pip install -r requirements.txt
```

- There may be an error for one of the packages, Twisted, as it requires C++ build tools.
- As such, it is recommended to download Visual Studio on your computer to ensure that C++ build tools is available.


##### 4. Configure host

- Go to _\GTDjango_ sub-folder in the root folder and open _settings.py_ in an editor
- _C:\Users\User\Documents\tiebacrawler\GTDjango\settings.py_
- Under `ALLOWED HOSTS = []`, change to your IP address and `'localhost'`
- To obtain your IP address, open Command Prompt, type: `ipconfig`, find the value for _IPv4 Address_
- This is necessary if your want to allow other computers to access your server. If you are the only user, you can keep `ALLOWED HOSTS = []` as an empty list.

5. Enable proxy rotation


## Deployment


##### 1. Open Anaconda prompt x 2

- [Download link for Anaconda as of 15 July 2019](https://www.anaconda.com/distribution/)
- First prompt will be used for running the Django web app on a development server
- Second prompt will be used for running Scrapy, the web scraping tool, as a daemon/background process, where Django can run it.


##### 2. First prompt - Django

- cd to the project root folder, e.g.
  cd _C:\Users\User\Documents\tiebacrawler_

- Activate the correct environment, e.g.

```
conda deactivate
.\venv\Scripts\activate
```

In this case, the virtual environment is customized for the project and stored in the root directory _C:\Users\User\Documents\tiebacrawler_

- Run Django server
- The additional argument "0.0.0.0:8000" allows other computers on the network to access the development server
- If you are the only user, you do not need the additional argument, simply `python manage.py runserver` will do

```
python manage.py runserver 0.0.0.0:8000
```
