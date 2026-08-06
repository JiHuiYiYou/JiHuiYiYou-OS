#!/usr/bin/env python3
"""
Wrap a raw FAT image into a GPT disk image with one EFI System Partition.

Layout:
  LBA 0          : Protective MBR
  LBA 1          : Primary GPT header
  LBA 2-33       : Primary partition entries (32 × 128 bytes)
  LBA 34 - N-34  : ESP partition (raw FAT image)
  LBA N-33 to N-1: Backup partition entries
  LBA N          : (no, this is wrong)

Actually correct:
  LBA 0          : Protective MBR
  LBA 1          : Primary GPT header
  LBA 2 to 33    : Primary partition entries
  LBA 34 to P-1  : Partition 1 (ESP, FAT)
  LBA P to P+32  : Backup partition entries (where P+32 = last_lba - 1)
  LBA last_lba   : Backup GPT header

So last_lba = total - 1
partition_entries backup at LBA last_lba - 32 to last_lba - 1
"""
import struct
import sys
import os

FAT_PATH = sys.argv[1] if len(sys.argv) > 1 else "esp.img"
OUT_PATH = sys.argv[2] if len(sys.argv) > 2 else "disk.img"

SECTOR = 512
GPT_HEADER_SIG = b"EFI PART"
GPT_PART_ENTRY_SIZE = 128
GPT_NUM_ENTRIES = 128  # = 128 × 128 bytes = 16384 bytes = 32 sectors
PART_ENTRIES_SECTORS = GPT_NUM_ENTRIES * GPT_PART_ENTRY_SIZE // SECTOR  # 32

# Partition type GUID for EFI System Partition: C12A7328-F81F-11D2-BA4B-00A0C93EC93B
ESP_TYPE_GUID = bytes.fromhex("28 73 2A C1 1F F8 D2 11 BA 4B 00 A0 C9 3E C9 3B".replace(" ", ""))
# Unique partition GUID (random, just needs to be unique)
ESP_UNIQUE_GUID = bytes.fromhex("01 23 45 67 89 AB CD EF FE DC BA 98 76 54 32 10".replace(" ", ""))

# Read FAT
with open(FAT_PATH, "rb") as f:
    fat_data = bytearray(f.read())
fat_sectors = len(fat_data) // SECTOR

# Layout
# LBA 0: MBR
# LBA 1: GPT header
# LBA 2..2+PART_ENTRIES_SECTORS-1: partition entries (= LBA 2-33)
# Partition starts at LBA 34.
PART_START_LBA = 2 + PART_ENTRIES_SECTORS  # = 34

# Update FAT BPB_HiddSec to match partition start LBA (offset 0x1C-0x1F, 4 bytes LE)
fat_data[0x1C:0x20] = struct.pack("<I", PART_START_LBA)

# Total size = MBR + GPT header + entries + partition + backup entries + backup header
TOTAL_SECTORS = 1 + 1 + PART_ENTRIES_SECTORS + fat_sectors + PART_ENTRIES_SECTORS + 1
LAST_LBA = TOTAL_SECTORS - 1
PART_END_LBA = PART_START_LBA + fat_sectors - 1
BACKUP_ENTRIES_LBA = PART_END_LBA + 1
BACKUP_HEADER_LBA = LAST_LBA

print(f"FAT sectors: {fat_sectors}")
print(f"Total disk sectors: {TOTAL_SECTORS}")
print(f"Partition: LBA {PART_START_LBA}..{PART_END_LBA} ({fat_sectors} sectors)")
print(f"Backup GPT entries LBA: {BACKUP_ENTRIES_LBA}")
print(f"Backup GPT header LBA: {BACKUP_HEADER_LBA}")

# --- Protective MBR ---
mbr = bytearray(SECTOR)
mbr[0:3] = b"\xEB\x63\x90"  # jump
mbr[440:444] = b"\x00\x00\x00\x00"  # disk signature
# Partition entry 1: type 0xEE (GPT protective), starts at LBA 1, ends at LAST_LBA
mbr[446 + 0] = 0x80  # bootable flag
mbr[446 + 4] = 0xEE  # type: GPT protective
mbr[446 + 8:446 + 12] = struct.pack("<I", 1)  # start LBA
mbr[446 + 12:446 + 16] = struct.pack("<I", LAST_LBA)  # size in sectors
mbr[510:512] = b"\x55\xAA"

