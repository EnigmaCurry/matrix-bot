from PIL import Image, ImageDraw
from svglib.svglib import svg2rlg
from reportlab.graphics import renderPM
from reportlab.graphics.shapes import Drawing
from reportlab.platypus import Flowable
import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

def interpolate(f_co, t_co, interval):
    det_co =[(t - f) / interval for f , t in zip(f_co, t_co)]
    for i in range(interval):
        yield [round(f + det * i) for f, det in zip(f_co, det_co)]

def remove_transparency(img):
    flat_composite = Image.new("RGB", img.size, (255,0,0))
    try:
        flat_composite.paste(img, mask=img.split()[3])
    except IndexError:
        logger.debug("NO Transparency to remove!")
        return img
    return flat_composite

def thumbnail(img):
    img.thumbnail((150, 150))
    return img

def svg_to_img(img_path):
    try:
        drawing = svg2rlg(img_path)
    except TypeError:
        logger.error("svg2rlg failed")
        raise
    sx = sy = 5
    drawing.width, drawing.height = drawing.minWidth() * sx, drawing.height * sy
    drawing.scale(sx, sy)
    #if you want to see the box around the image
    drawing._showBoundary = True
    #tmp_path = tempfile.mktemp(prefix=f"{term}-iconduck-", suffix=".jpg")
    return renderPM.drawToPIL(drawing)
