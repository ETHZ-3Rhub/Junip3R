:: The pyinstaller command is provided by the pyinstaller Python module, so the command needs to be executed inside a valid Python environment
pyinstaller^
 --add-data "src/junip3r/res/*;junip3r/app/res"^
 --add-data "LICENSE;."^
 --add-data "licenses/*;licenses"^
 --onedir^
 --name "Junip3R"^
 --icon "src/junip3r/res/junip3r_icon.ico"^
 --noconsole^
 src/junip3r/main.py -y