import os
import struct


def bgra(color):
    red, green, blue, alpha = color
    return bytes((blue, green, red, alpha))


def write_icon(path):
    size = 32
    pixels = []
    center = (size - 1) / 2
    for y in range(size):
        for x in range(size):
            dx = x - center
            dy = y - center
            distance = (dx * dx + dy * dy) ** 0.5
            if distance > 15:
                color = (0, 0, 0, 0)
            elif distance > 13:
                color = (102, 70, 24, 255)
            elif distance > 11:
                color = (244, 190, 62, 255)
            elif abs(dx) < 2 or abs(dy) < 2:
                color = (255, 236, 145, 255)
            else:
                color = (214, 136, 38, 255)
            pixels.append(bgra(color))

    xor_bitmap = b"".join(reversed([b"".join(pixels[y * size:(y + 1) * size]) for y in range(size)]))
    and_mask = b"\x00" * (size * size // 8)
    bitmap_header = struct.pack(
        "<IIIHHIIIIII",
        40,
        size,
        size * 2,
        1,
        32,
        0,
        len(xor_bitmap) + len(and_mask),
        0,
        0,
        0,
        0,
    )
    image = bitmap_header + xor_bitmap + and_mask
    icon_dir = struct.pack("<HHH", 0, 1, 1)
    icon_entry = struct.pack("<BBBBHHII", size, size, 0, 0, 1, 32, len(image), 6 + 16)

    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as file:
        file.write(icon_dir + icon_entry + image)


if __name__ == "__main__":
    write_icon(os.path.join("build", "windows", "coinrush.ico"))
