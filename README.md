## **Credits**
- **Original Author:** [jamesyeap](https://github.com/jamesyeap)
- **Updated By:** [synchrownicity](https://github.com/synchrownicity)
- **Forked From:** [https://github.com/jamesyeap/food-pricer](https://github.com/jamesyeap/food-pricer)

## **Features and Functionalities**
An API used for fetching the prices of food products from online supermarkets in Singapore (NTUC, Cold Storage and Sheng Siong).

This updated API adds the following features:
- Support for Sheng Siong online store
- Updated `requirements.txt` for compatibility with `Python 3.12` and up
- Improvements to the files in `app` folder to make scrapers more robust against changes in supermarket website UIs
- Added fuzzy matching for product names to allow more flexible and tolerant search queries

Perform the following steps to run the API on your localhost (`127.0.0.1`).

## **Step 1: Clone the repository**
Using `bash/zsh` (macOS/Linux/Unix) or `cmd/Powershell` (Windows), run
```bash
git clone https://github.com/synchrownicity/food-pricer
```

Then, change directory to the cloned repo using:
```bash
cd food-pricer
```

## **Step 2: Virtual Environment Creation and Package Installation**
Here, we will create a virtual environment, activate it, and install the packages listed in `requirements.txt`.
<br>
**Windows:**
```bash
python -m venv myvenv
myvenv\Scripts\activate
pip install -r requirements.txt
```

**macOS/Linux/Unix:**
```bash
python3 -m venv myvenv
source myvenv/bin/activate
pip install -r requirements.txt
```

You can deactivate the virtual environment after testing by running:
```bash
deactivate
```

## **Step 3: Begin the Flask Server**
**Windows:**
```bash
python wsgi.py
```

**macOS/Linux/Unix:**
```bash
python3 wsgi.py
```

It should display something like:
```bash
 * Serving Flask app 'app.api'
 * Debug mode: on
WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.
 * Running on http://127.0.0.1:5000     # This corresponds to your localhost
Press CTRL+C to quit
 * Restarting with stat
 * Debugger is active!
 * Debugger PIN: ****-***-****
```

## **Step 4: Try out the API**
There are several ways to go about this.

### **Option 1 (Preferred): Download and install Postman to test the API**
You can install Postman [here](https://www.postman.com/downloads/).

Sign in and create a new API request. Store it in any collection. <br><br>
Select the API method as **`POST`**. The API URL is the localhost URL shown in Step 3 (something like http://127.0.0.1:5000). <br><br>
Under the API method, select the "Body" tab. Select `raw` and make sure the body is stored in `JSON` format.

**Sample Input for JSON:**
```JSON
{
  "query" : "egg"
}
```

Overall, your Postman page should look like this: <br><br>
<img width="2620" height="593" alt="image" src="https://github.com/user-attachments/assets/41bbcdbe-7d7f-4c86-b2bf-557a804c676d" />

Press `Send` to perform the API call. <br><br>
**Sample Output (Abbreviated for Brevity):**
```JSON
{
    "results": [
        {
            "link": "https://coldstorage.com.sg/en/p/Reese's%20Hollow%20Egg%2092g/i/116398381.html",
            "measurement": "92g",
            "price": 7.0,
            "supermarket": "cold-storage",
            "title": "$ Reese's Hollow Egg 92g"
        },
        {
            "link": "https://coldstorage.com.sg/en/p/Darrell%20Lea%20Easter%20Milk%20Chocolate%20Speckle%20Eggs%20120g/i/116398166.html",
            "measurement": "120g",
            "price": 8.9,
            "supermarket": "cold-storage",
            "title": "$ Darrell Lea Easter Milk Chocolate Speckle Eggs 120g"
        },
        {
            "link": "https://coldstorage.com.sg/en/p/Zaini%20Hot%20Wheels%20Chocolate%20Egg%2C%2060g/i/113306749.html",
            "measurement": "60g",
            "price": 6.75,
            "supermarket": "cold-storage",
            "title": "$ Zaini Hot Wheels Chocolate Egg, 60g"
        }
  ]
}
```

By default, the API will fetch products from your `query` from **all supermarkets**. To call a particular supermarket, add the supermarket name in the link, for example:
- http://127.0.0.1:5000/ntuc/
- http://127.0.0.1:5000/cold-storage/
- http://127.0.0.1:5000/sheng-siong/

### **Option 2: Call the API via Command Line**
**Windows:** <br><br>
Begin the Flask server like you did in Step 3. <br><br>
Open **Powershell** in another terminal and run the following to call the API:
```Powershell
Invoke-RestMethod -Method POST `
   -Uri http://127.0.0.1:5000/ `
   -Body '{"query":"egg"}' `
   -ContentType "application/json" | ConvertTo-Json -Depth 5
```

To format the response in the form of a table:
```Powershell
$response = Invoke-RestMethod -Method POST `
   -Uri http://127.0.0.1:5000/ `
   -Body '{"query":"egg"}' `
   -ContentType "application/json"

$response.results | Format-Table
```

**macOS/Linux/Unix:** <br><br>
Begin the Flask server like you did in Step 3. <br><br>
Open another terminal and run the following to call the API:
```bash
curl -X POST http://127.0.0.1:5000/ \
  -H "Content-Type: application/json" \
  -d '{"query":"egg"}' | jq
```

To format the response in the form of a table:
```bash
curl -X POST http://127.0.0.1:5000/ \
  -H "Content-Type: application/json" \
  -d '{"query":"egg"}' \
  | jq -r '.results[] | "\(.supermarket)\t\(.title)\t\(.price)\t\(.measurement)"' \
  | column -t -s $'\t'
```

If `jq` is not installed on your Unix system, install it by running:
```bash
brew install jq       # macOS
sudo apt install jq   # Ubuntu / Debian distros
```

**Sample Output (Abbreviated for Brevity):** <br>
***Regular Form:*** <br>
```JSON
{
    "results": [
        {
            "link": "https://coldstorage.com.sg/en/p/Reese's%20Hollow%20Egg%2092g/i/116398381.html",
            "measurement": "92g",
            "price": 7.0,
            "supermarket": "cold-storage",
            "title": "$ Reese's Hollow Egg 92g"
        },
        {
            "link": "https://coldstorage.com.sg/en/p/Darrell%20Lea%20Easter%20Milk%20Chocolate%20Speckle%20Eggs%20120g/i/116398166.html",
            "measurement": "120g",
            "price": 8.9,
            "supermarket": "cold-storage",
            "title": "$ Darrell Lea Easter Milk Chocolate Speckle Eggs 120g"
        },
        {
            "link": "https://coldstorage.com.sg/en/p/Zaini%20Hot%20Wheels%20Chocolate%20Egg%2C%2060g/i/113306749.html",
            "measurement": "60g",
            "price": 6.75,
            "supermarket": "cold-storage",
            "title": "$ Zaini Hot Wheels Chocolate Egg, 60g"
        }
  ]
}
```

***Table Form:*** <br><br>
<img width="2825" height="277" alt="image" src="https://github.com/user-attachments/assets/73725f2c-1188-4aee-a2e6-514ad90c02a5" />

By default, the API will fetch products from your `query` from **all supermarkets**. To call a particular supermarket, add the supermarket name in the link, for example:
- http://127.0.0.1:5000/ntuc/
- http://127.0.0.1:5000/cold-storage/
- http://127.0.0.1:5000/sheng-siong/



