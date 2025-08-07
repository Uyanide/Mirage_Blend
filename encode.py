from PIL import Image
from pathlib import Path
from tqdm import tqdm
import math


def load_images_from_dir(dir: Path, maxNumber: int) -> list[Path]:
    ret = []
    count = 0
    for path in dir.glob("*"):
        if not path.is_file():
            print(f"跳过非文件: {path}")
            continue
        if count >= maxNumber:
            break
        ret.append(path)
        count += 1
    return ret


def resize_cover(image: Image.Image, tarSize: tuple) -> Image.Image:
    srcSize = image.size
    tarRatio = tarSize[0] / tarSize[1]
    srcRatio = srcSize[0] / srcSize[1]

    if srcRatio < tarRatio:
        newWidth = tarSize[0]
        newHeight = int(newWidth / srcRatio)
    else:
        newHeight = tarSize[1]
        newWidth = int(newHeight * srcRatio)

    resizedHmage = image.resize((newWidth, newHeight), Image.Resampling.LANCZOS)
    croppedImage = resizedHmage.crop((
        newWidth // 2 - tarSize[0] // 2,
        newHeight // 2 - tarSize[1] // 2,
        newWidth // 2 + tarSize[0] // 2,
        newHeight // 2 + tarSize[1] // 2))
    return croppedImage


def binarize_image(image: Image.Image) -> Image.Image:
    return image.convert("1")


def merge(imagePaths: list[Path], size: tuple, scale: int) -> Image.Image:
    ret = Image.new("RGBA", size)
    retPixels = ret.load()
    if not retPixels:
        raise ValueError("加载像素失败")

    for i, path in tqdm(enumerate(imagePaths), total=len(imagePaths), desc="混合图像"):
        try:
            image = Image.open(path)
            image = binarize_image(resize_cover(image, (size[0] // scale, size[1] // scale)))
        except Exception as e:
            print(f"加载图像 {path} 失败: {e}")
            continue
        imgPixels = image.load()
        if not imgPixels:
            print(f"加载第 {i} 张图像像素失败")
            continue

        offset = i // 32
        offsetX = offset % scale
        offsetY = offset // scale

        channel = (i % 32) // 8
        bit = (i % 32) % 8

        for y in range(image.size[1]):
            for x in range(image.size[0]):
                pos = (x * scale + offsetX, y * scale + offsetY)
                current_pixel = list(retPixels[pos])
                current_pixel[channel] = current_pixel[channel] | ((1 if imgPixels[x, y] else 0) << bit)
                retPixels[pos] = tuple(current_pixel)

    return ret


if __name__ == "__main__":
    from argparse import ArgumentParser
    parser = ArgumentParser(description="将大量图像整合为单张 PNG 图像")
    parser.add_argument("-x", "--width", type=int, default=800, help="输出图像宽度")
    parser.add_argument("-y", "--height", type=int, default=800, help="输出图像高度")
    parser.add_argument("-i", "--input", type=Path, default=Path("images"), help="输入图像目录")
    parser.add_argument("-o", "--output", type=Path, default=Path("encoded.png"), help="输出图像路径")
    parser.add_argument("-n", "--number", type=int, default=32, help="输入图像数量")
    args = parser.parse_args()

    if args.number < 1:
        raise ValueError("图像数量必须大于 0")

    imagePaths = sorted(load_images_from_dir(args.input, args.number))
    print(f"检测到 {len(imagePaths)} 张图像")

    scale = math.ceil(math.sqrt(math.ceil(len(imagePaths) / 32)))
    splitSize = (args.width // scale, args.height // scale)
    mergeSize = (splitSize[0] * scale, splitSize[1] * scale)

    merge(imagePaths, mergeSize, scale).save(args.output, "PNG")
