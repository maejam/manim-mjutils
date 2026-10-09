import contextlib
import tempfile
from pathlib import Path
from typing import Any

import manim as m
from manim.typing import Vector3DLike
from manim.utils.unit import Pixels
from PIL import Image


class IconText(m.Group):
    """A simple Mobject combining an icon and text.

    Similar to IconText but accepts raster images.

    Because of the limitations of Manim to handle SVG, especially ones with multiple
    colors, this class allows to use raster images as icons and handles resizing to the
    desired size. Prefer using SVGs whenever possible.

    Parameters
    ----------
    icon
        The icon to display. Can be:
        - A string or pathlib.Path to an image file (.svg, .png, .jpg).
        - A Manim VMobject instance.
        - None, which defaults to an empty VMobject.
    text
        The text string to display next to the icon.
    icon_height
        The target height of the icon in Munits.
    font_size
        The font size for the text.
    font
        The font family to use for the text.
    svg_icon_color
        The fill color for SVG icons. Ignored for raster images and VMobjects.
        Set to `None` (default) to keep original color.
    img_resampling_algo
        The resampling algorithm for resizing raster images. Can be a
        `PIL.Image.Resampling` constant or the associated integer:
        - 0: NEAREST
        - 1: LANCZOS (Default, recommended for quality when downsampling)
        - 2: BILINEAR
        - 3: BICUBIC
        - 4: BOX
        - 5: HAMMING
    text_color
        The color of the text (default WHITE).
    direction
        The direction in which to arrange the icon and text (default RIGHT).
    buff
        The buffer distance between the icon and the text.
    **kwargs
        Additional keyword arguments passed to the parent Mobject class.

    Attributes
    ----------
    icon
        The icon Mobject (SVGMobject, ImageMobject, empty or custom VMobject).
    text
        The text Mobject.

    """

    def __init__(
        self,
        icon: m.VMobject | str | Path | None = None,
        text: str = "",
        icon_height: float = 0.5,
        font_size: float = 48,
        font: str = "Monospace",
        svg_icon_color: m.ManimColor | None = None,
        img_resampling_algo: Image.Resampling | int = Image.Resampling.LANCZOS,
        text_color: m.ManimColor = m.WHITE,
        direction: Vector3DLike = m.RIGHT,
        buff: float = 0.15,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)

        # icon
        self.icon: m.SVGMobject | m.ImageMobject | m.VMobject

        if isinstance(icon, str):
            path = Path(icon).expanduser().resolve()
            if path.suffix.lower() == ".svg":
                self.icon = m.SVGMobject(path, fill_color=svg_icon_color)
            else:
                # use lanczos algo by default for better quality after downsampling
                target_height_px = icon_height / (1 * Pixels)
                with Image.open(path) as img:
                    w, h = img.size
                    scale_factor = target_height_px / h
                    new_w = int(w * scale_factor)
                    new_h = int(h * scale_factor)
                    resized = img.resize((new_w, new_h), img_resampling_algo)
                    suffix = path.suffix
                    with tempfile.NamedTemporaryFile(suffix=suffix) as tmp_file:
                        temp_path = tmp_file.name
                        resized.save(temp_path)
                        self.icon = m.ImageMobject(temp_path)

        elif isinstance(icon, m.VMobject):
            self.icon = icon
        else:
            self.icon = m.VMobject()

        with contextlib.suppress(ZeroDivisionError):
            self.icon.scale(icon_height / self.icon.height)

        # text
        self.text = m.Text(text, font=font, font_size=font_size)
        self.text.set_color(text_color)

        # arrange
        self.add(self.icon, self.text)
        self.arrange(direction, buff=buff)

    def __repr__(self) -> str:
        return f"{type(self).__name__}(text={self.text})"


class VIconText(m.VGroup):
    """A simple VMobject combining an icon and text.

    Similar to IconText but does not accept raster images.

    Parameters
    ----------
    icon
        The icon to display. Can be:
        - A string or pathlib.Path to an svg file.
        - A Manim VMobject instance.
        - None, which defaults to an empty VMobject.
    text
        The text string to display next to the icon.
    icon_height
        The target height of the icon in Munits.
    font_size
        The font size for the text.
    font
        The font family to use for the text.
    svg_icon_color
        The fill color for SVG icons. Ignored for VMobjects.
        Set to `None` (default) to keep original color.
    text_color
        The color of the text (default WHITE).
    direction
        The direction in which to arrange the icon and text (default RIGHT).
    buff
        The buffer distance between the icon and the text.
    **kwargs
        Additional keyword arguments passed to the parent Mobject class.

    Attributes
    ----------
    icon
        The icon Mobject (SVGMobject, empty or custom VMobject).
    text
        The text Mobject.

    """

    def __init__(
        self,
        icon: m.VMobject | str | Path | None = None,
        text: str = "",
        icon_height: float = 0.5,
        font_size: float = 48,
        font: str = "Monospace",
        svg_icon_color: m.ManimColor | None = None,
        text_color: m.ManimColor = m.WHITE,
        direction: Vector3DLike = m.RIGHT,
        buff: float = 0.15,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)

        # icon
        self.icon: m.SVGMobject | m.VMobject

        if isinstance(icon, str):
            path = Path(icon).expanduser().resolve()
            if path.suffix.lower() == ".svg":
                self.icon = m.SVGMobject(path, fill_color=svg_icon_color)
            else:
                raise TypeError(
                    f"The `icon` parameter in {type(self).__class__} can only be an "
                    "svg file or a custom VMobject."
                )

        elif isinstance(icon, m.VMobject):
            self.icon = icon
        else:
            self.icon = m.VMobject()

        with contextlib.suppress(ZeroDivisionError):
            self.icon.scale(icon_height / self.icon.height)

        # text
        self.text = m.Text(text, font=font, font_size=font_size)
        self.text.set_color(text_color)

        # arrange
        self.add(self.icon, self.text)
        self.arrange(direction, buff=buff)

    def __repr__(self) -> str:
        return f"{type(self).__name__}(text={self.text})"
