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