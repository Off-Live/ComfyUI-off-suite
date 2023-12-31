
import torch
from .util import tensor2pil, pil2tensor, empty_pil_tensor, crop_image

class OFFImageResizeFit:
    def __init__(self):
        pass
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required":{
                "image":("IMAGE",)
            },
            "optional":{
                "size":("INT",{
                    "default": 512,
                })
            }
        }
    
    RETURN_TYPES = ("IMAGE",)

    FUNCTION = "doit"
    CATEGORY = "OFF"

    def doit(self, image, size=512):
        image = tensor2pil(image)
        new_width = size
        new_height = size
        ratio = float(image.width) / float(image.height)
        
        if image.width > image.height :
            new_width = int(size* ratio)
        else:
            new_height = int(size/ratio)

    
        image = image.resize((new_width, new_height))

        return (pil2tensor(image),)



class OFFCenterCrop:

    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(s):
        """
            Return a dictionary which contains config for all input fields.
            Some types (string): "MODEL", "VAE", "CLIP", "CONDITIONING", "LATENT", "IMAGE", "INT", "STRING", "FLOAT".
            Input types "INT", "STRING" or "FLOAT" are special values for fields on the node.
            The type can be a list for selection.

            Returns: `dict`:
                - Key input_fields_group (`string`): Can be either required, hidden or optional. A node class must have property `required`
                - Value input_fields (`dict`): Contains input fields config:
                    * Key field_name (`string`): Name of a entry-point method's argument
                    * Value field_config (`tuple`):
                        + First value is a string indicate the type of field or a list for selection.
                        + Secound value is a config for type "INT", "STRING" or "FLOAT".
        """
        return {
            "required": {
                "image": ("IMAGE",)
            },
        }

    RETURN_TYPES = ("IMAGE",)
    # RETURN_NAMES = ("image_output_name",)

    FUNCTION = "image_crop"

    # OUTPUT_NODE = False

    CATEGORY = "OFF"

    # Tensor to PIL

    def image_crop(self, image):
        image = tensor2pil(image)
        img_width, img_height = image.size

        crop_size = img_width
        if img_width > img_height:
            crop_size = img_height

        top = (img_height - crop_size)/2
        left = (img_width - crop_size)/2
        bottom = top + crop_size
        right = left + crop_size

        # Calculate the final coordinates for cropping
        crop_top = max(top, 0)
        crop_left = max(left, 0)
        crop_bottom = min(bottom, img_height)
        crop_right = min(right, img_width)

        # Ensure that the cropping region has non-zero width and height
        crop_width = crop_right - crop_left
        crop_height = crop_bottom - crop_top
        if crop_width <= 0 or crop_height <= 0:
            raise ValueError(
                "Invalid crop dimensions. Please check the values for top, left, right, and bottom.")

        # Crop the image and resize
        crop = image.crop((crop_left, crop_top, crop_right, crop_bottom))

        crop = crop.resize(
            (((crop.size[0] // 8) * 8), ((crop.size[1] // 8) * 8)))

        return (pil2tensor(crop),)


class OFFSEGSToImage:
    @classmethod
    def INPUT_TYPES(s):
        return {"required": {
            "segs": ("SEGS", ),
        },
            "optional": {
            "fallback_image_opt": ("IMAGE", ),
        }
        }

    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "doit"

    CATEGORY = "OFF"

    def doit(self, segs, fallback_image_opt=None):
        results = list()

        for seg in segs[1]:
            if seg.cropped_image is not None:
                cropped_image = torch.from_numpy(seg.cropped_image)
            elif fallback_image_opt is not None:
                # take from original image
                cropped_image = torch.from_numpy(
                    crop_image(fallback_image_opt, seg.crop_region))
            else:
                cropped_image = empty_pil_tensor()

            results.append(cropped_image)

        if len(results) == 0:
            results.append(empty_pil_tensor())

        return (results[0],)
    
class OFFCenterCropSEGS:
    @classmethod
    def INPUT_TYPES(s):
        return {"required": {
                "segs": ("SEGS", ),
                "image": ("IMAGE",)
            }
        }

    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "doit"

    CATEGORY = "OFF"

    def doit(self, segs, image=None):
        results = list()
        image = tensor2pil(image)
        img_width, img_height = image.size

        crop_size = img_width
        if img_width > img_height:
            crop_size = img_height
            
        for seg in segs[1]:
            
            if seg.cropped_image is not None:
                center_x = (seg.crop_region[0] + seg.crop_region[2])/2
                center_y = (seg.crop_region[1] + seg.crop_region[3])/2

                crop_top = center_y  - crop_size/2
                crop_left = center_x - crop_size/2
                crop_bottom = center_y + crop_size/2
                crop_right = center_x + crop_size/2

                if crop_top < 0:
                    crop_bottom = crop_bottom - crop_top
                    crop_top = 0
                if crop_left < 0:
                    crop_right = crop_right - crop_left
                    crop_left = 0

                if crop_bottom > img_height:
                    crop_top = crop_top - (crop_bottom - img_height)
                    crop_bottom = img_height
                if crop_right > img_width:
                    crop_left = crop_left - (crop_right - img_width)
                    crop_right = img_width

                cropped_image = image.crop(
                    (crop_left, crop_top, crop_right, crop_bottom))
                cropped_image = cropped_image.resize(
                    (((cropped_image.size[0] // 8) * 8), ((cropped_image.size[1] // 8) * 8)))
                cropped_image = pil2tensor(cropped_image)
            else:
                cropped_image = empty_pil_tensor()

            results.append(cropped_image)

        if len(results) == 0:
            results.append(empty_pil_tensor())

        return (results[0],)

class OFFWatermark:
    def __init__(self):
        pass
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required":{
                "source":("IMAGE",),
                "watermark":("IMAGE",)
            }
        }
    
    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "doit"

    CATEGORY = "OFF"

    def doit(self, source, watermark):
        source_image = tensor2pil(source)
        watermark_image = tensor2pil(watermark).convert()

        watermark_ratio = watermark_image.height/ watermark_image.width
        new_wm_with = source_image.width*0.15
        watermark_image = watermark_image.resize((int(new_wm_with), int(new_wm_with*watermark_ratio)))
        source_image.paste(watermark_image,(10,10), watermark_image)
            
        return (pil2tensor(source_image),)
