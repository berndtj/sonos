#!/usr/bin/env python3

#         Python Stream Deck Library
#      Released under the MIT license
#
#   dean [at] fourwalledcubicle [dot] com
#         www.fourwalledcubicle.com
#

# Example script showing basic library usage - updating key images with new
# tiles gnerated at runtime, and responding to button state change events.

from __future__ import annotations

import argparse
import os
import sys
import threading
import time
import soco

from PIL import Image, ImageDraw, ImageFont
from StreamDeck.DeviceManager import DeviceManager
from StreamDeck.ImageHelpers import PILHelper
from StreamDeck.Transport.Transport import TransportError

STREAM_DECK_NEO = "Stream Deck Neo"
BRIGHTNESS = 100

# Folder location of image assets used by this example.
ASSETS_PATH = os.path.join(os.path.dirname(__file__), "assets")
FONT_PATH = os.path.join(ASSETS_PATH, "Roboto-Regular.ttf")

SPEAKERS = [
    "Family Room",
    "Patio",
    "Bedroom",
    "Office"
]

class Button:
    _icon_background_active = (0, 150, 0)
    _icon_background_inactive = (0, 0, 0)

    def __init__(self):
        self._pressed = False

    def render(self, neo: SonosDeckNeo) -> None:
        pass

    def on_press(self, neo: SonosDeckNeo, key: int) -> None:
        self._pressed = True
        print("Deck {} Key {} pressed".format(neo._deck.id(), key), flush=True)

    def on_release(self, neo: SonosDeckNeo, key: int) -> None:
        self._pressed = False
        print("Deck {} Key {} released".format(neo._deck.id(), key), flush=True)


class SpeakerButton(Button):
    _icon = os.path.join(ASSETS_PATH, "speaker-icon.png")

    def __init__(self, speaker: soco.core.SoCo):
        super().__init__()
        self._speaker = speaker
        self._cancel = False

    def is_active(self, neo: SonosDeckNeo) -> bool:
        return self._speaker in neo._leader.group

    def name(self) -> str:
        return self._speaker.player_name

    def on_release(self, neo: SonosDeckNeo, key: int) -> None:
        super().on_release(neo, key)
        if self._cancel:
            self._cancel = False
            return
        if self.is_active(neo):
            self._speaker.unjoin()
        else:
            self._speaker.join(neo._leader)
        # No way to block on the command completing... so just sleep a second
        time.sleep(0.5)
        self.render(neo, key)

    def render(self, neo: SonosDeckNeo, key: int) -> None:
        # Resize the source image asset to best-fit the dimensions of a single key,
        # leaving a margin at the bottom so that we can draw the key title
        # afterwards.
        icon = Image.open(self._icon)
        background = self._icon_background_inactive
        if self.is_active(neo):
            background = self._icon_background_active
        image = PILHelper.create_scaled_key_image(neo._deck, icon, margins=[0, 0, 40, 0], background=background)

        # Load a custom TrueType font and use it to overlay the key index, draw key
        # label onto the image a few pixels from the bottom of the key.
        draw = ImageDraw.Draw(image)
        font = ImageFont.truetype(FONT_PATH, 14)
        draw.text((image.width / 2, image.height - 25), text=self.name(), font=font, anchor="ms", fill="white")
        draw.text((image.width / 2, image.height - 5), text="vol: %d" % (self._speaker.volume), font=font, anchor="ms", fill="white")

        native_image = PILHelper.to_native_key_format(neo._deck, image)

        with neo._deck:
            # Update requested key with the generated image.
            neo._deck.set_key_color(key, 255, 0, 0)
            neo._deck.set_key_image(key, native_image)


class PlayURLButton(Button):

    def __init__(self, name: str, url: str, icon: str):
        super().__init__()
        self._name = name
        self._url = url
        self._icon = icon

    def name(self) -> str:
        return self._name

    def is_active(self, neo: SonosDeckNeo) -> bool:
        title = neo.get_current_title()
        return neo.get_current_title() == self._name

    def on_press(self, neo: SonosDeckNeo, key: int) -> None:
        super().on_press(neo, key)
        neo._leader.play_uri(title=self._name, uri=self._url, force_radio=True)
        self.render(neo, key)

    def render(self, neo: SonosDeckNeo, key: int) -> None:
        # Resize the source image asset to best-fit the dimensions of a single key,
        # leaving a margin at the bottom so that we can draw the key title
        # afterwards.
        image = None
        background = self._icon_background_inactive
        if self.is_active(neo):
            background = self._icon_background_active
        if self._icon:
            icon = Image.open(self._icon)
            image = PILHelper.create_scaled_key_image(neo._deck, icon, margins=[0, 0, 20, 0], background=background)
        else:
            image = PILHelper.create_key_image(neo._deck, background=background)

        # Load a custom TrueType font and use it to overlay the key index, draw key
        # label onto the image a few pixels from the bottom of the key.
        draw = ImageDraw.Draw(image)
        font = ImageFont.truetype(FONT_PATH, 14)
        draw.text((image.width / 2, image.height - 5), text=self.name(), font=font, anchor="ms", fill="white")

        native_image = PILHelper.to_native_key_format(neo._deck, image)

        with neo._deck:
            # Update requested key with the generated image.
            neo._deck.set_key_color(key, 255, 0, 0)
            neo._deck.set_key_image(key, native_image)


