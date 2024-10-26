# ha-insnrg-chlorinator
![GitHub Release](https://img.shields.io/github/release/Mattat01/ha-insnrg-chlorinator.svg?style=plastic) ![GitHub issues](https://img.shields.io/github/issues/Mattat01/ha-insnrg-chlorinator.svg?style=plastic) ![GitHub Stars](https://img.shields.io/github/stars/Mattat01/ha-insnrg-chlorinator.svg?style=plastic) ![GitHub Last Commit](https://img.shields.io/github/last-commit/Mattat01/ha-insnrg-chlorinator.svg?style=plastic) ![Documentation](https://img.shields.io/badge/docs-excellent-brightgreen.svg?style=plastic) ![HACS Status](https://img.shields.io/badge/HACS-Default-blue.svg?style=plastic) ![Home Assistant](https://img.shields.io/badge/Home%20Assistant-%3E%3D%202024.10.1-brightgreen.svg?style=plastic) 
<p align="center">
  <img src="https://github.com/user-attachments/assets/8e05446e-bc14-4a21-9f6d-8e9f9defd630" alt="Image">
</p>

<p align="center">
 <img src="https://github.com/user-attachments/assets/4b954930-9611-4408-a047-09a35a6e01cc" alt="Image">
</p>

This is a small part of the INSNRG Pool Chlorinator API and collects data from [https://www.insnrgapp.com](https://www.insnrgapp.com). You cannot set anything through this integration—use the official interface for that—but you can automate other actions and notifications with this information.

The integration uses your INSNRGapp email and password (the same ones you use to log in to the website above) and logs you in. If you set it up for the first time while your chlorinator/pump is off, you will receive "unknown" chemical data, but the data should be updated the next time the chlorinator runs.

The integration does not request chemical data while the chlorinator is off, as it can be faulty. However, once it has received data for the first time, it retains it overnight and through restarts of Home Assistant. You should remain logged in and receive the pool chemistry data hourly (it doesn't change very quickly, and I don't want to burden INSNRG's API more frequently).

If the integration loses access to the chlorinator data after some time, or if INSNRG logs you out of your session, you may need to re-authenticate. If Home Assistant does not automatically log you back in, the easiest solution is to remove and re-add the integration. Let me know if it happens and why, if you know, so I can try to correct it myself.

The integration sets up 23 sensors:

- **Chlorinator Current pH**
- **Chlorinator Set Point pH**
- **Chlorinator Current ORP**
- **Chlorinator Set Point ORP**
- **Chlorinator pH Connected**
- **Chlorinator ORP Connected**
- **Pool Current Temperature** (or 0 if you don't measure temperature)
- **Timer data for each of the 4 timers**:
  - Start Time
  - End Time
  - Chlorinator (this would be *True* for the timer controlling your filter pump, so the chlorinator turns on and off)
  - Enabled (is the timer being used at all)

If you have use cases that require other data to be brought into the integration, feel free to ask, and I'll look into it. I do not intend to allow the integration to make changes to your system, like you can from the app (e.g., changing chemical set points, timers, etc.). If someone else wants to make this a fully-fledged API interface, you are welcome to fork this repository or take it over, but note that you could cause damage by randomly turning things on and off.

---

## **Installing the INSNRG Chlorinator Custom Integration in Home Assistant via HACS**

This guide will walk you through the steps to install and set up the custom INSNRG Chlorinator integration in Home Assistant via the Home Assistant Community Store (HACS).

### **Prerequisites**

- **Home Assistant** must already be installed and configured on your system.
- **HACS** should be installed. If not, follow the instructions at [HACS Installation](https://www.hacs.xyz/docs/use/download/prerequisites/).

### **Step-by-Step Guide**

#### **1. Open HACS**

- In Home Assistant, navigate to the side menu and click on **"HACS"**.

#### **2. Add Custom Repository**

- Click on the **three dots menu** at the top right in HACS.
- Select **"Custom Repositories"**.

#### **3. Add Repository**

- In the **"Add Custom Repository URL"** field, paste the following URL:
  ```
  https://github.com/Mattat01/ha-insnrg-chlorinator
  ```
- Under **"Category"**, select **"Integration"**.
- Click on **"Add"**.

#### **4. Install Integration**

- After adding, the integration should be available in HACS.
- Search for **"INSNRG Chlorinator"** in the HACS integrations list.
- Click on the integration and then click **"Install this repository"**.
- Confirm the installation by clicking **"Install"**.

#### **5. Restart Home Assistant**

- After installation, you need to restart Home Assistant to load the integration.
- Go to **"Settings" > "System" > "Restart"** and click on **"Restart"**.

#### **6. Set Up Integration**

- After the restart, navigate to **"Settings" > "Devices & Services"**.
- Click on **"Add Integration"** (the **"+"** symbol at the bottom right).
- Search for **"INSNRG Chlorinator"**.
- Select the integration from the list.

#### **7. Enter Credentials**

- Enter your **email address** and **password** that you use to log in to [https://www.insnrgapp.com](https://www.insnrgapp.com).
- Click **"Submit"** or **"Next"** to complete the setup.

#### **8. Verify Installation**

- After successful setup, the sensors for your chlorinator will be created.
- You can view them under **"Settings" > "Devices & Services"**.
- Add the desired sensors to your dashboard to display the data.

### **Troubleshooting**

#### **No Sensors Detected**

- **Check Your Credentials**: Ensure that the email and password entered are correct by logging in directly on the [INSNRG website](https://www.insnrgapp.com).
- **Chlorinator Visibility**: Make sure your chlorinator is visible on the INSNRG website and linked to your account.

#### **Token Expiry Issues**

- **Automatic Token Refresh**: The integration should automatically refresh your access tokens. If this fails:
  - **Check Logs**: Go to **"Settings" > "System" > "Logs"** to check for error messages regarding token expiry.
  - **Reinstall Integration**: Delete the integration and reinstall it to force re-authentication.
  - **Report Errors**: If the problem persists, report the issue with the relevant log information in the [Issues section of the repository](https://github.com/Mattat01/ha-insnrg-chlorinator/issues).

---


**By installing via HACS, you receive automatic updates and easier management of the integration within Home Assistant. If you have any questions or issues, we are happy to assist you.**
