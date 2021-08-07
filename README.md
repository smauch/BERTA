# BERTA
**B**ooking **E**lusive **R**ooms **T**otally **A**utomated



## Installation

### Requirements
Ensure you have at least Python 3.8 installed. 

```
pip install -r requirements.txt
```

If you get an error by pytesseract you may try first installing Pillow with 

```
pip install Pillow
```
and afterwards try to install the packages from the requirements.txt again.

### Tesseract
Get the tesseract binaries:
```
sudo apt-get install tesseract-ocr
```

### Geckodriver

Get the latest version of [geckodriver](https://github.com/mozilla/geckodriver/releases) and add it to PATH environment variable.