class StopButton(Button):
    _icon = os.path.join(ASSETS_PATH, "stop.png")
    _name = "Stop"

    def on_press(self, neo: SonosDeckNeo, key: int) -> None:
        neo._leader.stop()

    def render(self, neo: SonosDeckNeo, key: int) -> None:
        # Resize the source image asset to best-fit the dimensions of a single key,
        # leaving a margin at the bottom so that we can draw the key title
        # afterwards.
        image = None
        background = self._icon_background_inactive
        icon = Image.open(self._icon)
        image = PILHelper.create_scaled_key_image(neo._deck, icon, margins=[0, 0, 20, 0], background=background)

        # Load a custom TrueType font and use it to overlay the key index, draw key
        # label onto the image a few pixels from the bottom of the key.
        draw = ImageDraw.Draw(image)
        font = ImageFont.truetype(FONT_PATH, 14)
        draw.text((image.width / 2, image.height - 5), text=self._name, font=font, anchor="ms", fill="white")

        native_image = PILHelper.to_native_key_format(neo._deck, image)

        with neo._deck:
            # Update requested key with the generated image.
            neo._deck.set_key_color(key, 255, 0, 0)
            neo._deck.set_key_image(key, native_image)


class VolumeButton(Button):

    def __init__(self, up: bool):
        super().__init__()
        self._up = up

    def on_press(self, neo: SonosDeckNeo, key: int) -> None:
        super().on_press(neo, key)
        target = neo._leader.group
        target_button = None
        for key, button in neo._speaker_buttons.items():
            if button._pressed:
                target = button._speaker
                target_button = (key, button)
                break

        snapped = round(target.volume / 5) * 5
        if self._up:
            target.volume = snapped + 5
        else:
            target.volume = snapped - 5
        if target_button is not None:
            target_button[1]._cancel = True
            target_button[1].render(neo, target_button[0])
        else:
            neo.refresh()

    def render(self, neo: SonosDeckNeo, key: int) -> None:
        if self._up:
            neo._deck.set_key_color(key, 0, 0, 255)
        else:
            neo._deck.set_key_color(key, 255, 0, 0)


class SonosDeckNeo:

    def __init__(self, deck: StreamDeckNeo, leader_name: str):
        self._deck = deck
        self._leader: soco.core.SoCo = soco.discovery.by_name(leader_name)
        self._buttons: dict[int, Button] = {}
        self._speaker_buttons: dict[int, SpeakerButton] = {}
        self._deck.set_key_callback(self.__callback)

    def __callback(self, deck: StreamDeckNeo, key: int, pressed: bool) -> None:
        button = self._buttons.get(key) or self._speaker_buttons.get(key)
        if button is None:
            return
        if pressed:
            button.on_press(self, key)
        else:
            button.on_release(self, key)
        button.render(self, key)

    def add_speaker(self, key: int, name: str) -> None:
        speaker = soco.discovery.by_name(name)
        button = SpeakerButton(speaker=speaker)
        self._speaker_buttons[key] = button

    def add_button(self, key: int, button: Button) -> None:
        self._buttons[key] = button

    def get_current_title(self) -> str:
        return self._leader.get_current_track_info()["title"]

    def render_screen(self) -> None:
        image = PILHelper.create_screen_image(self._deck)
        # Load a custom TrueType font and use it to create an image
        draw = ImageDraw.Draw(image)
        font = ImageFont.truetype(FONT_PATH, 14)
        draw.text((image.width / 2, image.height - 10), text=self.get_current_title(), font=font, anchor="ms", fill="white")
        draw.text((image.width / 2, image.height - 40), text="vol: %d" % (self._leader.group.volume), font=font, anchor="ms", fill="white")
        self._deck.set_screen_image(PILHelper.to_native_screen_format(self._deck, image))

    def refresh(self) -> None:
        for key, speaker in self._speaker_buttons.items():
            speaker.render(self, key)

        for key, button in self._buttons.items():
            button.render(self, key)

        self.render_screen()


def main():
    argparser = argparse.ArgumentParser()
    argparser.add_argument("-z", "--zone", help="Speaker name representing the control group", default="Family Room")
    args = argparser.parse_args()

    # Just grab the first deck (we don't support multiple anyway)
    deck = DeviceManager().enumerate().pop()

    # This example only works with devices that have screens.
    if deck.deck_type() != STREAM_DECK_NEO:
        sys.exit("Server only supports %s [found: %s]" % (STREAM_DECK_NEO, deck.deck_type()))

    deck.open()
    deck.reset()

    print("Opened '{}' device (serial number: '{}', fw: '{}')".format(
        deck.deck_type(), deck.get_serial_number(), deck.get_firmware_version()
    ))

    # Set initial screen brightness to 30%.
    deck.set_brightness(BRIGHTNESS)

    neo = SonosDeckNeo(deck=deck, leader_name=SPEAKERS[0])
    for i, name in enumerate(SPEAKERS):
        neo.add_speaker(key=4+i, name=name)

    kexp = PlayURLButton(url="https://kexp.streamguys1.com/kexp160.aac", name="KEXP", icon=os.path.join(ASSETS_PATH, "kexp.png"))
    neo.add_button(key=0, button=kexp)

    stop = StopButton()
    neo.add_button(key=3, button=stop)

    up = VolumeButton(up=True)
    down = VolumeButton(up=False)
    neo.add_button(key=8, button=up)
    neo.add_button(key=9, button=down)

    neo.refresh()

    def refresh_loop():
        while True:
            time.sleep(5)
            neo.refresh()

    t = threading.Thread(target=refresh_loop, daemon=True)
    t.start()

    for t in threading.enumerate():
        try:
            t.join()
        except (TransportError, RuntimeError):
            pass


if __name__ == "__main__":
    main()
