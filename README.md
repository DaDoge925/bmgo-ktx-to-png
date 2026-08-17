# bmgo-ktx-to-png

A Python script to convert Blockman GO `.ktx` texture files into viewable `.png` images.

## Requirements

- Python 3
- Install dependencies:

```bash
pip install texture2ddecoder pillow
```

## Usage

```bash
python3 ktx_folder_to_png.py /path/to/source_folder [/path/to/dest_folder]
```

### Arguments

- `ktx_folder_to_png.py` = the script file
- `/path/to/source_folder` = the unzipped appres folder that contains the `.ktx` files
- `/path/to/dest_folder` = where the converted `.png` files will be written; this can be left blank

If the destination folder is omitted, the script creates one next to the source folder named `<source_folder>_converted`.

## Extra prompt

You will be asked whether non-`.ktx` files should also be copied into the destination folder.

- `y` = copy everything as an exact mirror of the source folder
- `n` = only keep the converted PNG files

If you only want the PNG textures, use `n`.
