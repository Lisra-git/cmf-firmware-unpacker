# Extract files from CMF Watch Pro and CMF Watch Pro 2 firmware
# RapidZapper 2024

import os
import sys
import struct
import argparse
import zlib
import lzma

OTA_FIRMWARE_MAGIC = b'AOTA'
OTA_FIRMWARE_DIR_OFFSET = 0x200
OTA_FIRMWARE_DIR_ENTRY_SIZE = 0x20
OTA_FIRMWARE_HEADER_SIZE = 0x400
OTA_FIRMWARE_DATA_OFFSET = 0x400
OTA_FIRMWARE_VERSION = 0x0100

def is_aota(file_input):
	with open(file_input, 'rb') as f:
		ota_data = f.read()
	#check if aota is at least 1mb
	if len(ota_data) < 0x100000:
		return False
	magic, checksum, header_version, header_size, file_cnt, header_flag, \
	dir_offs, data_offs, data_len, data_crc = struct.unpack("<4sIHHHHHHII36x", ota_data[0:64])
	if magic != OTA_FIRMWARE_MAGIC:
		return False
	return True

def is_sdfs(file_input):
	open_file = open(file_input, "rb")
	file_data = open_file.read()
	open_file.close()
	magic_filename = "sdfs.bin"
	try:
		magic_in_file = file_data[:12].rstrip(b'\x00').decode("utf-8")
	except:
		return False
	if magic_in_file != magic_filename:
		return False
	return True	

def is_compressed_LZMA(file_data):
	if file_data[:4] == b'LZMA':
		return True
	return False

def unpack_sdfs(file_to_extract):
	open_file = open(file_to_extract, "rb")
	file_data = open_file.read()
	folder_path = file_to_extract + "_extracted"
	open_file.close()
	magic_filename = "sdfs.bin"
	#read first 12 bytes
	magic_in_file = file_data[:12].rstrip(b'\x00').decode("utf-8")
	if magic_in_file != magic_filename:
		print("Invalid SDFS file")
		return
	num_files = struct.unpack("<I", file_data[12:16])[0]
	print("Extracting %d files" % num_files)
	file_size = len(file_data)
	file_size_header = struct.unpack("<I", file_data[16:20])[0]
	if file_size != file_size_header:
		print("Invalid file size")
		return
	offset = 0x20
	for i in range(num_files):
		file_name = file_data[offset:offset+12].rstrip(b'\x00').decode("utf-8")
		print(file_name)
		offset += 12
		file_data_offset = struct.unpack("<I", file_data[offset:offset+4])[0]
		offset += 4
		file_size = struct.unpack("<I", file_data[offset:offset+4])[0]
		offset += 4 + 0xc
		file_data_end = file_data_offset + file_size
		print("Extracting %s" % file_name)
		print("File size: %d" % file_size)
		print("Offset: %d" % file_data_offset)
		if not os.path.exists(folder_path):
			os.makedirs(folder_path)
		open_file = open(folder_path + "/" + file_name, "wb")
		open_file.write(file_data[file_data_offset:file_data_end])



def unpack_aota(fpath, out_dir):
	print(f"Unpacking firmware: {fpath}")
	with open(fpath, 'rb') as f:
		ota_data = f.read()

	magic, checksum, header_version, header_size, file_cnt, header_flag, \
	dir_offs, data_offs, data_len, data_crc = struct.unpack("<4sIHHHHHHII36x", ota_data[0:64])

	if magic != OTA_FIRMWARE_MAGIC:
		panic('Invalid magic')

	print(f"Magic: {magic.decode('utf8')}")
	print(f"Header Version: {header_version}")
	print(f"Header Size: {header_size} bytes")
	print(f"Number of files: {file_cnt}")
	print(f"Data CRC: {data_crc:#010x}")
	print(f"Directory Offset: {dir_offs}")
	print(f"Data Offset: {data_offs}")
	print(f"Data Length: {data_len} bytes")

	if not os.path.exists(out_dir):
		os.makedirs(out_dir)

	for i in range(file_cnt):
		entry_offs = dir_offs + i * OTA_FIRMWARE_DIR_ENTRY_SIZE
		name, offset, file_length, checksum = \
			struct.unpack("<12s4xII4xI", ota_data[entry_offs : entry_offs + OTA_FIRMWARE_DIR_ENTRY_SIZE])

		filename = name.decode('utf8').rstrip('\0')
		file_data = ota_data[offset : offset + file_length]
		if file_data[:4] == b'LZMA':
			outputFileDecomp = b''
			offset = 0
			while file_data[offset:offset+4] == b'LZMA':
				offset += 8
				decompSize = struct.unpack("<I", file_data[offset:offset+4])[0]
				offset += 8
				outputFileDecomp += lzma.decompress(file_data[offset:offset+decompSize])
				offset += decompSize
			file_data = outputFileDecomp


		print(f"\nFile {i+1}:")
		print(f"  Name: {filename}")
		print(f"  Offset: {offset} bytes")
		print(f"  Length: {file_length} bytes")
		print(f"  CRC32 Checksum: {checksum:#010x}")

		output_path = os.path.join(out_dir, filename)
		with open(output_path, 'wb') as wf:
			wf.write(file_data)
		print(f"  Extracted to: {output_path}")

def check_files_in_dir(path):
	files = os.listdir(path)
	for file in files:
		if os.path.isdir(path + "/" + file):
			check_files_in_dir(path + "/" + file)
		else:
			if (is_aota(path + "/" + file)):
				print(f"Found AOTA file: {file}")
				unpack_aota(path + "/" + file, path + "/" + file + "_extracted")
				check_files_in_dir(path + "/" + file + "_extracted")
			if (is_sdfs(path + "/" + file)):
				print(f"Found SDFS file: {file}")
				unpack_sdfs(path + "/" + file)




def main():
	if len(sys.argv) != 2:
		print("Usage: python extract.py <file>")
		sys.exit(1)
	if not os.path.exists(sys.argv[1]):
		print("File not found")
		sys.exit(1)
	if not is_aota(sys.argv[1]) and not is_sdfs(sys.argv[1]):
		print("Invalid file")
		sys.exit(1)
	if is_aota(sys.argv[1]):
		print("AOTA file")
		unpack_aota(sys.argv[1], sys.argv[1] + "_extracted")
		check_files_in_dir(sys.argv[1] + "_extracted")
	elif is_sdfs(sys.argv[1]):
		print("SDFS file")
		unpack_sdfs(sys.argv[1])
		check_files_in_dir(sys.argv[1])

if __name__ == "__main__":
	main()