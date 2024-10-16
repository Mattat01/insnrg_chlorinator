# ha-insnrg-chlorinator

This is a small portion of the INSNRG Pool Chlorinator API. It is currently INCOMPLETE (in case you stumbled upon it)

Currently it only pulls in pH and ORP values like from https://www.insnrgapp.com/pool-chemistry.

To complete this integration I (or someone who actually knows how to do it already) needs to set up to AWS Congito authentication process so that users enter their e-mail and password when setting up the integration, and the integration will take care of the AWS access token refreshes. As it is currently written you need to enter your current access token and system ID when setting up the integration, and it will work for about an hour until the access token expires :(

I would appreciate help from anyone who could help finalise this.
