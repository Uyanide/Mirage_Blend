from PIL import Image
from pathlib import Path
from argparse import ArgumentParser
from tqdm import tqdm
import math

def split(encodedImage: Image.Image, number: int, outputDir: Path):
    if encodedImage.mode != "RGBA":
        raise ValueError("输入图像必须是 RGBA 模式")
    srcPixel = encodedImage.load()
    if not srcPixel:
        raise ValueError("加载输入图像像素失败")

    width, height = encodedImage.size
    scale = math.ceil(math.sqrt(math.ceil(number / 27)))
    if width % scale != 0 or height % scale != 0:
        raise ValueError("输入图像格式错误")
    splitWidth = width // scale
    splitHeight = height // scale

    for i in tqdm(range(number), desc="解码图像"):
        offset = i // 27
        offsetX = offset % scale
        offsetY = offset // scale

        channel = (i % 27) // 7
        bit = (i % 27) % 7

        image = Image.new("1", (splitWidth, splitHeight))
        pixels = image.load()
        if not pixels:
            raise ValueError(f"创建第 {i} 张图像失败")
        for y in range(splitHeight):
            for x in range(splitWidth):
                pos = (x * scale + offsetX, y * scale + offsetY)
                pixels[x, y] = (srcPixel[pos][channel] >> bit) & 1

        image.save(outputDir / f"{i}.png", "PNG")

    coverImage = Image.new("1", (width, height))
    coverPixels = coverImage.load()
    if not coverPixels:
        raise ValueError("创建表图像失败")
    for y in range(height):
        for x in range(width):
            v = (srcPixel[x, y][3] >> 6) & 1
            coverPixels[x, y] = v

    coverImage.save(outputDir / "cover.png", "PNG")
    print(f"成功解码表图和 {number} 张图像到 {outputDir} 目录")



if __name__ == "__main__":
    parser = ArgumentParser(description="从单张 PNG 图像中解码隐藏的图像")
    parser.add_argument("-i", "--input", type=Path, default=Path("encoded.png"), help="输入图像文件")
    parser.add_argument("-o", "--output", type=Path, default=Path("decoded"), help="输出图像目录")
    parser.add_argument("-n", "--number", type=int, default=27, help="解码图像数量(不包含表图)")
    args = parser.parse_args()

    if args.number < 1:
        raise ValueError("解码图像数量必须大于 0")

    try:
        encoded_image = Image.open(args.input)
    except Exception as e:
        raise ValueError(f"加载输入图像失败: {e}")
    if not encoded_image:
        raise ValueError("加载输入图像失败")

    if not args.output.exists():
        args.output.mkdir(parents=True, exist_ok=True)

    split(encoded_image, args.number, args.output)