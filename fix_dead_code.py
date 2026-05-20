p = r"c:\Trợ lý AI\erp_data_entry.py"
with open(p, encoding="utf-8") as f:
    lines = f.readlines()
# Remove lines 908-1129 (0-indexed: 907-1128)
del lines[907:1129]
with open(p, "w", encoding="utf-8") as f:
    f.writelines(lines)
print(f"Done. File now has {len(lines)} lines.")
