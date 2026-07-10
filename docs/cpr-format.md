# Cubase CPR Format Notes

## File Header

Bytes 0-3

    RIFF

Bytes 4-7

    Size (appears to be big-endian in Cubase projects tested)

Bytes 8-11

    NUND

## First Chunk

Offset 12

    ROOT

Offset 16

    Chunk size

Offset 20

    Chunk data

## ROOT chunk

Offset: 20

Observed structure:

- 4-byte big-endian length
- ASCII string "Arrangement1"

- 4-byte big-endian length
- ASCII string "PArrangement"

Notes:

- The first string appears to be the arrangement name.
- The purpose of the second string is currently unknown.

## ARCH chunk

Offset 52.

Observed beginning:

- `0xfffffffe` + length-prefixed string `GDocument`
- `0xfffffffe` + length-prefixed string `GModel`
- `0xfffffffe` + length-prefixed string `FShared`
- `0xfffffffe` + length-prefixed string `CmObject`
- `0xffffffff` + length-prefixed string `PArrangement`

After this, the structure changes at offset 156.

After the initial class entries, offset 156 contains:

03 00 04 8d 70

After that, more class-style entries continue:

- MGroupEvent
- MPartEvent
- MEvent

Further ARCH observations from offset 156:

- More marker/name records appear after a 5-byte sequence `03 00 04 8d 70`.
- Observed names:
  - MGroupEvent
  - MPartEvent
  - MEvent
  - CmIDLink
  - MRoot
  - MDataNode
  - MTrackList
  - MTrackEvent
  - MMidiTrackEvent
- These records are interleaved with other binary data, so `read_class_table()` currently only reads the initial simple sequence.

## Audio references

PAudioClip
Name : G Vox_11
File : G Vox_11.wav
Path : E:\Red Guitars\Sapphic 2\Audio\
Type : Broadcast Wave File

Observed audio reference:

- Clip/name field: `G Vox_11`
- Referenced audio file: `Vox_11.wav`
- Original folder: `E:\Red Guitars\Sapphic 2\Audio\`
- File type: `Broadcast Wave File`

The leading `G ` appears in CPR metadata but is not part of the actual filesystem filename.