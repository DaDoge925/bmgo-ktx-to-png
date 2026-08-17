#!/usr/bin/env python3
"""
ktx_folder_to_png.py

Recursively scans a source folder for .ktx (KTX 1.0) texture files and
writes a mirrored copy of the folder to a destination path, with every
.ktx file decoded and saved as .png (same relative path, same name,
just a different extension). Any non-.ktx files are copied through
unchanged so the destination is otherwise an identical copy of the source.

Supports ASTC, ETC1/ETC2/EAC, BC1/BC3/BC4/BC5/BC6/BC7 (S3TC/RGTC/BPTC),
PVRTC, and ATITC compressed formats, plus common uncompressed RGB/RGBA.

Requirements:
    pip install texture2ddecoder pillow

Usage:
    python3 ktx_folder_to_png.py /path/to/source_folder [/path/to/dest_folder]

If the destination folder is omitted, one is created next to the source
folder named "<source_folder>_converted".

You'll be prompted (y/n) whether non-.ktx files should also be copied
into the destination, so it can be an exact mirror or just the
converted textures.
"""

import os
import sys
import shutil
import struct

import texture2ddecoder as t2d
from PIL import Image

KTX1_IDENTIFIER = bytes(
    [0xAB, 0x4B, 0x54, 0x58, 0x20, 0x31, 0x31, 0xBB, 0x0D, 0x0A, 0x1A, 0x0A]
)

# ---- ASTC block sizes -------------------------------------------------
ASTC_BLOCK_SIZES = {
    0x93B0: (4, 4), 0x93B1: (5, 4), 0x93B2: (5, 5), 0x93B3: (6, 5),
    0x93B4: (6, 6), 0x93B5: (8, 5), 0x93B6: (8, 6), 0x93B7: (8, 8),
    0x93B8: (10, 5), 0x93B9: (10, 6), 0x93BA: (10, 8), 0x93BB: (10, 10),
    0x93BC: (12, 10), 0x93BD: (12, 12),
}

# ---- Other compressed formats: glInternalFormat -> decoder handler ----
# Handler is (function_name, extra_args) where extra_args are appended
# after (data, w, h) when calling the texture2ddecoder function.
OTHER_FORMATS = {
    0x8D64: ("decode_etc1", ()),           # ETC1_RGB8_OES
    0x9274: ("decode_etc2", ()),           # RGB8_ETC2
    0x9275: ("decode_etc2", ()),           # SRGB8_ETC2
    0x9276: ("decode_etc2a1", ()),         # RGB8_PUNCHTHROUGH_ALPHA1_ETC2
    0x9277: ("decode_etc2a1", ()),         # SRGB8_PUNCHTHROUGH_ALPHA1_ETC2
    0x9278: ("decode_etc2a8", ()),         # RGBA8_ETC2_EAC
    0x9279: ("decode_etc2a8", ()),         # SRGB8_ALPHA8_ETC2_EAC
    0x9270: ("decode_eacr", ()),           # R11_EAC
    0x9271: ("decode_eacr_signed", ()),    # SIGNED_R11_EAC
    0x9272: ("decode_eacrg", ()),          # RG11_EAC
    0x9273: ("decode_eacrg_signed", ()),   # SIGNED_RG11_EAC
    0x83F0: ("decode_bc1", ()),            # DXT1 RGB
    0x83F1: ("decode_bc1", ()),            # DXT1 RGBA
    0x83F3: ("decode_bc3", ()),            # DXT5
    0x8DBB: ("decode_bc4", ()),            # RGTC1 (BC4)
    0x8DBC: ("decode_bc4", ()),            # Signed RGTC1
    0x8DBD: ("decode_bc5", ()),            # RGTC2 (BC5)
    0x8DBE: ("decode_bc5", ()),            # Signed RGTC2
    0x8E8E: ("decode_bc6", ()),            # BPTC signed float (BC6H)
    0x8E8F: ("decode_bc6", ()),            # BPTC unsigned float (BC6H)
    0x8E8C: ("decode_bc7", ()),            # BPTC UNORM (BC7)
    0x8E8D: ("decode_bc7", ()),            # BPTC SRGB UNORM (BC7)
    0x8C00: ("decode_pvrtc", (False,)),    # PVRTC RGB 4bpp
    0x8C02: ("decode_pvrtc", (False,)),    # PVRTC RGBA 4bpp
    0x8C01: ("decode_pvrtc", (True,)),     # PVRTC RGB 2bpp
    0x8C03: ("decode_pvrtc", (True,)),     # PVRTC RGBA 2bpp
    0x8C92: ("decode_atc_rgb4", ()),       # ATC RGB
    0x8C93: ("decode_atc_rgba8", ()),      # ATC RGBA explicit alpha
    0x87EE: ("decode_atc_rgba8", ()),      # ATC RGBA interpolated alpha
}

