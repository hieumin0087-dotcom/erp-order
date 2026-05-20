import sys

path = r"C:\Trợ lý AI\erp_data_entry.py"
with open(path, "r", encoding="utf-8") as f:
    lines = f.readlines()

start_idx = 908 # Line 909
end_idx = 1178 # Line 1179

print("Deleting from:", lines[start_idx].strip())
print("To:", lines[end_idx].strip())

if "try:" in lines[start_idx] and "context.close()" in lines[end_idx + 1]:
    del lines[start_idx:end_idx + 1]
    with open(path, "w", encoding="utf-8") as f:
        f.writelines(lines)
    print("Deleted successfully!")
else:
    print("Sanity check failed, nothing deleted.")
