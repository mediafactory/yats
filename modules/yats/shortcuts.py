from PIL import Image#, ImageOps

def resize_image(filename, size=(200, 150), dpi=75):
    image = Image.open(filename)
    pw = image.size[0]
    ph = image.size[1]
    nw = size[0]
    nh = size[1]

    # icon generell too small or equal
    if (pw < nw and ph < nh) or (pw == nw and ph == nh):
        if image.format.lower() == 'jpg' or image.format.lower() == 'jpeg':
            return image
                     
    else:
        pr = float(pw) / float(ph)
        nr = float(nw) / float(nh)
        
        if pr > nr:
            # icon aspect is wider than destination ratio
            tw = int(round(nh * pr))
            image = image.resize((tw, nh), Image.ANTIALIAS)
            l = int(round(( tw - nw ) / 2.0))
            image = image.crop((l, 0, l + nw, nh))
        elif pr < nr:
            # icon aspect is taller than destination ratio
            th = int(round(nw / pr))
            image = image.resize((nw, th), Image.ANTIALIAS)
            t = int(round(( th - nh ) / 2.0))
            image = image.crop((0, t, nw, t + nh))
        else:
            # icon aspect matches the destination ratio
            image = image.resize(size, Image.ANTIALIAS)
            
    if image.mode != "RGB":
        # http://packages.debian.org/search?keywords=python-imaging
        # if thumb_image.mode == "CMYK":
        #    thumb_image = ImageOps.invert(thumb_image)
        image = image.convert('RGB')
    return image