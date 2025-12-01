"""Dynamic icon generation for system tray."""

import logging
from io import BytesIO

from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)


class IconGenerator:
    """Generates dynamic gauge-style icons for the system tray."""

    # Color palette (RGB)
    COLORS = {
        "green": (76, 175, 80),  # 0-49%
        "yellow": (255, 193, 7),  # 50-74%
        "orange": (255, 152, 0),  # 75-89%
        "red": (244, 67, 54),  # 90-100%
        "gray": (158, 158, 158),  # Error/disconnected
        "blue": (33, 150, 243),  # Auth required
    }

    def __init__(self, size: int = 64):
        """
        Initialize icon generator.

        Args:
            size: Icon size in pixels (square).
        """
        self.size = size
        self._font = self._load_font()

    def _load_font(self) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        """Load font for percentage text."""
        font_size = self.size // 3
        try:
            # Try common Windows fonts
            for font_name in ["arial.ttf", "segoeui.ttf", "tahoma.ttf"]:
                try:
                    return ImageFont.truetype(font_name, font_size)
                except OSError:
                    continue
            # Fallback to default
            return ImageFont.load_default()
        except Exception as e:
            logger.warning(f"Failed to load font: {e}")
            return ImageFont.load_default()

    def _get_color(self, percentage: float) -> tuple[int, int, int]:
        """Get color based on usage percentage."""
        if percentage < 50:
            return self.COLORS["green"]
        elif percentage < 75:
            return self.COLORS["yellow"]
        elif percentage < 90:
            return self.COLORS["orange"]
        else:
            return self.COLORS["red"]

    def create_usage_icon(
        self, five_hour: float = 0, seven_day: float = 0
    ) -> Image.Image:
        """
        Create icon showing the more critical usage value.

        Args:
            five_hour: 5-hour utilization percentage (0-100)
            seven_day: 7-day utilization percentage (0-100)

        Returns:
            PIL Image object for the icon.
        """
        # Use higher value for display
        percentage = max(five_hour, seven_day)
        color = self._get_color(percentage)

        img = Image.new("RGBA", (self.size, self.size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        padding = 4
        center = self.size // 2
        radius = (self.size - padding * 2) // 2

        # Draw background ring (gray)
        draw.ellipse(
            [padding, padding, self.size - padding, self.size - padding],
            outline=(80, 80, 80, 200),
            width=6,
        )

        # Draw progress arc if percentage > 0
        if percentage > 0:
            # Draw arc representing usage
            extent = int(360 * (percentage / 100))
            bbox = [padding, padding, self.size - padding, self.size - padding]

            # Draw the arc (starting from top, going clockwise)
            draw.arc(
                bbox,
                start=-90,  # Start from top
                end=-90 + extent,
                fill=color,
                width=6,
            )

        # Draw percentage text in center
        text = f"{int(percentage)}"
        bbox = draw.textbbox((0, 0), text, font=self._font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        text_x = (self.size - text_width) // 2
        text_y = (self.size - text_height) // 2 - 2

        draw.text((text_x, text_y), text, fill=color, font=self._font)

        return img

    def create_error_icon(self, error_type: str = "error") -> Image.Image:
        """
        Create icon indicating error state.

        Args:
            error_type: Type of error ('auth_expired', 'network_error', or 'error')

        Returns:
            PIL Image object for the error icon.
        """
        img = Image.new("RGBA", (self.size, self.size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        if error_type == "auth_expired":
            color = self.COLORS["blue"]
            symbol = "!"
        elif error_type == "network_error":
            color = self.COLORS["gray"]
            symbol = "?"
        else:
            color = self.COLORS["gray"]
            symbol = "X"

        padding = 4

        # Draw filled circle
        draw.ellipse(
            [padding, padding, self.size - padding, self.size - padding],
            fill=color,
        )

        # Draw symbol
        try:
            symbol_font = ImageFont.truetype("arial.ttf", self.size // 2)
        except OSError:
            symbol_font = self._font

        bbox = draw.textbbox((0, 0), symbol, font=symbol_font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        text_x = (self.size - text_width) // 2
        text_y = (self.size - text_height) // 2 - 4

        draw.text((text_x, text_y), symbol, fill=(255, 255, 255), font=symbol_font)

        return img

    def create_loading_icon(self) -> Image.Image:
        """Create icon indicating loading state."""
        img = Image.new("RGBA", (self.size, self.size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        padding = 4
        color = self.COLORS["gray"]

        # Draw circle outline
        draw.ellipse(
            [padding, padding, self.size - padding, self.size - padding],
            outline=color,
            width=6,
        )

        # Draw "..." or spinner-like dots
        text = "..."
        bbox = draw.textbbox((0, 0), text, font=self._font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        text_x = (self.size - text_width) // 2
        text_y = (self.size - text_height) // 2

        draw.text((text_x, text_y), text, fill=color, font=self._font)

        return img

    @staticmethod
    def image_to_bytes(img: Image.Image, format: str = "ICO") -> bytes:
        """Convert PIL Image to bytes."""
        buffer = BytesIO()
        img.save(buffer, format=format)
        return buffer.getvalue()