# Uncompressed glFormat values we know how to read directly
UNCOMPRESSED_MODES = {
    6408: "RGBA",  # GL_RGBA
    6407: "RGB",   # GL_RGB
}


def decode_ktx1(path):
    """Decode the level-0 image of a KTX1 file. Returns a PIL Image."""
    with open(path, "rb") as f:
        data = f.read()

    if data[:12] != KTX1_IDENTIFIER:
        raise ValueError("not a KTX 1.0 file (identifier mismatch — "
                          "KTX2 or corrupt file?)")

    offset = 12
    (endianness, gl_type, gl_type_size, gl_format, gl_internal_format,
     gl_base_internal_format, width, height, depth,
     num_array_elements, num_faces, num_mip_levels,
     bytes_of_kv_data) = struct.unpack_from("<13I", data, offset)
    offset += 13 * 4
    offset += bytes_of_kv_data

    image_size = struct.unpack_from("<I", data, offset)[0]
    offset += 4
    blob = data[offset:offset + image_size]

    # Compressed: gl_format == 0
    if gl_format == 0:
        if gl_internal_format in ASTC_BLOCK_SIZES:
            bw, bh = ASTC_BLOCK_SIZES[gl_internal_format]
            decoded = t2d.decode_astc(blob, width, height, bw, bh)
        elif gl_internal_format in OTHER_FORMATS:
            fn_name, extra = OTHER_FORMATS[gl_internal_format]
            fn = getattr(t2d, fn_name)
            decoded = fn(blob, width, height, *extra)
        else:
            raise ValueError(
                f"unsupported compressed glInternalFormat "
                f"0x{gl_internal_format:04X}"
            )
        # texture2ddecoder outputs BGRA byte order
        return Image.frombytes("RGBA", (width, height), decoded, "raw", "BGRA")

    # Uncompressed
    if gl_format in UNCOMPRESSED_MODES:
        mode = UNCOMPRESSED_MODES[gl_format]
        return Image.frombytes(mode, (width, height), blob)

    raise ValueError(f"unsupported uncompressed glFormat {gl_format}")


def ask_yes_no(prompt):
    while True:
        answer = input(f"{prompt} (y/n): ").strip().lower()
        if answer in ("y", "yes"):
            return True
        if answer in ("n", "no"):
            return False
        print("Please answer 'y' or 'n'.")


def convert_folder(src_root, dst_root, copy_others):
    src_root = os.path.abspath(src_root)
    dst_root = os.path.abspath(dst_root)

    if not os.path.isdir(src_root):
        print(f"Error: source folder does not exist: {src_root}")
        sys.exit(1)

    converted, copied, skipped, failed = 0, 0, 0, 0

    for dirpath, dirnames, filenames in os.walk(src_root):
        rel_dir = os.path.relpath(dirpath, src_root)
        dst_dir = os.path.join(dst_root, rel_dir) if rel_dir != "." else dst_root
        os.makedirs(dst_dir, exist_ok=True)

        for name in filenames:
            src_path = os.path.join(dirpath, name)

            if name.lower().endswith(".ktx"):
                dst_name = os.path.splitext(name)[0] + ".png"
                dst_path = os.path.join(dst_dir, dst_name)
                try:
                    img = decode_ktx1(src_path)
                    img.save(dst_path)
                    rel_out = os.path.relpath(dst_path, dst_root)
                    print(f"[OK]     {os.path.relpath(src_path, src_root)} -> {rel_out}")
                    converted += 1
                except Exception as e:
                    print(f"[FAILED] {os.path.relpath(src_path, src_root)}: {e}")
                    failed += 1
            elif copy_others:
                dst_path = os.path.join(dst_dir, name)
                shutil.copy2(src_path, dst_path)
                copied += 1
            else:
                skipped += 1

    print(f"\nDone. Converted: {converted}, copied as-is: {copied}, "
          f"skipped: {skipped}, failed: {failed}")


if __name__ == "__main__":
    if len(sys.argv) not in (2, 3):
        print(f"Usage: {sys.argv[0]} <source_folder> [destination_folder]")
        sys.exit(1)

    src = sys.argv[1]

    if len(sys.argv) == 3:
        dst = sys.argv[2]
    else:
        src_abs = os.path.abspath(src)
        parent = os.path.dirname(src_abs)
        base_name = os.path.basename(src_abs.rstrip(os.sep))
        dst = os.path.join(parent, f"{base_name}_converted")
        print(f"No destination specified — using: {dst}")

    copy_others = ask_yes_no("Copy non-.ktx files into the destination too?")

    convert_folder(src, dst, copy_others)