import tarfile
import json
from pathlib import Path

WINDOWS_RESERVED = {'con', 'prn', 'aux', 'nul', 'com1', 'com2', 'com3', 'com4', 'com5', 'com6', 'com7', 'com8', 'com9', 'lpt1', 'lpt2', 'lpt3', 'lpt4', 'lpt5', 'lpt6', 'lpt7', 'lpt8', 'lpt9'}

tmp_dir = Path(r"c:\Users\d\Documents\open-melayu\.audit-tmp")
output_dir = Path(r"c:\Users\d\Documents\open-melayu\data\prpm_raw")
output_dir.mkdir(parents=True, exist_ok=True)

tar_files = [
    tmp_dir / "shard_1.tar.gz",
    tmp_dir / "shard_1_p2.tar.gz",
    tmp_dir / "shard_1_p3.tar.gz",
    tmp_dir / "shard_2.tar.gz",
    tmp_dir / "shard_3.tar.gz",
    tmp_dir / "shard_4.tar.gz",
    tmp_dir / "shard_5.tar.gz",
]

total_extracted = 0
unique_words = set()
reserved_mapped = {}

for tar_path in tar_files:
    if not tar_path.exists():
        print(f"Skipping missing: {tar_path}")
        continue
    print(f"Unpacking {tar_path.name}...")
    with tarfile.open(tar_path, "r:gz") as tar:
        for member in tar.getmembers():
            if not member.name.endswith(".json"):
                continue
            word_base = Path(member.name).stem.lower()
            
            # Map Windows reserved names
            target_name = f"_reserved_{word_base}.json" if word_base in WINDOWS_RESERVED else f"{word_base}.json"
            if word_base in WINDOWS_RESERVED:
                reserved_mapped[word_base] = target_name
                
            out_file = output_dir / target_name
            f = tar.extractfile(member)
            if f:
                content = f.read()
                with open(out_file, "wb") as dest:
                    dest.write(content)
                total_extracted += 1
                unique_words.add(word_base)

print("================ UNPACK SUMMARY ================")
print(f"Total files written: {total_extracted}")
print(f"Unique words covered: {len(unique_words)}")
if reserved_mapped:
    print(f"Windows reserved mapped: {reserved_mapped}")
print(f"Target directory: {output_dir}")
print("=================================================")
