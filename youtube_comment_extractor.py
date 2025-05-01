import re
import json

def parse_comment_block(block):
    lines = [line.strip() for line in block.strip().split('\n') if line.strip()]
    
    if not lines or "[COMMENT]" not in lines[0]:
        return None  # Skip non-comment blocks

    comment_data = {
        "username": "",
        "profile_url": "",
        "comment_url": "",
        "posted": "",
        "edited": False,
        "likes": 0,
        "replies": 0,
        "comment": ""
    }

    try:
        comment_data["username"] = lines[1]
        comment_data["profile_url"] = lines[2]
        comment_data["comment_url"] = lines[3]

        meta_line = lines[4]
        if "(edited)" in meta_line:
            comment_data["edited"] = True
            meta_line = meta_line.replace("(edited)", "").strip()

        # Parse metadata
        meta_parts = [p.strip() for p in meta_line.split('|')]
        comment_data["posted"] = meta_parts[0]

        for part in meta_parts[1:]:
            if "like:" in part:
                comment_data["likes"] = int(part.replace("like:", "").strip())
            elif "reply:" in part:
                comment_data["replies"] = int(part.replace("reply:", "").strip())

        # Remaining lines are the comment text
        comment_data["comment"] = "\n".join(lines[5:]).strip()

        return comment_data
    except Exception as e:
        print("Failed to parse block:\n", block)
        print("Error:", e)
        return None


# Load text content
with open("youtube_1.txt", "r", encoding="utf-8") as file:
    text = file.read()

# Extract all blocks between ##### ... #####
comment_blocks = re.findall(r'#####(.*?)#####', text, re.DOTALL)

# Parse blocks
parsed_comments = [parse_comment_block(block) for block in comment_blocks if parse_comment_block(block)]

# Save to JSON
with open("parsed_youtube_comments.json", "w", encoding="utf-8") as f:
    json.dump(parsed_comments, f, indent=2, ensure_ascii=False)

print(f"Parsed {len(parsed_comments)} comments and saved to parsed_youtube_comments.json.")