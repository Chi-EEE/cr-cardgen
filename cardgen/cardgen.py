#!/usr/bin/env python3

import json
import logging
import os
import sys

import pngquant
import requests
import yaml
from PIL import Image
from PIL import ImageCms
from PIL import ImageChops

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

CONFIG = os.path.join("config.yaml")

pngquant.config('/usr/local/bin/pngquant')


enable_dataset_editing = True


def load_json(filename):
    """Load json by filename."""
    with open(filename, encoding='utf-8', mode='r') as f:
        data = json.load(f)

    # limit_card_keys = [
    #     'monk',
    #     'phoenix',
    # ]
    # limit_card_keys = None

    # if limit_card_keys is not None:
    #     data = [
    #         c for c in data if c.get('key') in limit_card_keys
    #     ]


    return data


def get_cards_data(config, local=False):
    if local:
        cards_data = load_json(config["cards_data"])
    else:
        r = requests.get(config["cards_data_url"])
        cards_data = r.json()

    return cards_data


def makedirs(dirs):
    for dir in dirs:
        os.makedirs(dir, exist_ok=True)


def generate_cards():
    """Generate Clash Royale cards."""
    with open(CONFIG) as f:
        config = yaml.full_load(f)

    cards_data = get_cards_data(config, local=True)

    src_path = config["src_dir"]
    spells_path = config["spells_dir"]

    output_png24_dir = config["output_png24_dir"]

    filenames = dict((v, k) for k, v in config["cards"].items())

    champion_frame = Image.open(os.path.join(src_path, "frame-champion.png"))

    card_frame = Image.open(os.path.join(src_path, "frame-card.png"))

    card_mask = Image.open(
        os.path.join(src_path, "mask-card.png")).convert("RGBA")
    leggie_mask = Image.open(
        os.path.join(src_path, "mask-legendary.png")).convert("RGBA")
    champion_mask = Image.open(
        os.path.join(src_path, "mask-champion.png")).convert("RGBA")

    size = card_frame.size

    for card_data in cards_data:
        name = card_data['key']
        rarity = card_data['rarity']

        filename = filenames.get(name)

        if filename is None:
            logger.warning(f"{name} does not have a corresponding file, continuing…")
            continue
            
        card_src = os.path.join(spells_path, "{}.png".format(filename))
        card_dst_png24 = os.path.join(output_png24_dir, "{}.png".format(name.replace("-", "_")))
        card_image = Image.open(card_src)

        if rarity == "Champion":
            card_image = card_image.resize((197,250), Image.Resampling.LANCZOS)
        else:
            card_image = card_image.resize((235,300), Image.Resampling.LANCZOS)
            
        # pad card with transparent pixels to be same size as output
        card_size = card_image.size
        
        card_x = int((size[0] - card_size[0]) / 2)
        card_y = int((size[1] - card_size[1]) / 2)
        card_x1 = card_x + card_size[0]
        card_y1 = card_y + card_size[1]

        im = Image.new("RGBA", size)
        im.paste(
            card_image, (card_x, card_y, card_x1, card_y1))
        card_image = im

        im = Image.new("RGBA", size)

        if rarity == "Legendary":
            im.paste(card_image, mask=leggie_mask)
            if enable_dataset_editing:
                LEFT = 33
                TOP = 31
                RIGHT = 235 + LEFT
                BOTTOM = 300 + TOP
            
                # Crop the image
                card_image = im.crop((LEFT, TOP, RIGHT, BOTTOM))
            else:
                card_image = im
        elif rarity == "Champion":
            # scale up image slightly and then crop to same dimension
            c_image = card_image
            orig_size = c_image.size
            old_w = orig_size[0]
            old_h = orig_size[1]
            scale = 1.1
            new_w = int(old_w * scale)
            new_h = int(old_h * scale)
            c_image = c_image.resize(
                (new_w, new_h)
            )
            crop_x = int((new_w - old_w) / 2)
            crop_y = int((new_h - old_w) / 2)
            crop_right = crop_x + old_w
            crop_bottom = crop_y + old_h

            c_image = c_image.crop(
                (crop_x, crop_y, crop_right, crop_bottom)
            )
            c_image = ImageChops.offset(c_image, 0, 50)
            im.paste(c_image, mask=champion_mask)
                        
            im = Image.alpha_composite(im, champion_frame)
            if enable_dataset_editing:
                LEFT = 54
                TOP = 66
                RIGHT = 195 + LEFT
                BOTTOM = 240 + TOP
            
                # Crop the image
                card_image = im.crop((LEFT, TOP, RIGHT, BOTTOM))
            else:
                card_image = im
        else:
            im.paste(card_image, mask=card_mask)
            if enable_dataset_editing:
                LEFT = 33
                TOP = 31
                RIGHT = 235 + LEFT
                BOTTOM = 300 + TOP
            
                # Crop the image
                card_image = im.crop((LEFT, TOP, RIGHT, BOTTOM))
            else:
                card_image = im

            
        if enable_dataset_editing:
            # Resize the image
            card_image = card_image.resize((197,251), Image.Resampling.LANCZOS) # Image.Resampling.NEAREST (More Pixelated)
            
        im = Image.new("RGBA", card_image.size)
        im = Image.alpha_composite(im, card_image)
        
        # save and output path to std out

        converted_im = ImageCms.profileToProfile(im, './AdobeRGB1998.icc', 'sRGB.icc')
        converted_im.save(card_dst_png24)
        logger.info(card_dst_png24)


def main(arguments):
    """Main."""
    
    generate_cards()

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
