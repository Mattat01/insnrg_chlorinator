# ha-insnrg-chlorinator

This is a small portion of the INSNRG Pool Chlorinator API. It is currently INCOMPLETE (in case you stumbled upon it)

Currently it only pulls in pH and ORP values like from https://www.insnrgapp.com/pool-chemistry.

The integration takes your INSNRGapp email and password (same as you log into the above website) and logs you in. 
You should remain logged in and get the pool chemistry data every hour (it does not change very quickly and I don't want to spam INSNRG's API every 5 minutes).
It is possible that the integration will break after a period if certain access tokens expire (I'm not aware that they do), or if INSNRG logs you out of your session.
The easiest fix is to remove and re-add the integration, but let me know if it happens and why, if you know, so I can try to self-correct it.

The integration sets up 23 sensors:
- Chlorinator Current pH, 
- Chlorinator Set Point pH, 
- Chlorinator Current ORP,
- Chlorinator Set Point ORP,
- Chlorinator pH Connected,
- Chlorinator ORP Connected
- Pool Current Temperature (or 0 if you don't measure temperature)
- One set of timer data for each of the 4 timers:
	- Start Time
	- End Time
	- Chlorinator (this would be True on the timer controlling your filter pump, so the chlorinator turns on and off)
	- Enabled (is the timer being used at all)

You could use the chemical levels to automate turning your pump on or off (with a smart plug), alerting that your acid drum may be empty, etc.
If you have use cases that require other data to be brought into the integration feel free to ask, and I'll look into it. 
I don't particularly want to let the integration make changes to your system, like you can from the app (such as changing chemical set points, timers, etc.).
If someone else wants to make this a fully fledged API interface, you are welcome to fork this repo, or take it over.

# Installing the INSNRG Chlorinator Custom Integration in Home Assistant
This guide will walk you through the steps to install and set up the custom INSNRG Chlorinator integration in Home Assistant.

## Step-by-Step Installation
### 1. Download the Custom Integration
Download or clone the contents of custom_components/insnrg_chlorinator.

### 2. Copy the Files to Home Assistant
Using File Editor, SSH, or another method, navigate to your Home Assistant custom_components folder. 
If it doesn’t exist, create it in the /homeassistant directory.
Create a new folder within custom_components named ha_insnrg_chlorinator.
Copy the downloaded files into this new folder.

### 3. Restart Home Assistant
After copying the integration files, restart Home Assistant to load the new integration.

### 4. Install the Integration in Home Assistant
After restarting, go to Settings > Devices & Services.
Click on Add Integration and search for "INSNRG Chlorinator"
Select the integration and follow the prompts to enter the email and password you use to log in to https://www.insnrgapp.com.
The integration will now be set up, and sensors for your chlorinator will be created and updated hourly.

## Troubleshooting
### No Sensors Detected: 
Ensure that your credentials (email and password) are correct (test them on the insnrgapp site) and that your chlorinator is visible on the insnrgapp site.
### Token Expiry Issues: 
If your access token expires frequently, the integration should automatically refresh it using the refresh token. If this fails, check the logs for error messages about token refresh failures.
You can find logs under Settings > System > Logs to view any errors or issues related to the integration. Please report them on the issues tab of this repo.