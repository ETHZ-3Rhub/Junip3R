:: The pyside6-uic command is provided by the pyside6 Python module, so the command needs to be executed inside the conda environment
echo Compiling Widgets...
pyside6-uic "ui/PoseEditor.ui" -o "src/junip3r/labeller/layout/pose_editor.py"
pyside6-uic "ui/SelectionControls.ui" -o "src/junip3r/labeller/layout/selection_controls.py"
pyside6-uic "ui/ImageNavigation.ui" -o "src/junip3r/labeller/layout/image_navigation.py"
pyside6-uic "ui/Editor.ui" -o "src/junip3r/labeller/layout/editor.py"
echo Compiling Main Windows...
pyside6-uic "ui/Labeller.ui" -o "src/junip3r/labeller/layout/labeller.py"
pyside6-uic "ui/FrameExtractor.ui" -o "src/junip3r/frame_extractor/layout/frame_extractor.py"