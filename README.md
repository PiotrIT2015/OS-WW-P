## OS-WW-P

## Table of contents
* [General info](#general-info)
* [Running](#running)
* [Technologies](#technologies)

## General info
A simple OS simulation with desktop.

1. **Web Explorer**
WhiteDwarf is an advanced search engine project that expands upon the foundational concepts of a basic version I previously developed in Java.
The initial Java prototype served as a proof-of-concept during my academic studies and was successfully presented at several university and 
local tech conferences, showcasing my early work in information retrieval systems.
This current iteration, WhiteDwarf, is being developed in Python and aims to tackle more complex challenges in search engine design. 
It focuses on implementing more sophisticated indexing algorithms, improving search result relevance through advanced ranking mechanisms, 
and exploring efficient methods for handling larger datasets. The goal is to create a robust and scalable search solution.
The application is a website whose main function is to run the web crawling process (automatic browsing and analysis of websites).

2. **Witchcraft**
It is a clone of Youtube. To use it you have to download project 'RelaxationTube' from repository.

3. **PCAAnalyzer**
As part of the master's thesis, was created a web application that analyzes data from many files, ending a presentation data on the charts. 
There was implemented a statistical algorithm (PCA) for data analysis. Asynchronous communication, enabled by the framework, 
allows for the interaction of computer units and manipulation of shared data.

3. **PandasAnalyzer**
As part of the project, a python script was commissioned to compare CSV files. These are large files, up to several hundred thousand lines 
in length.

4. **NetworkMonitor**
I've always would like to implement this project in Java since the university. Unfortunately those days there wasn't such a great 
tools i.e.chatGPT . It is only a shortcut to run a file[*.jar] . 

## Running

**MS Windows**

1. `winget install Python.Python.3.10`(via cmd)
2. add python to PATH
3. `pip install python-nmap` [po użyciu instalatora(plik nmap-setup.exe) z oficialnej strony]
4. configure Apache and MySQL on XAMPP/Cloud
5. double click on `install-require-libraries.bat`
6. double click on `run.bat`

**Other[MS Windows]**

1. `docker-compose up\down`
2. os-ww-p: `http://localhost:55000`
3. Apache: `http://localhost:55001`
4. MySQL/phpMyAdmin; `http://localhost:55002`

**Linux**

1. `sudo apt install python3`
2. `sudo apt install nmap`
3. configure Apache and MySQL on XAMPP/Cloud
4. `./install-require-libraries.sh` (via bash)
5. `./run.sh` (via bash)

**Other[Linux]**

# Uruchamianie środowiska Docker (Python App + Apache + MySQL + phpMyAdmin)

Ten projekt zawiera cztery kontenery:  
1. **MySQL** – baza danych  
2. **Python App** – aplikacja z własnym obrazem  
3. **Apache** – serwer HTTP  
4. **phpMyAdmin** – panel do zarządzania bazą  

Wszystkie kontenery komunikują się przez dedykowaną sieć `secure_network`.  
Dane MySQL są przechowywane w wolumenie `mysql_data`.  

---

## 1. Utwórz sieć i wolumen

```bash
docker network create secure_network
docker volume create mysql_data
```

##2. Uruchom MySQL

```bash
docker run -d \
  --name mysql_db \
  --network secure_network \
  --restart unless-stopped \
  -e MYSQL_ROOT_PASSWORD=rootpassword \
  -e MYSQL_DATABASE=mydatabase \
  -e MYSQL_USER=user \
  -e MYSQL_PASSWORD=password \
  -v mysql_data:/var/lib/mysql \
  mysql:8.0
```

###3. Uruchom aplikację Python. Pobierz obraz i uruchom kontener:

```bash
docker pull piotrit2015/os-ww-p:5.0

docker run -d \
  --name os-ww-p \
  --network secure_network \
  --restart unless-stopped \
  -v $(pwd):/main.py \
  -p 55000:80 \
  -e MYSQL_HOST=mysql_db \
  -e MYSQL_USER=root \
  -e MYSQL_PASSWORD=" " \
  -e MYSQL_DATABASE=search_db \
  piotrit2015/os-ww-p:5.0
```

##4. Uruchom Apache

```bash
docker run -d \
  --name apache_server \
  --network secure_network \
  --restart unless-stopped \
  -p 55001:80 \
  -v $(pwd)/apache.conf:/usr/local/apache2/conf/extra/httpd-vhosts.conf \
  httpd:2.4
```
  
##5. Uruchom phpMyAdmin

```bash
docker run -d \
  --name phpmyadmin_ui \
  --network secure_network \
  --restart unless-stopped \
  -p 55002:80 \
  -e PMA_HOST=mysql_db \
  -e PMA_PORT=3306 \
  phpmyadmin:latest
 ```
  
##6. Sprawdzenie działania

*Aplikacja: http://localhost:55000

*Apache: http://localhost:55001

**phpMyAdmin: http://localhost:55002




	
## Technologies
Project is created with:
* python version: 3.10
...,but project also use:
* Apache
* MySQL

![image alt](https://github.com/PiotrIT2015/OS-WW-P/blob/master/screenshot.jpeg?raw=true)

![image alt](https://github.com/PiotrIT2015/OS-WW-P/blob/master/screenshot-2.jpeg?raw=true)

![image alt](https://github.com/PiotrIT2015/OS-WW-P/blob/master/screenshot-3-pca.jpeg?raw=true)

![image alt]( https://github.com/PiotrIT2015/OS-WW-P/blob/master/screenshot-4-nmap.jpeg?raw=true )

![image alt]( https://github.com/PiotrIT2015/OS-WW-P/blob/master/screenshot-5-web-explorer-1.jpeg?raw=true )

![image alt]( https://github.com/PiotrIT2015/OS-WW-P/blob/master/screenshot-6-web-explorer-2.jpeg?raw=true )

![image alt]( https://github.com/PiotrIT2015/OS-WW-P/blob/master/screenshot-7-settings-calculator-2.jpeg?raw=true )

![image alt]( https://github.com/PiotrIT2015/OS-WW-P/blob/master/screenshot-8-file-explorer.jpeg?raw=true )


