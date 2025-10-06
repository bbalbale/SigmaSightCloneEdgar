# Read the original file
with open('API_REFERENCE_V1.4.6.md', 'r') as f:
    lines = f.readlines()

# Read the new admin section content
with open('../../_docs/temp_admin_section.md', 'r') as f:
    new_content = f.read()

# Replace lines 1179-1592 (indices 1178-1591 in 0-indexed list)
# Keep lines 0-1177, add new content, then keep lines from 1592 onwards
new_lines = lines[:1178] + [new_content] + lines[1592:]

# Write back
with open('API_REFERENCE_V1.4.6.md', 'w') as f:
    f.writelines(new_lines)

print("✅ Successfully updated admin section")
print(f"   Replaced lines 1179-1592 ({1592-1179+1} lines)")
print(f"   With new content ({new_content.count(chr(10))} lines)")
