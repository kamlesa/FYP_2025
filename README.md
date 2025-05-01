# ENG4701/FIT4701 FYP 2025
AI-Driven Sentiment Analysis for Public Perception of Emerging Technologies

## Automated YouTube comment scraping using Selenium

### Steps to reproduce

Ensure that your chrome version and the chrome driver version is updated to the latest version as mentioned here.

https://googlechromelabs.github.io/chrome-for-testing/#stable

For the context of this project, we are assuming a 64-bit Windows version for the execution platform. You are required to download the zip then extract the folder as-is from the zip file in order to replace the current version in the event that this version is out-of-date.

cd .\chrome-extension-files\

Similarly git pull the YCS continued extension within the chrome-extension-files folder for extension accessibility

git pull https://github.com/pc035860/YCS-cont --allow-unrelated-histories

Then return to current project directory

cd ..

Create the virtual environment, activate it and install selenium which is a required dependency

python -m venv .venv

.venv\Scripts\activate

pip install selenium

Then run the Automated Selenium Processing script in order to process YouTube videos and output processed JSON files accordingly.

python Automated_Selenium_Processing.py