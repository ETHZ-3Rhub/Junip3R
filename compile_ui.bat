:: The pyside6-uic command is provided by the pyside6 Python module, so the command needs to be executed inside the conda environment
:: No .ui file is currently wired up - every layout/*.py file is hand-written.
:: To regenerate one from a Designer .ui file, uncomment and adjust a line like the example below.
echo Compiling Main Windows...
:: pyside6-uic "ui/FrameExtractor.ui" -o "src/junip3r/frame_extractor/layout/frame_extractor.py"