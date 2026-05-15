from gui_master import RootGUI, ComGui


RootMaster = RootGUI()

ComMaster = ComGui(RootMaster.root)

RootMaster.root.mainloop()