"""Captcha solver for the indianrail.gov.in PNR enquiry page.

The PNR endpoint serves a small PNG containing a simple arithmetic
expression (e.g. "7+2=?") rendered in a fixed pixel font. The solver is
template matching - no ML, no external OCR:

1. Flatten the image to grayscale and threshold it into a 0/1 matrix
   (dark pixels = ink).
2. Segment characters by finding contiguous vertical runs of ink columns,
   then trim empty rows inside each segment.
3. Serialize each character matrix into a bit-string ("0"/"1" per pixel)
   and look it up in KNOWN_TEMPLATES (pre-captured from the live site).
4. Evaluate the resulting "A+B" / "A-B" expression and return the answer.

The response includes '=' and '?' glyphs; they are stripped before solving.
Unknown glyphs abort the solve so the caller can retry with a fresh captcha.
"""

import io
from PIL import Image

# Bit-string templates (row-major, "1" = ink) captured from the live
# captcha font -> character it represents. Keys are exact pixel masks, so
# any font/CSS change on the site requires re-capturing these.
KNOWN_TEMPLATES = {
    "111111111111111111000000111000000110000000110000001100000001100000011000000011000000110000000110000001110000": "7",
    "0000110000000011000000001100000000110000111111111111111111110000110000000011000000001100000000110000": "+",
    "011111001111111010000111000000110000001100000111000011100001110000111000011100001111111111111111": "2",
    "001111100011111110011000110110000011110000011110000011110000011110000011110000011011000110011111110001111100": "0",
    "111111111111111111110000000000000000000011111111111111111111": "=",
    "011111011111111000011000001100001110001110001110000110000000000001100000110000011000": "?",
    "000111100011111110011000010110000000111111100111111110111000111110000011110000011011000111011111110001111100": "6",
    "011111110111111111110000011110000011011111110011111110111000111110000011110000011111000111011111110001111100": "8",
    "1111111111": "-",
    "011111110111111111110000011110000011001111110001111110000000111000000011000000011100000111111111110011111100": "3",
    "011110001111100011011000000110000001100000011000000110000001100000011000000110001111111111111111": "1",
    "000011110000001111000001101100001110110000110011000111001100011000110011000011001111111111111111111100000011000000001100": "4",
    "00111110001111111011100001101100000111100000111110001110111111110011111110000000110100001100111111100011111000": "9",
    "111111110111111110110000000110000000111111100111111110100000111000000011000000011100000111111111110011111100": "5",
}


def _solve(image_bytes):
    """Solve a captcha image and evaluate the arithmetic expression.

    Args:
        image_bytes: Raw PNG/JPEG bytes of the captcha as served by
            indianrail.gov.in/enquiry/captchaDraw.png.

    Returns:
        dict on both success and failure so callers can branch cleanly:
            {"success": True, "text": "<raw expression>", "answer": <int>}
            {"success": False, "error": "<reason>"}  # caller should retry
    """
    try:
        img = Image.open(io.BytesIO(image_bytes))

        # Flatten transparency onto white so anti-aliased edges threshold
        # cleanly; grayscale ('L') is what the threshold below expects.
        if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
            bg = Image.new('RGB', img.size, (255, 255, 255))
            bg.paste(img, (0, 0), img.convert('RGBA'))
            img = bg.convert('L')
        else:
            img = img.convert('L')

        # Threshold to a binary matrix: 1 = ink (dark pixel), 0 = background.
        pixels = img.load()
        width, height = img.size
        matrix = [[1 if pixels[x, y] < 128 else 0 for x in range(width)] for y in range(height)]

        def trim_empty_rows(mat):
            """Drop all-white rows so each glyph's bit-string is tight/aligned."""
            if not mat: return []
            top, bottom = 0, len(mat) - 1
            while top < len(mat) and sum(mat[top]) == 0: top += 1
            while bottom >= 0 and sum(mat[bottom]) == 0: bottom -= 1
            return mat[top:bottom+1] if top <= bottom else []

        # Segment characters: a glyph occupies a run of columns containing ink;
        # fully blank columns are separators. This assumes glyphs never touch.
        col_sums = [sum(matrix[y][x] for y in range(height)) for x in range(width)]
        chars, in_char, start_x = [], False, 0
        for x, col_sum in enumerate(col_sums):
            if col_sum > 0 and not in_char:
                in_char, start_x = True, x
            elif col_sum == 0 and in_char:
                in_char = False
                tight = trim_empty_rows([row[start_x:x] for row in matrix])
                if tight: chars.append(tight)
        # Trailing glyph (no blank column after it).
        if in_char:
            tight = trim_empty_rows([row[start_x:width] for row in matrix])
            if tight: chars.append(tight)

        # Map each glyph's pixel mask to a character via the template table.
        equation_string = ""
        for char_matrix in chars:
            char_hash = "".join("".join(str(c) for c in row) for row in char_matrix)
            if char_hash in KNOWN_TEMPLATES:
                equation_string += KNOWN_TEMPLATES[char_hash]
            else:
                # Unknown glyph (font change / noise) - abort so caller retries.
                return {"success": False, "error": f"Unknown hash found: {char_hash}"}

        # Evaluate "A+B" / "A-B"; '=' and '?' are decorative and ignored.
        clean_eq = equation_string.replace('=', '').replace('?', '').strip()
        if '+' in clean_eq:
            parts = clean_eq.split('+')
            answer = int(parts[0]) + int(parts[1])
        elif '-' in clean_eq:
            parts = clean_eq.split('-')
            answer = int(parts[0]) - int(parts[1])
        else:
            return {"success": False, "error": "No valid math operator found."}

        return {"success": True, "text": equation_string, "answer": answer}

    except Exception as e:
        # Never raise: a failed solve just triggers another captcha fetch.
        return {"success": False, "error": str(e)}
