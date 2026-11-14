import sys

def check_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    stack = []
    pairs = {')': '(', '}': '{', ']': '['}
    line = 1
    col = 1
    in_string = False
    in_multiline_string = False
    in_comment = False
    in_block_comment = False
    i = 0
    n = len(content)

    while i < n:
        char = content[i]
        if char == '\n':
            line += 1
            col = 1
            i += 1
            in_comment = False
            continue

        if not in_string and not in_multiline_string and not in_comment and not in_block_comment:
            if content[i:i+3] == '"""':
                in_multiline_string = True
                i += 3
                col += 3
                continue
            if content[i:i+2] == '//':
                in_comment = True
                i += 2
                col += 2
                continue
            if content[i:i+2] == '/*':
                in_block_comment = True
                i += 2
                col += 2
                continue
            if char == '"':
                in_string = True
                i += 1
                col += 1
                continue
            if char == "'":
                # char literal like '\n'
                if i + 2 < n and content[i+2] == "'":
                    i += 3
                    col += 3
                    continue
                elif i + 3 < n and content[i+1] == '\\' and content[i+3] == "'":
                    i += 4
                    col += 4
                    continue
            if char in '({[':
                stack.append((char, line, col))
            elif char in ')}]':
                if not stack:
                    print(f'Error: Unmatched {char} at {line}:{col} in {path}')
                    return False
                top, l, c = stack.pop()
                if top != pairs[char]:
                    print(f'Error: Mismatched {top} at {l}:{c} with {char} at {line}:{col} in {path}')
                    return False
        elif in_multiline_string:
            if content[i:i+3] == '"""':
                in_multiline_string = False
                i += 3
                col += 3
                continue
        elif in_string:
            if char == '\\':
                i += 2
                col += 2
                continue
            if char == '"':
                in_string = False
        elif in_block_comment:
            if content[i:i+2] == '*/':
                in_block_comment = False
                i += 2
                col += 2
                continue

        i += 1
        col += 1

    if stack:
        top, l, c = stack[-1]
        print(f'Error: Unclosed {top} from {l}:{c} in {path}')
        return False
    print(f'OK: {path}')
    return True

files = [
    r'C:\Ai_code\037movies\app\src\main\java\com\movies037\ui\player\PlayerViewModel.kt',
    r'C:\Ai_code\037movies\app\src\main\java\com\movies037\ui\player\PlayerScreen.kt',
    r'C:\Ai_code\037movies-mobile\app\src\main\java\com\movies037\mobile\ui\player\PlayerViewModel.kt',
    r'C:\Ai_code\037movies-mobile\app\src\main\java\com\movies037\mobile\ui\player\PlayerScreen.kt'
]

all_ok = all(check_file(p) for p in files)
sys.exit(0 if all_ok else 1)
