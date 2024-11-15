# ⚙️ Nodepay mining 

* ```` INSTAL ````
* You can run it anywhere, but I use Termux
````
pkg ugrade && update 
````
````
pkg install git
````
````
pkg install python
````
````
pkg install python-pip
````
````
pip install aiohttp
````
````
pkg install loguru
````

# ⏭️ Next-step

* ```` CLONE ````
````
git clone https://github.com/fawkins/nodepay.git
````

* Fill in your proxy ```` ( Http ) ````
````
nano proxy.txt
````


* Fill in your Token
````
nano token.txt
````

```` How to get tokens ```` Use Inspect Element in your browser ```` F12 ```` 
go to the console, then type ```` localStorage.getItem('np_token'); ````

![Token](https://github.com/user-attachments/assets/d6e38b07-1d25-48e3-b377-0f2e4619605d)


# ☕ Start

If you have completed all the steps,
you can run the command below

````
python start.py
````
