"""Burn redactions into re-encoded images before crops and annotations."""
from common import source_bytes,MAX_PIXELS
from io import BytesIO

def prepare_image(row,privacy,step,dest):
    from PIL import Image,ImageDraw,ImageOps
    snapshot=source_bytes(row)
    with Image.open(BytesIO(snapshot)) as original:
        if original.width*original.height>MAX_PIXELS:raise ValueError('图片尺寸超限')
        oriented=ImageOps.exif_transpose(original)
        rgba=oriented.convert('RGBA')
        image=Image.new('RGB',rgba.size,'white')
        image.paste(rgba,mask=rgba.getchannel('A'))
    if image.size!=(row['width'],row['height']):raise ValueError('图片尺寸与来源索引不一致')
    draw=ImageDraw.Draw(image)
    for b in privacy['redactions']:
        x0,y0,x1,y1=map(int,b);draw.rectangle((x0,y0,x1-1,y1-1),fill=(30,41,59))
    crop=step.get('crop') or [0,0,*image.size];x0,y0,x1,y1=map(int,crop)
    image=image.crop((x0,y0,x1,y1))
    # A separate gutter carries numbered badges without painting over screen text.
    canvas=Image.new('RGB',(max(image.width,16+32*len(step['annotations'])),image.height+40),'white');canvas.paste(image,(0,40));draw=ImageDraw.Draw(canvas)
    for index,a in enumerate(step['annotations']):
        color=[(37,99,235),(180,83,9),(126,34,206),(4,120,87),(190,18,60),(14,116,144),(67,56,202),(77,124,15),(162,28,175),(120,53,15)][index]
        bx0,by0,bx1,by1=map(int,a['box']);box=(bx0-x0,by0-y0+40,bx1-x0-1,by1-y0+39)
        draw.rectangle(box,outline=color,width=3)
        badge_x=8+index*32
        draw.rounded_rectangle((badge_x,7,badge_x+25,32),radius=6,fill=color)
        draw.text((badge_x+7,12),a['label'],fill='white')
    # New RGB canvas strips EXIF/text chunks and never embeds the original.
    canvas.save(dest,format='PNG')
