# -*- coding: utf-8 -*-
"""Contact sheet for QA. Chinese paths: imdecode/imencode only."""
import sys

import cv2
import numpy as np


def rd(p):
    return cv2.imdecode(np.frombuffer(open(p, "rb").read(), np.uint8), cv2.IMREAD_COLOR)


def wr(p, im):
    ok, buf = cv2.imencode(".png", im)
    assert ok, p
    open(p, "wb").write(buf.tobytes())


def main():
    out = sys.argv[1]
    files = sys.argv[2:]
    cols = 5
    if "--cols" in files:
        i = files.index("--cols")
        cols = int(files[i + 1])
        files = files[:i] + files[i + 2:]
    imgs = [rd(f) for f in files]
    h = max(i.shape[0] for i in imgs)
    w = max(i.shape[1] for i in imgs)
    rows = -(-len(imgs) // cols)
    sheet = np.full((rows * (h + 6) + 6, cols * (w + 6) + 6, 3), 245, np.uint8)
    for k, im in enumerate(imgs):
        r, c = divmod(k, cols)
        y, x = 6 + r * (h + 6), 6 + c * (w + 6)
        sheet[y:y + im.shape[0], x:x + im.shape[1]] = im
    wr(out, sheet)
    print("sheet", out, sheet.shape)


if __name__ == "__main__":
    main()
