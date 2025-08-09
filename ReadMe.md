create  a virtual env
```
python -m venv venv
# Activate venv:
# On Windows
venv\Scripts\activate
# On macOS/Linux
source venv/bin/activate

```

Instal dependencies
````
pip install -r requirements.txt
````

run the code
```
uvicorn main:app --reload
```