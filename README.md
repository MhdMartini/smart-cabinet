# Smart_cabinet
Capstone Project

This script is the Inventory Application of the Smart Cabinet Capstone project I am working on this semester (FALL20,) with the help of my colleague Thanakiath, who is authoring the id_scanner script. The script is currently under development and is not tested yet. The script is to be deployed on Raspberry pi 4.

# System Requirements
The Smart Cabinet contains stock belonginig to the Electrical and Computer Engineering Lab at the University of Masachusetts Lowell. It is operated by an RFID card reader, and it contains kits (boxes) tagged with RFID tags which inform the Cabinet what items are present vs. borrowed. 
The system shall:
1- Read the RFID number on a student's ID when they scan it
2- Only allow students who are explicitly permitted by the lab instructors
3- Read RFID tags on the component kits
4- Keep track of stock traffic and maintain a log of which students borrowed/returned what items and at what times
5- Record video of Cabinet users while the Cabinet door is open, and save the videos for a week window
6- Be robust, secure, easily operable, and allow easy adding or removing of allowed users/admins
7- Be efficient at formal Lab times by implimenting a supervised mode which relaxes security for the sake of practicality.