# --- GPT Header (primary) ---
def crc32(data):
    import binascii
    return binascii.crc32(data) & 0xFFFFFFFF

gpt_hdr = bytearray(SECTOR)
gpt_hdr[0:8] = GPT_HEADER_SIG
gpt_hdr[8:12] = struct.pack("<I", 0x00010000)  # revision 1.0
gpt_hdr[12:16] = struct.pack("<I", 92)  # header size
gpt_hdr[16:20] = struct.pack("<I", 0)  # header CRC32 (fill later)
gpt_hdr[20:24] = struct.pack("<I", 0)  # reserved
gpt_hdr[24:32] = struct.pack("<Q", 0)  # my LBA (fill later)
gpt_hdr[32:40] = struct.pack("<Q", 0)  # alternate LBA (fill later)
gpt_hdr[40:48] = struct.pack("<Q", PART_START_LBA)  # first usable LBA
gpt_hdr[48:56] = struct.pack("<Q", PART_END_LBA)  # last usable LBA
gpt_hdr[56:72] = bytes.fromhex("00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00".replace(" ", ""))  # disk GUID
gpt_hdr[72:80] = struct.pack("<Q", 2)  # partition entries start LBA (right after header)
gpt_hdr[80:84] = struct.pack("<I", GPT_NUM_ENTRIES)
gpt_hdr[84:88] = struct.pack("<I", GPT_PART_ENTRY_SIZE)
gpt_hdr[88:92] = struct.pack("<I", 0)  # partition entries CRC32 (fill later)

# --- Partition entries (primary and backup are identical) ---
def make_part_entry(type_guid, unique_guid, start_lba, end_lba, attrs, name):
    e = bytearray(GPT_PART_ENTRY_SIZE)
    e[0:16] = type_guid
    e[16:32] = unique_guid
    e[32:40] = struct.pack("<Q", start_lba)
    e[40:48] = struct.pack("<Q", end_lba)
    e[48:56] = struct.pack("<Q", attrs)
    # name: UTF-16LE, 36 chars max
    name_utf16 = name.encode("utf-16-le")[:72]
    name_utf16 = name_utf16 + b"\x00" * (72 - len(name_utf16))
    e[56:128] = name_utf16
    return e

part_entry = make_part_entry(
    ESP_TYPE_GUID, ESP_UNIQUE_GUID,
    PART_START_LBA, PART_END_LBA,
    0, "EFI System"
)

partition_entries = bytearray(PART_ENTRIES_SECTORS * SECTOR)
partition_entries[0:128] = part_entry

# Fill in GPT header fields
gpt_hdr[24:32] = struct.pack("<Q", 1)  # my LBA = 1
gpt_hdr[32:40] = struct.pack("<Q", BACKUP_HEADER_LBA)  # alternate LBA

# Compute CRCs
part_entries_crc = crc32(bytes(partition_entries))
gpt_hdr[88:92] = struct.pack("<I", part_entries_crc)

header_crc = crc32(bytes(gpt_hdr))
gpt_hdr[16:20] = struct.pack("<I", header_crc)

# Backup GPT header (at BACKUP_HEADER_LBA)
backup_gpt = bytearray(gpt_hdr)
backup_gpt[24:32] = struct.pack("<Q", BACKUP_HEADER_LBA)
backup_gpt[32:40] = struct.pack("<Q", 1)  # alternate = primary
backup_gpt[72:80] = struct.pack("<Q", BACKUP_ENTRIES_LBA)
backup_header_crc = crc32(bytes(backup_gpt))
backup_gpt[16:20] = struct.pack("<I", backup_header_crc)

# --- Assemble disk image ---
out = bytearray(TOTAL_SECTORS * SECTOR)
out[0:SECTOR] = mbr
out[SECTOR:2*SECTOR] = gpt_hdr
out[2*SECTOR:2*SECTOR + len(partition_entries)] = partition_entries
out[PART_START_LBA*SECTOR:(PART_START_LBA + fat_sectors)*SECTOR] = fat_data
out[BACKUP_ENTRIES_LBA*SECTOR:BACKUP_ENTRIES_LBA*SECTOR + len(partition_entries)] = partition_entries
out[BACKUP_HEADER_LBA*SECTOR:BACKUP_HEADER_LBA*SECTOR + SECTOR] = backup_gpt

with open(OUT_PATH, "wb") as f:
    f.write(out)
print(f"Wrote {OUT_PATH}: {len(out)} bytes ({TOTAL_SECTORS} sectors)")