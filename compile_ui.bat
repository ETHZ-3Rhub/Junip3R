:: The pyside6-uic command is provided by the pyside6 Python module, so the command needs to be executed inside the conda environment
call conda activate Labell3R
echo Compiling Widgets...
pyside6-uic "ui/PoseEditor.ui" -o "app/labeller/layout/pose_editor.py"
pyside6-uic "ui/SelectionControls.ui" -o "app/labeller/layout/selection_controls.py"
pyside6-uic "ui/ImageNavigation.ui" -o "app/labeller/layout/image_navigation.py"
pyside6-uic "ui/Editor.ui" -o "app/labeller/layout/editor.py"
echo Compiling Main Windows...
pyside6-uic "ui/Labeller.ui" -o "app/labeller/layout/labeller.py"
pyside6-uic "ui/FrameExtractor.ui" -o "app/frame_extractor/layout/frame_extractor.py"