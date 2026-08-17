# bmgo-ktx-to-png
A python script to convert Blockman GO ktx assets into a viewable PNG Format

Requirements:
- Python
- then do `pip install texture2ddecoder pillow`
 
Usage:
    python3 ktx_folder_to_png.py /path/to/source_folder [/path/to/dest_folder]
Where:
    - ktx_folder_to_png.py = The file name
    - /path/to/source_folder = The unzipped appres folder for the script to look for ktx files on
    - /path/to/dest_folder = What folder to write the converted png files, although u can leave this blank
 
If the destination folder is omitted, one is created next to the source
folder named "<source_folder>_converted".
 
You'll be prompted (y/n) whether non-.ktx files should also be copied
into the destination, so it can be an exact mirror or just the
converted textures.
If you're just curious about the png assets, i recommend you inputting "n" on this one
