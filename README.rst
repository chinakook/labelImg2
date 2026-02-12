LabelImg2
========

LabelImg2 is a graphical image annotation tool.

It is written in Python and uses Qt for its graphical interface.

Annotations are saved as XML files in PASCAL VOC format.

Annotations can now be exported in Ultralytics YOLO's BOX format and OBB format.

.. image:: img/screen0.jpg
     :alt: labelImg2 with rotated box and extra label

Installation
------------------

Build from source
~~~~~~~~~~~~~~~~~

Linux/macOS
^^^^^^^^^^^

uv is recommended for building the app.
Download and install uv python evironment:

.. code::

    curl -LsSf https://astral.sh/uv/install.sh | sh
    uv venv --python 3.13 .venv
    source .venv/bin/activate
    uv pip install -r requirements.txt

Windows + uv
^^^^^^^

Open the Windows PowerShell and go to the `labelImg <#labelimg>`__ directory. 
You might need admin privileges to install.

.. code::

    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

Then run the following commands in the Command Prompt:

.. code::

    set Path=C:\Users\<Your User Name>\.local\bin;%Path%
    uv venv --python 3.13 .venv
    .\.venv\Scripts\activate.bat
    uv pip install -r requirements.txt

Atfer that, you can run the app:

.. code::

    python labelImg.py
    python labelImg.py [IMAGE_PATH] [PRE-DEFINED CLASS FILE]

Usage
-----

Steps (PascalVOC)
~~~~~

1. Build and launch using the instructions above.
2. Click 'Change default saved annotation folder' in Menu/File
3. Click 'Open Dir'
4. Click 'Create RectBox'
5. Click and release left mouse to select a region to annotate the rect
   box
6. You can use right mouse to drag the rect box to copy or move it

The annotation will be saved to the folder you specify.

You can refer to the below hotkeys to speed up your workflow.

Create pre-defined classes
~~~~~~~~~~~~~~~~~~~~~~~~~~

You can edit the
`data/predefined\_classes.txt <https://github.com/chinakook/labelImg2/blob/master/data/predefined_classes.txt>`__
to load pre-defined classes

OBB Format
~~~~~~~~~~

TODO:

Hotkeys
~~~~~~~

+------------+--------------------------------------------+
| Ctrl + u   | Load all of the images from a directory    |
+------------+--------------------------------------------+
| Ctrl + r   | Change the default annotation target dir   |
+------------+--------------------------------------------+
| Ctrl + s   | Save                                       |
+------------+--------------------------------------------+
| Ctrl + d   | Copy the current label and rect box        |
+------------+--------------------------------------------+
| Space      | Flag the current image as verified         |
+------------+--------------------------------------------+
| w          | Create a rect box                          |
+------------+--------------------------------------------+
| d          | Next image                                 |
+------------+--------------------------------------------+
| a          | Previous image                             |
+------------+--------------------------------------------+
| z          | Rotates counterclockwise, big steps;       |
+------------+--------------------------------------------+
| x          | Rotates counterclockwise, small steps;     |
+------------+--------------------------------------------+
| c          | Rotates clockwise, small steps;            |
+------------+--------------------------------------------+
| v          | Rotates clockwise, big steps.              |
+------------+--------------------------------------------+
| f          | Rotates 90 degrees clockwise.              |
+------------+--------------------------------------------+
| del        | Delete the selected rect box               |
+------------+--------------------------------------------+
| Enter      | Select a rect box                          |
+------------+--------------------------------------------+
| Ctrl++     | Zoom in                                    |
+------------+--------------------------------------------+
| Ctrl--     | Zoom out                                   |
+------------+--------------------------------------------+
| ↑→↓←       | Keyboard arrows to move selected rect box  |
+------------+--------------------------------------------+

How to contribute
~~~~~~~~~~~~~~~~~

Send a pull request

License
~~~~~~~
`Free software: MIT license <https://github.com/chinakook/labelImg2/blob/master/LICENSE>`_

Citation: Chinakook. LabelImg2. Git code (2018-2026). https://github.com/chinakook/labelImg2
