"""
Main entry point for the RMS BMS UI application.
This script initializes the GUI root and the Application Controller, 
linking the graphical interface with the Serial Controller.
"""
from gui_master import RootGUI, AppController
from Serial_Com_ctrl import SerialCtrl

# Initialize the main Tkinter root window
root = RootGUI()

# Create the application controller, passing the root window 
# and a new instance of the Serial communication controller
AppController(root.root, SerialCtrl())

# Start the Tkinter main event loop to display the GUI
root.root.mainloop()
