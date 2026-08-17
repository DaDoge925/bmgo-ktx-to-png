# bmgo-ktx-to-png
A python script to convert Blockman GO ktx assets into a viewable PNG Format

Requirements:
    pip install texture2ddecoder pillow
 
Usage:
    python3 ktx_folder_to_png.py /path/to/source_folder [/path/to/dest_folder]
 
If the destination folder is omitted, one is created next to the source
folder named "<source_folder>_converted".
 
You'll be prompted (y/n) whether non-.ktx files should also be copied
into the destination, so it can be an exact mirror or just the
converted textures.
