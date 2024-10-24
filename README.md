# ha-insnrg-chlorinator

This is a small portion of the INSNRG Pool Chlorinator API and collects data from https://www.insnrgapp.com. You cannot set anything through this integration, use the official interface for that, but you can automate other actions and alerts with this information.

The integration takes your INSNRGapp email and password (same as you log into the above website) and logs you in.
When you set it up for the first time whilst your chlorinator/pump is off you will get 'unknown' chemical data, but data should start updating when the chlorinator is running next. 
The integration does not request chemical data whils the chlorinator is off, as it can be erroneous, but once it has obtained data for the first time it will retain it overnight and through restarts of HA.
You should remain logged in and get the pool chemistry data every hour (it does not change very quickly and I don't want to spam INSNRG's API more frequently).
If the integration loses access to the chlorinator data after a period of time, or if INSNRG logs you out of your session, you may need to reauthenticate.
If HA does not log you back in automatically, the easiest fix is to remove and re-add the integration, but let me know if it happens and why, if you know, so I can try to self-correct it.

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

If you have use cases that require other data to be brought into the integration feel free to ask, and I'll look into it. 
I don't intend to allow the integration make changes to your system, like you can from the app (such as changing chemical set points, timers, etc.).
If someone else wants to make this a fully fledged API interface, you are welcome to fork this repo, or take it over, but you could cause damage by turning things on and off randomly.

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
The integration should automatically refresh your access tokens. If this fails, check the logs for error messages about token refresh failures.
You can find logs under Settings > System > Logs to view any errors or issues related to the integration.
Try deleting and reinstalling the integration first, which should reauthenticate you, but otherwise please report any issues, with log information, on the issues tab of this repo.