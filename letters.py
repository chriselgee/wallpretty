#!/usr/bin/env python3
from PIL import Image, ImageFont
img = Image.new('L', (500, 500), color=0)
img_w, img_h = img.size
font = ImageFont.truetype('/usr/share/fonts/truetype/freefont/FreeMono.ttf', 20)
mask = font.getmask('some text related location that is going to write here.', mode='L')
mask_w, mask_h = mask.size
print(mask_w,mask_h)
print(type(mask))
d = Image.core.draw(img.im, 0)
d.draw_bitmap(((img_w - mask_w)/2, (img_h - mask_h)/2), mask, 255)
#img = img.rotate(40)
img.show()
img.save('op.jpg')