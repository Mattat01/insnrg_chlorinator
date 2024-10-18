# ha-insnrg-chlorinator

This is a small portion of the INSNRG Pool Chlorinator API. It is currently INCOMPLETE (in case you stumbled upon it)

Currently it only pulls in pH and ORP values like from https://www.insnrgapp.com/pool-chemistry.

The integration takes your INSNRGapp email and password (same as you log into the above website) and logs you in. 
You should remain logged in and get the pool chemistry data every hour (it does not change very quickly and I don't want to spam INSNRG's API every 5 minutes).
It is possible that the integration will break after a period if certain access tokens expire (I'm not aware that they do), or if INSNRG logs you out of your session.
The easiest fix is to remove and re-add the integration, but let me know if it happens and why, if you know, so I can try to self-correct it.

The integration sets up 6 sensors:
- Chlorinator Current pH, 
- Chlorinator Set Point pH, 
- Chlorinator Current ORP,
- Chlorinator Set Point ORP,
- Chlorinator pH Connected,
- Chlorinator ORP Connected

You could use the chemical levels to automate turning your pump on or off (with a smart plug), alerting that your acid drum may be empty, etc.
If you have use cases that require other data to be brought into the integration feel free to ask, and I'll look into it. 
I don't particularly want to let the integration make changes to your system, like you can from the app (such as changing chemical set points, timers, etc.).
If someone else wants to make this a fully fledged API interface, you are welcome to fork this repo, or take it over.