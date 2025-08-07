from PIL import Image
from pathlib import Path
from argparse import ArgumentParser
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


def merge(imagePaths: list[Path], coverImage: Image.Image, size: tuple, scale: int) -> Image.Image:
    ret = Image.new("RGBA", size)
    retPixels = ret.load()
    if not retPixels:
        raise ValueError("加载像素失败")
    coverPixels = coverImage.load()
    if not coverPixels:
        raise ValueError("加载表图像素失败")

    for i, path in tqdm(enumerate(imagePaths), total=len(imagePaths), desc="合并图像"):
        try:
            image = Image.open(path)
            image = binarize_image(resize_cover(image, (size[0] // scale, size[1] // scale)))
        except Exception as e:
            raise ValueError(f"加载图像 {path} 失败: {e}")

        offset = i // 27
        offsetX = offset % scale
        offsetY = offset // scale

        # skip MSB of each channel for coverImage
        channel = (i % 27) // 7
        bit = (i % 27) % 7

        imgPixels = image.load()
        if not imgPixels:
            raise ValueError(f"加载第 {i} 张图像像素失败")
        for y in range(image.size[1]):
            for x in range(image.size[0]):
                pos = (x * scale + offsetX, y * scale + offsetY)
                current_pixel = list(retPixels[pos])
                current_pixel[channel] = current_pixel[channel] | ((1 if imgPixels[x, y] else 0) << bit)
                retPixels[pos] = tuple(current_pixel)

    for y in range(coverImage.size[1]):
        for x in range(coverImage.size[0]):
            v = (1 if coverPixels[x, y] else 0) << 7
            r = retPixels[x, y]
            retPixels[x, y] = (r[0] | v, r[1] | v, r[2] | v, r[3] | (1 << 6))

    return ret


if __name__ == "__main__":
    parser = ArgumentParser(description="将大量图像整合为单张 PNG 图像")
    parser.add_argument("-x", "--width", type=int, default=800, help="输出图像宽度")
    parser.add_argument("-y", "--height", type=int, default=800, help="输出图像高度")
    parser.add_argument("-i", "--input", type=Path, default=Path("images"), help="输入图像目录")
    parser.add_argument("-o", "--output", type=Path, default=Path("encoded.png"), help="输出图像路径")
    parser.add_argument("-n", "--number", type=int, default=27, help="隐藏图像数量")
    parser.add_argument("-c", "--cover", type=Path, help="表图(肉眼可分辨图像)路径")
    args = parser.parse_args()

    if args.number < 1:
        raise ValueError("隐藏图像数量必须大于 0")

    try:
        coverImage = Image.open(args.cover) if args.cover else Image.new("1", (args.width, args.height))
    except Exception as e:
        raise ValueError(f"加载表图失败: {e}")
    if not coverImage:
        raise ValueError("加载表图失败")

    imagePaths = load_images_from_dir(args.input, args.number)
    print(f"检测到 {len(imagePaths)} 张图像")

    scale = math.ceil(math.sqrt(math.ceil(len(imagePaths) / 27)))
    splitSize = (args.width // scale, args.height // scale)
    mergeSize = (splitSize[0] * scale, splitSize[1] * scale)

    coverImage = binarize_image(resize_cover(coverImage, mergeSize))

    merge(imagePaths, coverImage, mergeSize, scale).save(args.output, "PNG")
